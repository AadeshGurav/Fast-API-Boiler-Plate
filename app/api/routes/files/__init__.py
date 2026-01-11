"""File upload and management routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.files.download import router as download_router
from app.api.routes.files.manage import router as manage_router
from app.api.routes.files.spreadsheet import router as spreadsheet_router
from app.api.routes.files.upload import router as upload_router

router = APIRouter(tags=["Files"])

router.include_router(upload_router, prefix="/upload")
# Register more specific routes first
router.include_router(spreadsheet_router)
router.include_router(download_router)
router.include_router(manage_router)

__all__ = ["router"]
