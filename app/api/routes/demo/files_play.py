"""File processing and manipulation demo routes (after upload)."""

from __future__ import annotations

import base64
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from app import container as app_container
from app.services.file import FileService
from app.utils.demo_context import get_demo_user_context
from app.utils.permissions import get_current_user

files_play_router = APIRouter(prefix="/demo/files", tags=["File Processing Demo"])


@files_play_router.get("/play", response_class=HTMLResponse)
async def files_play_page(request: Request) -> HTMLResponse:
    """File processing and manipulation demo page.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        HTML response with file processing page

    """
    user = await get_demo_user_context(request)
    return request.app.state.templates.TemplateResponse(
        "demo/files/play.html",
        {"request": request, "title": "File Processing Demo", "user": user},
    )


@files_play_router.get("/play/api/{file_id}/read", response_class=JSONResponse)
async def read_file_api(
    file_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> JSONResponse:
    """Read and process file content API endpoint.

    Args:
    ----
        file_id: File ID
        request: FastAPI request object
        current_user: Current authenticated user
        file_service: FileService instance

    Returns:
    -------
        JSON response with processed file content

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        result = await file_service.download_file(file_id, user_id=user_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        file_content, file_metadata = result

        # Handle both dict and FileMetadata object
        if isinstance(file_metadata, dict):
            filename = file_metadata.get("filename", "")
            content_type = file_metadata.get("content_type", "")
            size = file_metadata.get("size", 0)
        else:
            filename = file_metadata.filename
            content_type = file_metadata.content_type
            size = file_metadata.size

        processed_data = {
            "file_id": file_id,
            "filename": filename,
            "content_type": content_type,
            "size": size,
            "is_text": content_type.startswith("text"),
            "is_image": content_type.startswith("image"),
            "is_json": content_type == "application/json",
        }

        if content_type.startswith("text"):
            try:
                text_content = file_content.decode("utf-8", errors="ignore")
                processed_data["text_content"] = text_content
                processed_data["line_count"] = len(text_content.splitlines())
                processed_data["word_count"] = len(text_content.split())
                processed_data["char_count"] = len(text_content)
            except (UnicodeDecodeError, ValueError) as e:
                processed_data["error"] = f"Failed to decode text: {str(e)}"

        elif content_type == "application/json":
            try:
                json_content = file_content.decode("utf-8", errors="ignore")
                import json

                parsed_json = json.loads(json_content)
                processed_data["json_content"] = parsed_json
                processed_data["json_keys"] = (
                    list(parsed_json.keys()) if isinstance(parsed_json, dict) else []
                )
            except (json.JSONDecodeError, ValueError) as e:
                processed_data["error"] = f"Failed to parse JSON: {str(e)}"

        elif content_type.startswith("image/"):
            try:
                from PIL import Image

                image = Image.open(BytesIO(file_content))
                processed_data["image_width"] = image.width
                processed_data["image_height"] = image.height
                processed_data["image_format"] = image.format
                processed_data["image_mode"] = image.mode

                img_base64 = base64.b64encode(file_content).decode("utf-8")
                processed_data["image_base64"] = (
                    f"data:{content_type};base64,{img_base64}"
                )
            except (OSError, ValueError) as e:
                processed_data["error"] = f"Failed to process image: {str(e)}"

        return JSONResponse(content=processed_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}",
        ) from e


@files_play_router.post("/play/api/{file_id}/transform", response_class=JSONResponse)
async def transform_file_api(
    file_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> JSONResponse:
    """Transform file content API endpoint.

    Args:
    ----
        file_id: File ID
        request: FastAPI request object
        current_user: Current authenticated user
        file_service: FileService instance

    Returns:
    -------
        JSON response with transformation result

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        body = await request.json()
        transform_type = body.get("transform_type", "uppercase")

        result = await file_service.download_file(file_id, user_id=user_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        file_content, file_metadata = result

        if not file_metadata.content_type.startswith("text"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transformation only supported for text files",
            )

        text_content = file_content.decode("utf-8", errors="ignore")

        transformed_content = text_content
        if transform_type == "uppercase":
            transformed_content = text_content.upper()
        elif transform_type == "lowercase":
            transformed_content = text_content.lower()
        elif transform_type == "reverse":
            transformed_content = text_content[::-1]
        elif transform_type == "word_count":
            words = text_content.split()
            transformed_content = f"Word count: {len(words)}"
        elif transform_type == "line_count":
            lines = text_content.splitlines()
            transformed_content = f"Line count: {len(lines)}"

        return JSONResponse(
            content={
                "file_id": file_id,
                "transform_type": transform_type,
                "original_length": len(text_content),
                "transformed_length": len(transformed_content),
                "transformed_content": transformed_content,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transform file: {str(e)}",
        ) from e


__all__ = ["files_play_router"]
