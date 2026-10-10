"""Personal access tokens: create, list and revoke your own.

Send one as ``Authorization: Bearer fabp_pat_...``. Managing tokens needs a signed-in session:
a token cannot mint or revoke tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_auth_service
from app.models.api_token import ApiToken, ApiTokenCreate, ApiTokenCreated, ApiTokenListResponse
from app.models.auth import TokenPayload
from app.services.auth import AuthService
from app.services.auth.api_tokens import ApiTokenError
from app.utils.permissions import get_session_user

router = APIRouter(prefix="/tokens", tags=["API tokens"])


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_api_token(
    body: ApiTokenCreate,
    user: TokenPayload = Depends(get_session_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiTokenCreated:
    """Issue a token limited to ``scopes``. The secret is in this response only."""
    try:
        token, record = await auth_service.api_tokens.create(
            user.user_id, body.name, body.scopes, body.expires_in_days
        )
    except ApiTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiTokenCreated(token=token, **record)


@router.get("", response_model=ApiTokenListResponse)
async def list_api_tokens(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: TokenPayload = Depends(get_session_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiTokenListResponse:
    """Your tokens, newest first (never their secrets)."""
    records, total = await auth_service.api_tokens.list_for(user.user_id, page, page_size)
    return ApiTokenListResponse(
        tokens=[ApiToken(**r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        has_next=page * page_size < total,
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_token(
    token_id: str,
    user: TokenPayload = Depends(get_session_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Revoke one of your tokens; it stops working immediately."""
    if not await auth_service.api_tokens.revoke(user.user_id, token_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
