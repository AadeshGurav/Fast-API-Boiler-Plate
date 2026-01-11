"""Models package initialization."""

from __future__ import annotations

from .auth import (
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    TokenPayload,
)
from .oauth import OAuthAccount, OAuthConfig, OAuthProvider, OAuthToken, OAuthUserInfo
from .role import Group, Permission, Role, TemporaryPermission
from .session import DeviceInfo, RefreshToken, Session
from .user import (
    User,
    UserCreate,
    UserInDB,
    UserPublic,
    UserRole,
    UserStatus,
    UserUpdate,
)

__all__ = [
    # User models
    "UserRole",
    "UserStatus",
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserPublic",
    # Role models
    "Permission",
    "Role",
    "Group",
    "TemporaryPermission",
    # Session models
    "DeviceInfo",
    "RefreshToken",
    "Session",
    # Auth models
    "TokenPair",
    "TokenPayload",
    "LoginRequest",
    "RegisterRequest",
    "LoginResponse",
    "RefreshRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    # OAuth models
    "OAuthProvider",
    "OAuthConfig",
    "OAuthToken",
    "OAuthUserInfo",
    "OAuthAccount",
]
