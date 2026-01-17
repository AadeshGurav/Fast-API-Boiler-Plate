"""Unified demo router combining authentication, admin, and API demo functionality."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app import container
from app.services.data import DataService
from app.utils.demo_context import get_demo_user_context
from app.utils.permissions import get_current_user

# Create unified demo router
demo_router = APIRouter(prefix="/demo", tags=["demo"])


# Client-driven demo: templates render and client-side JS calls real API


# Demo Home Page
@demo_router.get("/", response_class=HTMLResponse)
async def demo_home(request: Request):
    """Demo home page with navigation to all demo features."""
    user = await get_demo_user_context(request)
    return request.app.state.templates.TemplateResponse(
        "demo/index.html",
        {"request": request, "title": "FastAPI Demo Home", "user": user},
    )


# Authentication Demo Routes
@demo_router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    user = await get_demo_user_context(request)
    return request.app.state.templates.TemplateResponse(
        "demo/auth/login.html",
        {"request": request, "title": "Login - FastAPI Demo", "user": user},
    )


# POST handled on client via fetch to /api/v1/auth/login


@demo_router.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    user = await get_demo_user_context(request)
    return request.app.state.templates.TemplateResponse(
        "demo/auth/register.html",
        {"request": request, "title": "Register - FastAPI Demo", "user": user},
    )


# POST handled on client via fetch to /api/v1/auth/register


@demo_router.get("/auth/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard shell; client fetches user via /api/v1/auth/me."""
    try:
        token_payload = await get_current_user(request)
        if not token_payload:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Get full user data from database
        data_service: DataService = container.data_service()
        user_data = await data_service.users.get_user_by_id(token_payload.user_id)

        if not user_data:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Extract metadata for profile info
        metadata = user_data.get("metadata", {})
        created_at = user_data.get("created_at")
        if isinstance(created_at, str):
            from datetime import datetime as dt

            try:
                created_at = dt.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = datetime.now()

        # Get sessions and login attempts from user data
        sessions = user_data.get("sessions", [])
        login_attempts = user_data.get(
            "login_attempts_history", user_data.get("login_attempts", [])
        )
        if not isinstance(login_attempts, list):
            login_attempts = []

        # Format dates for JSON serialization and display
        # Validate dates are not in the future
        created_at_str = None
        created_at_formatted = None
        if created_at:
            if hasattr(created_at, "strftime"):
                # Ensure date is not in the future
                if created_at > datetime.now():
                    created_at = datetime.now()
                created_at_str = created_at.strftime("%Y-%m-%d")
                created_at_formatted = created_at.strftime("%B %d, %Y")
            else:
                created_at_str = str(created_at)
                created_at_formatted = created_at_str

        last_login_str = None
        last_login = user_data.get("last_login")
        if last_login:
            if hasattr(last_login, "strftime"):
                last_login_str = last_login.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_login_str = str(last_login)

        def convert_datetime_to_str(obj: Any) -> Any:
            """Recursively convert datetime objects to strings."""
            if hasattr(obj, "strftime"):
                return obj.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(obj, dict):
                return {
                    key: convert_datetime_to_str(value) for key, value in obj.items()
                }
            if isinstance(obj, list):
                return [convert_datetime_to_str(item) for item in obj]
            return obj

        # Convert datetime objects in sessions to strings (recursively)
        formatted_sessions = convert_datetime_to_str(sessions)

        # Convert datetime objects in login_attempts to strings (recursively)
        formatted_login_attempts = convert_datetime_to_str(login_attempts)

        # Determine role - prioritize "admin" in roles array, then first role, then role field
        roles_list = user_data.get("roles", [])
        if "admin" in roles_list:
            display_role = "admin"
        elif roles_list:
            display_role = roles_list[0]
        else:
            display_role = user_data.get("role", "user")

        # Convert to dictionary format for template with profile structure
        user_dict = {
            "id": user_data.get("id"),
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "role": display_role,
            "roles": roles_list,
            "groups": user_data.get("groups", []),
            "status": user_data.get("status", "active"),
            "permissions": token_payload.permissions,
            "created_at": created_at_formatted or created_at_str,
            "created_at_raw": created_at_str,
            "last_login": last_login_str,
            "sessions": formatted_sessions,
            "login_attempts": formatted_login_attempts,
            "profile": {
                "first_name": metadata.get("first_name", ""),
                "last_name": metadata.get("last_name", ""),
                "email": user_data.get("email", ""),
            },
        }

        # Final pass: recursively convert any remaining datetime objects
        user_dict = convert_datetime_to_str(user_dict)

        return request.app.state.templates.TemplateResponse(
            "demo/auth/dashboard.html",
            {
                "request": request,
                "user": user_dict,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": "Dashboard - FastAPI Demo",
            },
        )
    except (HTTPException, ValueError, KeyError, AttributeError):
        return RedirectResponse(
            url="/demo/auth/login", status_code=status.HTTP_302_FOUND
        )


@demo_router.get("/auth/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """Logout user."""
    from app.utils.cookie_manager import CookieManager

    # Try to get session ID and revoke it
    try:
        from app import container

        session_id = getattr(request.state, "session_id", None)
        if session_id:
            auth_service = container.auth_service()
            await auth_service.logout(session_id)
    except Exception:
        pass  # Continue with cookie clearing even if session revocation fails

    # Client tokens are cleared by JS on landing; server clears cookies and redirects
    response = RedirectResponse(url="/demo/", status_code=status.HTTP_302_FOUND)
    CookieManager.delete_auth_cookies(response)
    # Clear session cookie
    config = getattr(request.app.state, "config", None)
    CookieManager.delete_session_cookie(response, config)
    return response


@demo_router.get("/auth/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page."""
    try:
        token_payload = await get_current_user(request)
        if not token_payload:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Get full user data from database
        data_service: DataService = container.data_service()
        user_data = await data_service.users.get_user_by_id(token_payload.user_id)

        if not user_data:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Format dates for JSON serialization and display
        created_at = user_data.get("created_at")
        created_at_str = None
        created_at_formatted = None
        if created_at:
            if hasattr(created_at, "strftime"):
                created_at_str = created_at.strftime("%Y-%m-%d")
                created_at_formatted = created_at.strftime("%B %d, %Y")
            else:
                created_at_str = str(created_at)
                created_at_formatted = created_at_str

        last_login = user_data.get("last_login")
        last_login_str = None
        if last_login:
            if hasattr(last_login, "strftime"):
                last_login_str = last_login.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_login_str = str(last_login)

        # Convert to dictionary format for template
        user_dict = {
            "id": user_data.get("id"),
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "role": user_data.get("roles", [])[0] if user_data.get("roles") else "user",
            "roles": user_data.get("roles", []),
            "groups": user_data.get("groups", []),
            "status": user_data.get("status", "active"),
            "permissions": token_payload.permissions,
            "member_since": created_at_formatted or created_at_str or "2024-01-01",
            "last_login": last_login_str or "Just now",
        }

        return request.app.state.templates.TemplateResponse(
            "demo/auth/profile.html",
            {"request": request, "user": user_dict, "title": "Profile - FastAPI Demo"},
        )
    except (HTTPException, ValueError, KeyError, AttributeError):
        return RedirectResponse(
            url="/demo/auth/login", status_code=status.HTTP_302_FOUND
        )


@demo_router.get("/auth/sessions", response_class=HTMLResponse)
async def sessions_page(request: Request):
    """User sessions management page."""
    try:
        token_payload = await get_current_user(request)
        if not token_payload:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Get full user data from database
        data_service: DataService = container.data_service()
        user_data = await data_service.users.get_user_by_id(token_payload.user_id)

        if not user_data:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Get sessions from database, not user object
        sessions = await data_service.sessions.get_user_sessions(token_payload.user_id)

        # Filter out revoked sessions
        active_sessions = [
            session for session in sessions if not session.get("revoked_at")
        ]

        # Format sessions for template (similar to dashboard route)
        formatted_sessions = []
        for session in active_sessions:
            created_at = session.get("created_at")
            expires_at = session.get("expires_at")
            device_info = session.get("device_info", {})

            # Handle timestamp if expires_at is a number
            if isinstance(expires_at, (int, float)):
                from datetime import datetime

                expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)

            formatted_session = {
                "id": session.get("id"),
                "device_info": device_info,
                "created_at": created_at,
                "expires_at": expires_at,
                "revoked_at": session.get("revoked_at"),
                "is_active": not session.get("revoked_at"),
            }
            formatted_sessions.append(formatted_session)

        # Determine role - prioritize "admin" in roles array, then first role, then role field
        roles_list = user_data.get("roles", [])
        if "admin" in roles_list:
            display_role = "admin"
        elif roles_list:
            display_role = roles_list[0]
        else:
            display_role = user_data.get("role", "user")

        # Convert to dictionary format for template
        user_dict = {
            "id": user_data.get("id"),
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "role": display_role,
            "roles": roles_list,
            "groups": user_data.get("groups", []),
            "status": user_data.get("status", "active"),
            "sessions": formatted_sessions,
        }

        return request.app.state.templates.TemplateResponse(
            "demo/auth/sessions.html",
            {"request": request, "user": user_dict, "title": "Sessions - FastAPI Demo"},
        )
    except (HTTPException, ValueError, KeyError, AttributeError):
        return RedirectResponse(
            url="/demo/auth/login", status_code=status.HTTP_302_FOUND
        )


@demo_router.get("/auth/login-attempts", response_class=HTMLResponse)
async def login_attempts_page(request: Request):
    """User login attempts history page."""
    try:
        token_payload = await get_current_user(request)
        if not token_payload:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Get full user data from database
        data_service: DataService = container.data_service()
        user_data = await data_service.users.get_user_by_id(token_payload.user_id)

        if not user_data:
            return RedirectResponse(
                url="/demo/auth/login", status_code=status.HTTP_302_FOUND
            )

        # Get login attempts from user data
        login_attempts = user_data.get(
            "login_attempts_history", user_data.get("login_attempts", [])
        )
        if not isinstance(login_attempts, list):
            login_attempts = []

        # Convert to dictionary format for template
        user_dict = {
            "id": user_data.get("id"),
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "role": user_data.get("roles", [])[0] if user_data.get("roles") else "user",
            "roles": user_data.get("roles", []),
            "groups": user_data.get("groups", []),
            "status": user_data.get("status", "active"),
            "login_attempts": login_attempts,
        }

        return request.app.state.templates.TemplateResponse(
            "demo/auth/login_attempts.html",
            {
                "request": request,
                "user": user_dict,
                "title": "Login Attempts - FastAPI Demo",
            },
        )
    except (HTTPException, ValueError, KeyError, AttributeError):
        return RedirectResponse(
            url="/demo/auth/login", status_code=status.HTTP_302_FOUND
        )


# Admin Demo Routes
@demo_router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Admin panel shell; client JS fetches RBAC/metrics from API."""
    user = await get_demo_user_context(request)
    if not user:
        return RedirectResponse(
            url="/demo/auth/login", status_code=status.HTTP_302_FOUND
        )

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

    try:
        from app import container

        rbac_service = container.rbac_service()
        data_service = container.data_service()

        roles_cache = getattr(rbac_service, "roles_cache", {})
        permissions_cache = getattr(rbac_service, "permissions_cache", {})
        groups_cache = getattr(rbac_service, "groups_cache", {})

        roles_list = []
        for role_id, role_data in roles_cache.items():
            roles_list.append(
                {
                    "id": role_id,
                    "name": role_data.get("name", role_id),
                    "description": role_data.get("metadata", {}).get("description", ""),
                    "permissions": len(role_data.get("permissions", [])),
                    "users": 0,
                }
            )

        permissions_list = []
        for perm_id, perm_data in permissions_cache.items():
            permissions_list.append(
                {
                    "id": perm_id,
                    "name": perm_id,
                    "description": perm_data.get("description", "")
                    if isinstance(perm_data, dict)
                    else "",
                    "category": perm_id.split(":")[0] if ":" in perm_id else "general",
                    "roles": 0,
                }
            )

        groups_list = []
        for group_id, group_data in groups_cache.items():
            groups_list.append(
                {
                    "id": group_id,
                    "name": group_data.get("name", group_id)
                    if isinstance(group_data, dict)
                    else group_id,
                    "description": group_data.get("description", "")
                    if isinstance(group_data, dict)
                    else "",
                    "roles": len(group_data.get("roles", []))
                    if isinstance(group_data, dict)
                    else 0,
                    "users": 0,
                }
            )

        users_data = await data_service.users.list_users()
        total_users = len(users_data) if users_data else 0
        active_users = sum(
            1 for u in users_data if u.get("status", "inactive") == "active"
        )
        if users_data is None:
            active_users = 0

        admin_data = {
            "total_users": total_users,
            "active_users": active_users,
            "total_roles": len(roles_list),
            "total_permissions": len(permissions_list),
            "roles": roles_list,
            "permissions": permissions_list,
            "groups": groups_list,
            "metrics": {},
        }
    except Exception as e:
        admin_data["error"] = f"Failed to load RBAC data: {str(e)}"

    return request.app.state.templates.TemplateResponse(
        "demo/admin/panel.html",
        {
            "request": request,
            "user": user,
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
    user = await get_demo_user_context(request)
    users = []
    return request.app.state.templates.TemplateResponse(
        "demo/admin/users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "title": "Manage Users - FastAPI Demo",
        },
    )


@demo_router.get("/admin/roles", response_class=HTMLResponse)
async def manage_roles(request: Request):
    """Manage roles page."""
    user = await get_demo_user_context(request)
    roles = []
    return request.app.state.templates.TemplateResponse(
        "demo/admin/roles.html",
        {
            "request": request,
            "user": user,
            "roles": roles,
            "title": "Manage Roles - FastAPI Demo",
        },
    )


@demo_router.get("/admin/permissions", response_class=HTMLResponse)
async def manage_permissions(request: Request):
    """Manage permissions page."""
    user = await get_demo_user_context(request)
    permissions = []
    return request.app.state.templates.TemplateResponse(
        "demo/admin/permissions.html",
        {
            "request": request,
            "user": user,
            "permissions": permissions,
            "title": "Manage Permissions - FastAPI Demo",
        },
    )


@demo_router.get("/admin/settings", response_class=HTMLResponse)
async def system_settings(request: Request):
    """System settings page."""
    user = await get_demo_user_context(request)
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
    return request.app.state.templates.TemplateResponse(
        "demo/admin/settings.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "title": "System Settings - FastAPI Demo",
        },
    )


@demo_router.get("/admin/metrics", response_class=HTMLResponse)
async def system_metrics(request: Request):
    """System metrics page."""
    user = await get_demo_user_context(request)
    metrics = {
        "requests_total": 0,
        "active_users": 0,
        "response_time_avg": 0,
        "error_rate": 0,
        "memory_usage": 0,
        "cpu_usage": 0,
    }
    return request.app.state.templates.TemplateResponse(
        "demo/admin/metrics.html",
        {
            "request": request,
            "user": user,
            "metrics": metrics,
            "title": "System Metrics - FastAPI Demo",
        },
    )


# API Demo Routes
@demo_router.get("/api", response_class=HTMLResponse)
async def api_demo(request: Request):
    """API demo page with real data."""
    user = await get_demo_user_context(request)
    # Render shell; client lists/calls endpoints directly
    api_endpoints = []
    return request.app.state.templates.TemplateResponse(
        "demo/api/demo.html",
        {
            "request": request,
            "user": user,
            "api_endpoints": api_endpoints,
            "title": "API Demo - FastAPI Demo",
        },
    )


@demo_router.get("/api/test", response_class=HTMLResponse)
async def api_test(request: Request):
    """API test page."""
    user = await get_demo_user_context(request)
    return request.app.state.templates.TemplateResponse(
        "demo/api/test.html",
        {"request": request, "user": user, "title": "API Test - FastAPI Demo"},
    )


@demo_router.get("/api/info", response_class=HTMLResponse)
async def api_info(request: Request):
    """API info page."""
    user = await get_demo_user_context(request)
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
    return request.app.state.templates.TemplateResponse(
        "demo/api/info.html",
        {
            "request": request,
            "user": user,
            "api_info": api_info,
            "title": "API Info - FastAPI Demo",
        },
    )


@demo_router.get("/api/health", response_class=HTMLResponse)
async def health_check(
    request: Request,
):
    """Health check page with real data."""
    user = await get_demo_user_context(request)
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

    return request.app.state.templates.TemplateResponse(
        "demo/api/health.html",
        {
            "request": request,
            "user": user,
            "health_data": health_data,
            "title": "Health Check - FastAPI Demo",
        },
    )


@demo_router.get("/api/status", response_class=HTMLResponse)
async def system_status(request: Request):
    """System status page."""
    user = await get_demo_user_context(request)
    status_data = {
        "system": "unknown",
        "load": "unknown",
        "memory": "unknown",
        "disk": "unknown",
        "network": "unknown",
        "last_restart": "unknown",
        "version": "1.0.0",
    }
    return request.app.state.templates.TemplateResponse(
        "demo/api/status.html",
        {
            "request": request,
            "user": user,
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
