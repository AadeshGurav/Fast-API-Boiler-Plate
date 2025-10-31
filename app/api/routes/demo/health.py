"""Health check endpoints for monitoring and orchestration."""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from prometheus_client import CONTENT_TYPE_LATEST

from app.services.data_service import DataService
from app.services.logger import Logger
from app.services.metrics import MetricsService
from config import Config

router = APIRouter(tags=["health"])


async def get_dependencies() -> (
    tuple[DataService, Logger, Config, MetricsService | None]
):
    """Get common dependencies from the app's container."""
    from app import container  # Use the same container instance as the app

    metrics_service = None

    try:
        metrics_service = container.metrics_service()
    except Exception:  # noqa: BLE001
        pass

    return (
        container.data_service(),
        container.logger(),
        container.config(),
        metrics_service,
    )


@router.get("/health")
async def health_check(
    dependencies: tuple[DataService, Logger, Config, MetricsService | None] = Depends(
        get_dependencies
    ),
) -> dict[str, Any]:
    """Basic health check endpoint.

    Returns 200 if the application is running.
    Used by load balancers for basic health monitoring.
    """
    data_service, logger, config, _ = dependencies

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": config.get("app_title", "fastapi-app"),
        "version": config.get("app_version", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@router.get("/ready")
async def readiness_check(
    response: Response,
    dependencies: tuple[DataService, Logger, Config, MetricsService | None] = Depends(
        get_dependencies
    ),
) -> dict[str, Any]:
    """Readiness check endpoint.

    Checks if all dependencies are ready to handle requests.
    Returns 503 if any dependency is not ready.
    Used by orchestrators (k8s) to determine if the pod should receive traffic.
    """
    data_service, logger, config, _ = dependencies

    checks = {}
    all_ready = True
    start_time = time.time()

    # Check MongoDB
    try:
        backend = data_service.database_service.backend
        if hasattr(backend, "client") and backend.client is not None:
            mongo_healthy = await backend.health_check()
            checks["mongodb"] = {
                "status": "ready" if mongo_healthy else "not_ready",
                "type": "database",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
            }
            if not mongo_healthy:
                all_ready = False
        else:
            checks["mongodb"] = {
                "status": "not_connected",
                "type": "database",
                "error": "Client not initialized",
            }
            all_ready = False
    except Exception as e:  # noqa: BLE001
        logger.error(f"MongoDB health check failed: {str(e)}")
        checks["mongodb"] = {"status": "error", "type": "database", "error": str(e)}
        all_ready = False

    # Check Redis
    redis_start = time.time()
    try:
        redis_client = data_service.cache_service.redis_client
        if hasattr(redis_client, "client") and redis_client.client is not None:
            redis_healthy = await redis_client.health_check()
            checks["redis"] = {
                "status": "ready" if redis_healthy else "not_ready",
                "type": "cache",
                "latency_ms": round((time.time() - redis_start) * 1000, 2),
            }
            if not redis_healthy:
                all_ready = False
        else:
            checks["redis"] = {
                "status": "not_connected",
                "type": "cache",
                "error": "Client not initialized",
            }
            all_ready = False
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        checks["redis"] = {"status": "error", "type": "cache", "error": str(e)}
        all_ready = False

    # Check disk space
    try:
        stat = os.statvfs("/")
        disk_free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        disk_total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
        disk_usage_percent = ((disk_total_gb - disk_free_gb) / disk_total_gb) * 100

        disk_healthy = disk_usage_percent < 90  # Alert if > 90% used
        checks["disk"] = {
            "status": "ready" if disk_healthy else "warning",
            "type": "resource",
            "usage_percent": round(disk_usage_percent, 2),
            "free_gb": round(disk_free_gb, 2),
        }
        if disk_usage_percent > 95:
            all_ready = False
    except Exception as e:
        logger.error(f"Disk check failed: {str(e)}")
        checks["disk"] = {"status": "error", "type": "resource", "error": str(e)}

    # Check memory
    try:
        with open("/proc/meminfo") as f:
            meminfo = dict(
                (line.split()[0].rstrip(":"), int(line.split()[1]))
                for line in f.readlines()
            )
        mem_total = meminfo["MemTotal"] / 1024  # Convert to MB
        mem_available = meminfo["MemAvailable"] / 1024
        mem_usage_percent = ((mem_total - mem_available) / mem_total) * 100

        memory_healthy = mem_usage_percent < 90
        checks["memory"] = {
            "status": "ready" if memory_healthy else "warning",
            "type": "resource",
            "usage_percent": round(mem_usage_percent, 2),
            "available_mb": round(mem_available, 2),
        }
    except Exception:  # noqa: BLE001
        # Not critical if we can't read memory
        checks["memory"] = {"status": "unknown", "type": "resource"}

    # Overall status
    overall_status = "ready" if all_ready else "not_ready"
    total_latency = round((time.time() - start_time) * 1000, 2)

    # Set appropriate status code
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "total_latency_ms": total_latency,
        "service": config.get("app_title", "fastapi-app"),
        "version": config.get("app_version", "1.0.0"),
    }


@router.get("/startup")
async def startup_check(
    dependencies: tuple[DataService, Logger, Config, MetricsService | None] = Depends(
        get_dependencies
    ),
) -> dict[str, Any]:
    """Startup probe endpoint.

    Used by orchestrators to know when the application has started successfully.
    Can perform one-time initialization checks.
    """
    data_service, logger, config, _ = dependencies

    # Check if essential services are initialized
    startup_checks = {
        "config_loaded": bool(config.data),
        "logger_initialized": logger._initialized,
        "database_connected": (
            hasattr(data_service.database_service.backend, "client")
            and data_service.database_service.backend.client is not None
        ),
        "cache_connected": (
            hasattr(data_service.cache_service.redis_client, "client")
            and data_service.cache_service.redis_client.client is not None
        ),
    }

    all_started = all(startup_checks.values())

    return {
        "status": "started" if all_started else "starting",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": startup_checks,
        "service": config.get("app_title", "fastapi-app"),
        "version": config.get("app_version", "1.0.0"),
    }


@router.get("/metrics", response_class=Response)
async def metrics_endpoint(
    dependencies: tuple[DataService, Logger, Config, MetricsService | None] = Depends(
        get_dependencies
    ),
) -> Response:
    """Prometheus metrics endpoint.

    Returns application metrics in Prometheus text format.
    """
    _, _, _, metrics_service = dependencies

    if metrics_service and metrics_service.enabled:
        # Generate Prometheus metrics
        metrics_data = metrics_service.generate_metrics()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    else:
        # Return basic metrics if service not available
        metrics = []
        metrics.append("# HELP app_info Application information")
        metrics.append("# TYPE app_info gauge")
        metrics.append('app_info{service="fastapi-app",version="1.0.0"} 1')

        return Response(content="\n".join(metrics), media_type="text/plain")


@router.get("/live")
async def liveness_check() -> dict[str, Any]:
    """Kubernetes liveness probe endpoint.

    Simple check that the application process is alive.
    Should not check external dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
