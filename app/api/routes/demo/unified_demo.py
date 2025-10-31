"""Unified demo router combining authentication, admin, and API demo functionality."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.utils.permissions import get_current_user

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Create unified demo router
demo_router = APIRouter(prefix="/demo", tags=["demo"])


# Client-driven demo: templates render and client-side JS calls real API


# Demo Home Page
@demo_router.get("/", response_class=HTMLResponse)
async def demo_home(request: Request):
    """Demo home page with navigation to all demo features."""
    return templates.TemplateResponse(
        "demo/index.html", {"request": request, "title": "FastAPI Demo Home"}
    )


# Authentication Demo Routes
@demo_router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse(
        "demo/auth/login.html", {"request": request, "title": "Login - FastAPI Demo"}
    )


# POST handled on client via fetch to /api/v1/auth/login


@demo_router.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse(
        "demo/auth/register.html",
        {"request": request, "title": "Register - FastAPI Demo"},
    )


# POST handled on client via fetch to /api/v1/auth/register


@demo_router.get("/auth/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard shell; client fetches user via /api/v1/auth/me."""
    # Provide minimal context to avoid template errors before client fills
    placeholder_user = {
        "username": "",
        "profile": {"first_name": "", "last_name": "", "email": ""},
        "role": "user",
        "groups": [],
        "status": "",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "permissions": [],
        "last_login": "",
    }
    return templates.TemplateResponse(
        "demo/auth/dashboard.html",
        {
            "request": request,
            "user": placeholder_user,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": "Dashboard - FastAPI Demo",
        },
    )


@demo_router.get("/auth/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """Logout user."""
    # Client tokens are cleared by JS on landing; server just redirects
    response = RedirectResponse(url="/demo/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session_token")
    return response


@demo_router.get("/auth/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(
            url="/demo/auth/login", status_code=status.HTTP_302_FOUND
        )

    return templates.TemplateResponse(
        "demo/auth/profile.html",
        {"request": request, "user": user, "title": "Profile - FastAPI Demo"},
    )


# Admin Demo Routes
@demo_router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Admin panel shell; client JS fetches RBAC/metrics from API."""
    admin_data = {
        "total_users": 0,
        "active_users": 0,
        "total_roles": 0,
        "total_permissions": 0,
        "roles": [],
        "permissions": [],
        "groups": [],
        "metrics": {},
    }
    return templates.TemplateResponse(
        "demo/admin/panel.html",
        {
            "request": request,
            "admin_data": admin_data,
            "title": "Admin Panel - FastAPI Demo",
        },
    )


async def get_all_users_from_api(client, headers):
    """Helper function to get all users from API."""
    try:
        # This would need to be implemented in the actual API
        # For now, return empty list
        return []
    except Exception:
        return []


@demo_router.get("/admin/users", response_class=HTMLResponse)
async def manage_users(request: Request):
    """Manage users page."""
    users = []
    return templates.TemplateResponse(
        "demo/admin/users.html",
        {"request": request, "users": users, "title": "Manage Users - FastAPI Demo"},
    )


@demo_router.get("/admin/roles", response_class=HTMLResponse)
async def manage_roles(request: Request):
    """Manage roles page."""
    roles = []
    return templates.TemplateResponse(
        "demo/admin/roles.html",
        {"request": request, "roles": roles, "title": "Manage Roles - FastAPI Demo"},
    )


@demo_router.get("/admin/permissions", response_class=HTMLResponse)
async def manage_permissions(request: Request):
    """Manage permissions page."""
    permissions = []
    return templates.TemplateResponse(
        "demo/admin/permissions.html",
        {
            "request": request,
            "permissions": permissions,
            "title": "Manage Permissions - FastAPI Demo",
        },
    )


@demo_router.get("/admin/settings", response_class=HTMLResponse)
async def system_settings(request: Request):
    """System settings page."""
    # Simple defaults; client can augment if needed
    settings = {
        "app_name": "FastAPI Demo",
        "version": "1.0.0",
        "debug": True,
        "max_users": 1000,
        "session_timeout": 3600,
        "enable_registration": True,
        "require_email_verification": False,
    }
    return templates.TemplateResponse(
        "demo/admin/settings.html",
        {
            "request": request,
            "settings": settings,
            "title": "System Settings - FastAPI Demo",
        },
    )


@demo_router.get("/admin/metrics", response_class=HTMLResponse)
async def system_metrics(request: Request):
    """System metrics page."""
    metrics = {
        "requests_total": 0,
        "active_users": 0,
        "response_time_avg": 0,
        "error_rate": 0,
        "memory_usage": 0,
        "cpu_usage": 0,
    }
    return templates.TemplateResponse(
        "demo/admin/metrics.html",
        {
            "request": request,
            "metrics": metrics,
            "title": "System Metrics - FastAPI Demo",
        },
    )


# API Demo Routes
@demo_router.get("/api", response_class=HTMLResponse)
async def api_demo(request: Request):
    """API demo page with real data."""
    # Render shell; client lists/calls endpoints directly
    api_endpoints = []
    return templates.TemplateResponse(
        "demo/api/demo.html",
        {
            "request": request,
            "api_endpoints": api_endpoints,
            "title": "API Demo - FastAPI Demo",
        },
    )


@demo_router.get("/api/test", response_class=HTMLResponse)
async def api_test(request: Request):
    """API test page."""
    return templates.TemplateResponse(
        "demo/api/test.html",
        {"request": request, "title": "API Test - FastAPI Demo"},
    )


@demo_router.get("/api/info", response_class=HTMLResponse)
async def api_info(request: Request):
    """API info page."""
    # Static info; developers can visit /docs for full spec
    api_info = {
        "version": "1.0.0",
        "title": "FastAPI Demo API",
        "description": "A comprehensive FastAPI demo with authentication, RBAC, and monitoring",
        "endpoints": "See Swagger UI",
        "features": [
            "JWT Authentication",
            "Role-Based Access Control",
            "OAuth Integration",
            "Metrics & Monitoring",
            "Redis Caching",
            "MongoDB Storage",
            "Session Management",
        ],
    }
    return templates.TemplateResponse(
        "demo/api/info.html",
        {
            "request": request,
            "api_info": api_info,
            "title": "API Info - FastAPI Demo",
        },
    )


@demo_router.get("/api/health", response_class=HTMLResponse)
async def health_check(
    request: Request,
):
    """Health check page with real data."""
    # Client should call /api/v1/health directly; provide basic placeholder
    health_data = {
        "status": "unknown",
        "timestamp": datetime.now().isoformat(),
        "service": "FastAPI Demo",
        "version": "1.0.0",
        "environment": "development",
        "uptime": "N/A",
        "services": {},
    }

    return templates.TemplateResponse(
        "demo/api/health.html",
        {
            "request": request,
            "health_data": health_data,
            "title": "Health Check - FastAPI Demo",
        },
    )


@demo_router.get("/api/status", response_class=HTMLResponse)
async def system_status(request: Request):
    """System status page."""
    status_data = {
        "system": "unknown",
        "load": "unknown",
        "memory": "unknown",
        "disk": "unknown",
        "network": "unknown",
        "last_restart": "unknown",
        "version": "1.0.0",
    }
    return templates.TemplateResponse(
        "demo/api/status.html",
        {
            "request": request,
            "status_data": status_data,
            "title": "System Status - FastAPI Demo",
        },
    )


@demo_router.get("/api/docs", response_class=HTMLResponse)
async def docs_redirect(request: Request):
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs", status_code=status.HTTP_302_FOUND)


@demo_router.get("/api/redoc", response_class=HTMLResponse)
async def redoc_redirect(request: Request):
    """Redirect to ReDoc documentation."""
    return RedirectResponse(url="/redoc", status_code=status.HTTP_302_FOUND)
