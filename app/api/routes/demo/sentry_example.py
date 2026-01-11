"""Example routes demonstrating Sentry integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services.sentry import SentryService

router = APIRouter(prefix="/sentry", tags=["sentry"])


async def get_sentry_service() -> SentryService:
    """Get Sentry service from app state."""
    from app import container

    return container.sentry_service()


@router.get("/test-error")
async def test_sentry_error(
    request: Request,
    sentry: SentryService = Depends(get_sentry_service),
):
    """Test endpoint to demonstrate Sentry error tracking."""
    # Add breadcrumb
    sentry.add_breadcrumb(
        message="Testing Sentry error tracking", category="test", level="info"
    )

    # Set some context
    sentry.set_context(
        "test",
        {
            "endpoint": "/sentry/test-error",
            "user_agent": request.headers.get("user-agent", "unknown"),
        },
    )

    # Simulate an error
    raise HTTPException(
        status_code=500, detail="This is a test error for Sentry tracking"
    )


@router.get("/test-performance")
async def test_sentry_performance(
    request: Request,
    sentry: SentryService = Depends(get_sentry_service),
):
    """Test endpoint to demonstrate Sentry performance monitoring."""
    # Start a transaction
    with sentry.start_transaction(
        name="test_performance_endpoint", operation="http.server"
    ) as transaction:
        # Add some spans
        transaction.set_tag("endpoint", "/sentry/test-performance")
        transaction.set_tag("method", "GET")

        # Simulate some work
        import time

        time.sleep(0.1)  # Simulate processing time

        # Add breadcrumb
        sentry.add_breadcrumb(
            message="Performance test completed", category="performance", level="info"
        )

        return {
            "message": "Performance test completed",
            "transaction_id": transaction.trace_id if transaction else None,
        }


@router.get("/test-message")
async def test_sentry_message(
    message: str = "Test message",
    level: str = "info",
    sentry: SentryService = Depends(get_sentry_service),
):
    """Test endpoint to demonstrate Sentry message capture."""
    # Capture a message
    event_id = sentry.capture_message(message=message, level=level)

    return {
        "message": "Message captured in Sentry",
        "event_id": event_id,
        "level": level,
    }


@router.get("/test-user-context")
async def test_sentry_user_context(
    user_id: str = "test-user-123",
    username: str = "testuser",
    email: str = "test@example.com",
    sentry: SentryService = Depends(get_sentry_service),
):
    """Test endpoint to demonstrate Sentry user context."""
    # Set user context
    sentry.set_user(user_id=user_id, username=username, email=email)

    # Add some tags
    sentry.set_tag("user_action", "context_test")
    sentry.set_tag("user_type", "test")

    # Capture a message with user context
    event_id = sentry.capture_message(message="User context test", level="info")

    return {
        "message": "User context set in Sentry",
        "event_id": event_id,
        "user_id": user_id,
    }


@router.get("/test-exception")
async def test_sentry_exception(
    exception_type: str = "ValueError",
    sentry: SentryService = Depends(get_sentry_service),
):
    """Test endpoint to demonstrate Sentry exception capture."""
    # Add breadcrumb before exception
    sentry.add_breadcrumb(
        message="About to raise test exception", category="test", level="warning"
    )

    # Set context
    sentry.set_context(
        "exception_test", {"exception_type": exception_type, "test_mode": True}
    )

    # Raise different types of exceptions
    if exception_type == "ValueError":
        raise ValueError("This is a test ValueError for Sentry")
    elif exception_type == "RuntimeError":
        raise RuntimeError("This is a test RuntimeError for Sentry")
    elif exception_type == "TypeError":
        raise TypeError("This is a test TypeError for Sentry")
    else:
        raise Exception(f"This is a test {exception_type} for Sentry")


@router.get("/status")
async def sentry_status(
    sentry: SentryService = Depends(get_sentry_service),
):
    """Check Sentry service status."""
    return {
        "enabled": sentry.is_enabled(),
        "environment": sentry.environment,
        "dsn_masked": sentry._mask_dsn(sentry.dsn),
        "traces_sample_rate": sentry.traces_sample_rate,
        "profiles_sample_rate": sentry.profiles_sample_rate,
        "performance_monitoring": sentry.enable_performance_monitoring,
        "session_tracking": sentry.enable_session_tracking,
    }
