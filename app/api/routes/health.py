"""Liveness, readiness and metrics endpoints for orchestrators and monitoring."""

from __future__ import annotations

import shutil
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_services
from app.services.registry import Services

router = APIRouter(tags=["health"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


@router.get("/health")
async def health_check(services: Services = Depends(get_services)) -> dict[str, Any]:
    """The process is up (load balancers). Checks no dependencies."""
    return {
        "status": "healthy",
        "timestamp": _now(),
        "service": services.config["app_title"],
        "version": services.config["app_version"],
    }


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness: restart me only if the process itself is wedged."""
    return {"status": "alive", "timestamp": _now()}


@router.get("/ready")
async def readiness_check(
    response: Response, services: Services = Depends(get_services)
) -> dict[str, Any]:
    """Kubernetes readiness: 503 until the database and cache answer."""
    checks: dict[str, dict[str, Any]] = {}
    for name, backend in (
        ("database", services.database_service),
        ("cache", services.cache_service),
    ):
        started = time.perf_counter()
        try:
            healthy = backend.is_connected and await backend.health_check()
        except Exception as e:
            services.logger.error(f"{name} readiness check failed: {e}")
            healthy = False
        checks[name] = {
            "status": "ready" if healthy else "not_ready",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    usage = shutil.disk_usage(services.config["file_storage_base_path"])
    checks["disk"] = {"status": "info", "free_gb": round(usage.free / 1024**3, 2)}

    ready = all(c["status"] == "ready" for n, c in checks.items() if n != "disk")
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", "timestamp": _now(), "checks": checks}


@router.get("/startup")
async def startup_check(
    response: Response, services: Services = Depends(get_services)
) -> dict[str, Any]:
    """Kubernetes startup probe: have the backends connected yet?"""
    checks = {
        "database_connected": services.database_service.is_connected,
        "cache_connected": services.cache_service.is_connected,
    }
    started = all(checks.values())
    if not started:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "started" if started else "starting", "timestamp": _now(), "checks": checks}


@router.get("/metrics", response_class=Response)
async def metrics_endpoint(services: Services = Depends(get_services)) -> Response:
    """Prometheus metrics (admin only, see ``admin_only_paths``)."""
    if services.metrics_service is None:
        return Response(
            content="# metrics are disabled; set metrics_enabled = true\n",
            media_type="text/plain",
        )
    return Response(
        content=services.metrics_service.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


__all__ = ["router"]
