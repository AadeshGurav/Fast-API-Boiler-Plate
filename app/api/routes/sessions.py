"""Session management API routes for viewing and revoking sessions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.container import Container
from app.services.data import DataService
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/sessions", tags=["Session Management"])


@router.get("/active")
async def list_active_sessions(
    current_user: dict = Depends(get_current_user),
    data_service: DataService = Depends(lambda: Container.data_service()),
) -> dict[str, list[dict]]:
    """List active sessions for current user.

    Args:
    ----
        current_user: Current authenticated user
        data_service: Data service instance

    Returns:
    -------
        List of active sessions

    Raises:
    ------
        HTTPException: If user doesn't have permission or retrieval fails

    """
    try:
        # Get user sessions
        sessions = await data_service.sessions.get_user_sessions(
            current_user["user_id"]
        )

        # Filter out revoked sessions
        active_sessions = [
            session for session in sessions if not session.get("revoked_at")
        ]

        # Remove sensitive data
        safe_sessions = []
        for session in active_sessions:
            safe_session = {
                "id": session["id"],
                "device_info": session.get("device_info", {}),
                "created_at": session.get("created_at"),
                "expires_at": session.get("expires_at"),
                "last_used_at": session.get("last_used_at"),
            }
            safe_sessions.append(safe_session)

        return {"sessions": safe_sessions}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active sessions",
        ) from e


@router.delete("/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    data_service: DataService = Depends(lambda: Container.data_service()),
):
    """Revoke specific session.

    Args:
    ----
        session_id: Session ID to revoke
        current_user: Current authenticated user
        data_service: Data service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If user doesn't have permission or revocation fails

    """
    try:
        # Get session to verify ownership
        session = await data_service.sessions.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Check if user owns the session
        if session["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: cannot revoke other user's session",
            )

        # Revoke session
        success = await data_service.sessions.revoke_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke session",
            )

        return {"message": f"Session {session_id} revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session",
        ) from e


@router.delete("/all")
async def revoke_all_sessions(
    current_user: dict = Depends(get_current_user),
    data_service: DataService = Depends(lambda: Container.data_service()),
):
    """Revoke all sessions for current user.

    Args:
    ----
        current_user: Current authenticated user
        data_service: Data service instance

    Returns:
    -------
        Success message with count of revoked sessions

    Raises:
    ------
        HTTPException: If revocation fails

    """
    try:
        # Revoke all user sessions
        revoked_count = await data_service.sessions.revoke_user_sessions(
            current_user["user_id"]
        )

        return {
            "message": "All sessions revoked successfully",
            "revoked_count": revoked_count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke all sessions",
        ) from e


@router.get("/{session_id}")
async def get_session_details(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    data_service: DataService = Depends(lambda: Container.data_service()),
):
    """Get details of specific session.

    Args:
    ----
        session_id: Session ID
        current_user: Current authenticated user
        data_service: Data service instance

    Returns:
    -------
        Session details

    Raises:
    ------
        HTTPException: If user doesn't have permission or session not found

    """
    try:
        # Get session
        session = await data_service.sessions.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Check if user owns the session
        if session["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: cannot view other user's session",
            )

        # Remove sensitive data
        safe_session = {
            "id": session["id"],
            "device_info": session.get("device_info", {}),
            "created_at": session.get("created_at"),
            "expires_at": session.get("expires_at"),
            "last_used_at": session.get("last_used_at"),
            "revoked_at": session.get("revoked_at"),
        }

        return {"session": safe_session}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session details",
        ) from e
