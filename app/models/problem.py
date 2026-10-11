"""RFC 9457 problem details: the one error shape every endpoint answers with."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PROBLEM_MEDIA_TYPE = "application/problem+json"


class ProblemDetail(BaseModel):
    """An error response (``application/problem+json``)."""

    model_config = ConfigDict(extra="allow")  # extension members: errors, details, ...

    type: str = Field("about:blank", description="Problem type URI")
    title: str = Field(..., description="Short, human-readable summary of the status")
    status: int = Field(..., description="HTTP status code")
    detail: str | None = Field(None, description="What went wrong, for people")
    code: str = Field(..., description="Stable machine-readable code, e.g. validation_error")
    instance: str | None = Field(None, description="The request path")
    errors: list[dict[str, Any]] | None = Field(None, description="Field errors (422)")
    details: Any = Field(None, description="Code-specific data, e.g. mfa_token")


# Statuses any route can answer through the shared middleware and handlers, with their RFC 9110
# names spelled out: http.HTTPStatus phrases changed in Python 3.13 ("Content Too Large"), and the
# committed contract must not depend on the interpreter version.
COMMON_ERRORS = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    413: "Content Too Large",
    422: "Unprocessable Content",
    429: "Too Many Requests",
    503: "Service Unavailable",
}


def problem_responses() -> dict[int | str, dict[str, Any]]:
    """OpenAPI ``responses`` declaring the problem shape for the common error statuses."""
    ref = {"$ref": "#/components/schemas/ProblemDetail"}
    return {
        status: {"description": description, "content": {PROBLEM_MEDIA_TYPE: {"schema": ref}}}
        for status, description in COMMON_ERRORS.items()
    }
