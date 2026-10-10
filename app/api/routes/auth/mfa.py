"""Two-factor authentication: set up, confirm, sign in with a code, recovery codes, turn off."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import get_auth_service
from app.models.auth import LoginResponse, TokenPayload
from app.models.mfa import (
    MFACode,
    MFALoginRequest,
    MFAStatus,
    PasswordAndCode,
    PasswordConfirmation,
    RecoveryCodes,
    TOTPSetup,
)
from app.services.auth import AuthenticationError, AuthService, MFAError
from app.services.auth.mfa import MFAStateError
from app.utils.cookie_manager import CookieManager
from app.utils.permissions import get_current_user
from app.utils.utils import extract_device_info

router = APIRouter(prefix="/auth", tags=["Two-factor authentication"])


def _refused(e: MFAError) -> HTTPException:
    code = status.HTTP_409_CONFLICT if isinstance(e, MFAStateError) else status.HTTP_403_FORBIDDEN
    return HTTPException(status_code=code, detail=str(e))


@router.post("/login/mfa", response_model=LoginResponse)
async def login_with_mfa_code(
    body: MFALoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> JSONResponse:
    """Finish a two-factor sign-in with an authenticator or recovery code."""
    try:
        login_response, remember_me = await auth_service.complete_mfa_login(
            body.mfa_token, body.code, extract_device_info(request)
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    response = JSONResponse(content=login_response.model_dump(mode="json"))
    CookieManager.set_auth_cookies(
        response, login_response.tokens, request.app.state.services.config, remember_me
    )
    return response


@router.get("/mfa", response_model=MFAStatus)
async def get_mfa_status(
    user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> MFAStatus:
    """Whether two-factor sign-in is on, and how many recovery codes are left."""
    return MFAStatus(**await auth_service.mfa.status(user.user_id))


@router.post("/mfa/totp", response_model=TOTPSetup, status_code=status.HTTP_201_CREATED)
async def start_totp_setup(
    body: PasswordConfirmation,
    user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> TOTPSetup:
    """Begin setup: returns the secret to add to an authenticator app. Not active until confirmed."""
    try:
        return TOTPSetup(**await auth_service.mfa.start_totp(user.user_id, body.password))
    except MFAError as e:
        raise _refused(e) from e


@router.post("/mfa/totp/confirm", response_model=RecoveryCodes)
async def confirm_totp_setup(
    body: MFACode,
    user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> RecoveryCodes:
    """Turn two-factor sign-in on with a first code; returns recovery codes, shown once."""
    try:
        return RecoveryCodes(
            recovery_codes=await auth_service.mfa.confirm_totp(user.user_id, body.code)
        )
    except MFAError as e:
        raise _refused(e) from e


@router.post("/mfa/recovery-codes", response_model=RecoveryCodes)
async def regenerate_recovery_codes(
    body: PasswordAndCode,
    user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> RecoveryCodes:
    """Replace all recovery codes; the old ones stop working."""
    try:
        codes = await auth_service.mfa.regenerate_recovery_codes(
            user.user_id, body.password, body.code
        )
    except MFAError as e:
        raise _refused(e) from e
    return RecoveryCodes(recovery_codes=codes)


@router.delete("/mfa/totp", status_code=status.HTTP_204_NO_CONTENT)
async def disable_totp(
    body: PasswordAndCode,
    user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Turn two-factor sign-in off (password plus a current or recovery code)."""
    try:
        await auth_service.mfa.disable(user.user_id, body.password, body.code)
    except MFAError as e:
        raise _refused(e) from e
