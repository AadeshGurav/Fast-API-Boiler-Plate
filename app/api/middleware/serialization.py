"""Serialization middleware for FastAPI responses."""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import Request
from starlette.responses import JSONResponse, Response

from .base import BaseMiddleware


class JSONEncoder:
    """Custom JSON serializer for common Python/BSON types."""

    @staticmethod
    def serialize(obj: Any) -> Any:
        """Recursively serialize objects for JSON response.

        Args:
        ----
            obj: Object to serialize

        Returns:
        -------
            Serialized object

        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, dict):
            return {key: JSONEncoder.serialize(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [JSONEncoder.serialize(item) for item in obj]
        return obj


class SerializationMiddleware(BaseMiddleware):
    """Middleware to handle automatic serialization of JSON responses."""

    def initialize(self, **kwargs) -> None:
        """Initialize serialization middleware.

        Args:
        ----
            kwargs: Additional keyword arguments

        """
        self.logger.info(
            "SerializationMiddleware initialized",
            extra={"middleware": "SerializationMiddleware"},
        )

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Process request and serialize response data if JSON.

        Args:
        ----
            request: Incoming HTTP request
            call_next: Next callable in middleware chain

        Returns:
        -------
            Response object

        """
        response = await call_next(request)

        if not isinstance(response, JSONResponse):
            self.logger.warning(
                "SerializationMiddleware failed: Response is not a JSONResponse",
                extra={"middleware": "SerializationMiddleware"},
            )
            return response

        try:
            data = json.loads(response.body.decode("utf-8"))

            # Serialize using custom encoder
            serialized_data = JSONEncoder.serialize(data)

            # Return a new JSONResponse with serialized data
            return JSONResponse(
                content=serialized_data,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=response.background,
            )

        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                f"SerializationMiddleware failed: {exc}",
                extra={"middleware": "SerializationMiddleware"},
            )
            # Return original response if serialization fails
            return response
