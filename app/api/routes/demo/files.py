"""File upload and management demo routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.utils.demo_context import get_demo_user_context

files_router = APIRouter(prefix="/demo/files", tags=["File Upload Demo"])


@files_router.get("/", response_class=HTMLResponse)
async def files_page(request: Request) -> HTMLResponse:
    """File management demo page.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        HTML response with file management page

    """
    user = await get_demo_user_context(request)
    return request.app.state.templates.TemplateResponse(
        "demo/files/files.html",
        {"request": request, "title": "File Management Demo", "user": user},
    )


__all__ = ["files_router"]
