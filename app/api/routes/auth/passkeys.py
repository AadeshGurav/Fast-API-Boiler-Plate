"""Passkeys: register, list and remove your own; sign in without a password."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import get_auth_service, get_data_service
from app.models.auth import LoginResponse, TokenPayload
from app.models.passkey import Passkey, PasskeyLogin, PasskeyOptions, PasskeyRegistration
from app.services.auth import AuthenticationError, AuthService
from app.services.auth.passkeys import PasskeyError, PasskeysDisabledError
from app.services.data import DataService
from app.utils.cookie_manager import CookieManager
from app.utils.permissions import get_session_user
from app.utils.utils import extract_device_info

router = APIRouter(prefix="/auth/passkeys", tags=["Passkeys"])


def _refused(e: PasskeyError) -> HTTPException:
    code = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if isinstance(e, PasskeysDisabledError)
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=str(e))


@router.post("/registration/options", response_model=PasskeyOptions)
async def passkey_registration_options(
    user: TokenPayload = Depends(get_session_user),
    auth_service: AuthService = Depends(get_auth_service),
    data_service: DataService = Depends(get_data_service),
) -> PasskeyOptions:
    """Step 1 of adding a passkey: options for ``navigator.credentials.create()``."""
    record = await data_service.users.get_user_by_id(user.user_id, fresh=True)
    try:
        return PasskeyOptions(**await auth_service.passkeys.registration_options(record))
    except PasskeyError as e:
        raise _refused(e) from e


@router.post("", response_model=Passkey, status_code=status.HTTP_201_CREATED)
async def register_passkey(
    body: PasskeyRegistration,
    user: TokenPayload = Depends(get_session_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Passkey:
    """Step 2: store the passkey the browser created."""
    try:
        return Passkey(
            **await auth_service.passkeys.register(
                user.user_id, body.challenge_id, body.credential, body.name
            )
        )
    except PasskeyError as e:
        raise _refused(e) from e


@router.get("", response_model=list[Passkey])
async def list_passkeys(
    user: TokenPayload = Depends(get_session_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[Passkey]:
    """Your passkeys (at most 20), newest first."""
    return [Passkey(**p) for p in await auth_service.passkeys.list_for(user.user_id)]


@router.delete("/{passkey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_passkey(
    passkey_id: str,
    user: TokenPayload = Depends(get_session_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Remove one of your passkeys."""
    if not await auth_service.passkeys.remove(user.user_id, passkey_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkey not found")


@router.post("/login/options", response_model=PasskeyOptions)
async def passkey_login_options(
    auth_service: AuthService = Depends(get_auth_service),
) -> PasskeyOptions:
    """Step 1 of signing in: options for ``navigator.credentials.get()`` (no username needed)."""
    try:
        return PasskeyOptions(**await auth_service.passkeys.authentication_options())
    except PasskeyError as e:
        raise _refused(e) from e


@router.post("/login", response_model=LoginResponse)
async def login_with_passkey(
    body: PasskeyLogin,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> JSONResponse:
    """Step 2: verify the passkey and start a session."""
    try:
        login_response = await auth_service.login_with_passkey(
            body.challenge_id, body.credential, extract_device_info(request)
        )
    except PasskeysDisabledError as e:
        raise _refused(e) from e
    except (PasskeyError, AuthenticationError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    response = JSONResponse(content=login_response.model_dump(mode="json"))
    CookieManager.set_auth_cookies(
        response, login_response.tokens, request.app.state.services.config
    )
    return response
