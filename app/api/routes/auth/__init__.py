"""Main authentication routes combining all auth route modules."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.auth.login import router as login_router
from app.api.routes.auth.password import router as password_router
from app.api.routes.auth.registration import router as registration_router
from app.api.routes.auth.session import router as session_router

# Create main router
router = APIRouter(tags=["Authentication"])

# Include all sub-routers
router.include_router(login_router)
router.include_router(registration_router)
router.include_router(password_router)
router.include_router(session_router)

__all__ = ["router"]
