"""Session management API: list and revoke the caller's own sessions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service, get_data_service
from app.models.auth import TokenPayload
from app.services.auth import AuthService
from app.services.data import DataService
from app.services.data.sessions_ops import is_session_active
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/sessions", tags=["Session Management"])


def _public_view(session: dict[str, Any], current_sid: str | None) -> dict[str, Any]:
    """Session fields that are safe to show (never token hashes)."""
    return {
        "id": session["id"],
        "current": session["id"] == current_sid,
        "device_info": session.get("device_info", {}),
        "created_at": session.get("created_at"),
        "expires_at": session.get("expires_at"),
        "last_used_at": session.get("last_used_at"),
    }


async def _own_session(
    session_id: str, user: TokenPayload, data_service: DataService
) -> dict[str, Any]:
    """The caller's session, or 404 (also for other users' sessions, so ids can't be probed)."""
    session = await data_service.sessions.get_session(session_id)
    if not session or session.get("user_id") != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.get("/active")
async def list_active_sessions(
    user: TokenPayload = Depends(get_current_user),
    data_service: DataService = Depends(get_data_service),
) -> dict[str, list[dict]]:
    """List the caller's sessions that can still be used."""
    sessions = await data_service.sessions.get_user_sessions(user.user_id)
    return {"sessions": [_public_view(s, user.sid) for s in sessions if is_session_active(s)]}


# Declared before "/{session_id}" so "all" is not captured as a session id.
@router.delete("/all")
async def revoke_all_sessions(
    user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Revoke every session of the caller, including the current one."""
    revoked = await auth_service.logout_all_devices(user.user_id)
    return {"message": "All sessions revoked successfully", "revoked_count": revoked}


@router.get("/{session_id}")
async def get_session_details(
    session_id: str,
    user: TokenPayload = Depends(get_current_user),
    data_service: DataService = Depends(get_data_service),
) -> dict[str, Any]:
    """Details of one of the caller's sessions."""
    return _public_view(await _own_session(session_id, user, data_service), user.sid)


@router.delete("/{session_id}")
async def revoke_session(
    session_id: str,
    user: TokenPayload = Depends(get_current_user),
    data_service: DataService = Depends(get_data_service),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Revoke one of the caller's sessions."""
    await _own_session(session_id, user, data_service)
    if not await auth_service.logout(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to revoke session"
        )
    return {"message": f"Session {session_id} revoked successfully"}


__all__ = ["router"]
