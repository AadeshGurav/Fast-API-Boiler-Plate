# Authentication & RBAC System Documentation

## Overview

This document provides comprehensive guidance for using the robust authentication and RBAC (Role-Based Access Control) system implemented in this FastAPI application.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication Flow](#authentication-flow)
3. [RBAC Configuration Guide](#rbac-configuration-guide)
4. [Role Inheritance Examples](#role-inheritance-examples)
5. [Temporary Permissions Usage](#temporary-permissions-usage)
6. [OAuth2 Setup](#oauth2-setup)
7. [Session Management Guide](#session-management-guide)
8. [API Endpoints Reference](#api-endpoints-reference)
9. [Logging and Monitoring Guide](#logging-and-monitoring-guide)
10. [Security Best Practices](#security-best-practices)

## Architecture Overview

The authentication system follows a **"Simply Clever"** architecture with these key principles:

- **Platform Agnostic**: Uses interface-service patterns for complete database abstraction
- **JSON-Driven Configuration**: All RBAC roles, permissions, and groups load from JSON configs
- **Hybrid Token System**: Stateless JWT access tokens + stateful refresh tokens
- **Comprehensive Logging**: Every action logged with structured context
- **Hot-Reload Capability**: RBAC configs can be updated without restart

### Key Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Middleware    │    │   Services      │
│                 │    │                 │    │                 │
│ • Auth Routes   │◄──►│ • RBAC          │◄──►│ • AuthService   │
│ • OAuth Routes  │    │ • Session       │    │ • RBACService   │
│ • RBAC Routes   │    │ • Security      │    │ • OAuthService  │
│ • Session Routes│    │                 │    │ • PasswordSvc   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Repositories  │    │   Database      │    │   Configuration │
│                 │    │                 │    │                 │
│ • UserRepo      │◄──►│ • MongoDB       │    │ • JSON Configs  │
│ • SessionRepo   │    │ • Redis Cache   │    │ • DynamicConfig │
│ • RBACRepo      │    │ • Hybrid Store  │    │ • Hot Reload    │
│ • OAuthRepo     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Authentication Flow

### 1. User Registration

```python
# POST /api/v1/auth/register
{
    "username": "john_doe",
    "email": "john@example.com", 
    "password": "SecurePassword123!",
    "roles": ["user"],
    "groups": ["staff"]
}
```

**Response:**
```json
{
    "id": "user_123",
    "username": "john_doe",
    "email": "john@example.com",
    "roles": ["user"],
    "groups": ["staff"],
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z"
}
```

### 2. User Login

```python
# POST /api/v1/auth/login
{
    "username": "john_doe",
    "password": "SecurePassword123!",
    "device_info": {
        "user_agent": "Mozilla/5.0...",
        "ip_address": "192.168.1.100",
        "fingerprint": "192.168.1.100:Mozilla/5.0"
    }
}
```

**Response:**
```json
{
    "user": {
        "id": "user_123",
        "username": "john_doe",
        "email": "john@example.com",
        "roles": ["user"],
        "groups": ["staff"]
    },
    "tokens": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "Bearer",
        "expires_in": 900
    },
    "permissions": ["profile:read", "profile:write", "dashboard:read"]
}
```

### 3. Token Refresh

```python
# POST /api/v1/auth/refresh
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "device_info": {
        "user_agent": "Mozilla/5.0...",
        "ip_address": "192.168.1.100",
        "fingerprint": "192.168.1.100:Mozilla/5.0"
    }
}
```

### 4. Logout

```python
# POST /api/v1/auth/logout
# Headers: Authorization: Bearer <access_token>
```

## RBAC Configuration Guide

### JSON Configuration Files

All RBAC configuration is stored in JSON files in the `config.d/` directory:

#### 1. Roles Configuration (`config.d/rbac-roles-global.json`)

```json
{
    "rbac_roles": {
        "admin": {
            "id": "admin",
            "name": "Administrator", 
            "permissions": ["*"],
            "inherits": [],
            "metadata": {"level": 100}
        },
        "manager": {
            "id": "manager",
            "name": "Manager",
            "permissions": ["users:read", "users:write", "reports:read"],
            "inherits": ["user"],
            "metadata": {"level": 50}
        },
        "user": {
            "id": "user", 
            "name": "User",
            "permissions": ["profile:read", "profile:write", "dashboard:read"],
            "inherits": [],
            "metadata": {"level": 10}
        }
    }
}
```

#### 2. Permissions Configuration (`config.d/rbac-permissions-global.json`)

```json
{
    "rbac_permissions": {
        "users:read": {
            "id": "users:read",
            "name": "Read Users",
            "description": "View user information",
            "resource": "users",
            "action": "read"
        },
        "users:write": {
            "id": "users:write", 
            "name": "Write Users",
            "description": "Create/update users",
            "resource": "users",
            "action": "write"
        },
        "reports:read": {
            "id": "reports:read",
            "name": "Read Reports", 
            "description": "View reports",
            "resource": "reports",
            "action": "read"
        }
    }
}
```

#### 3. Groups Configuration (`config.d/rbac-groups-global.json`)

```json
{
    "rbac_groups": {
        "admins": {
            "id": "admins",
            "name": "Administrators",
            "roles": ["admin"],
            "metadata": {}
        },
        "staff": {
            "id": "staff", 
            "name": "Staff Members",
            "roles": ["manager", "user"],
            "metadata": {}
        }
    }
}
```

### Hot-Reload Configuration

RBAC configurations are automatically reloaded every 5 minutes. To manually refresh:

```python
# Via RBAC service
rbac_service = Container.rbac_service()
await rbac_service.refresh_rbac_config()
```

## Role Inheritance Examples

### Simple Inheritance

```json
{
    "manager": {
        "permissions": ["users:read", "reports:write"],
        "inherits": ["user"]
    },
    "user": {
        "permissions": ["profile:read", "dashboard:read"],
        "inherits": []
    }
}
```

**Result for manager role:**
- Direct permissions: `["users:read", "reports:write"]`
- Inherited permissions: `["profile:read", "dashboard:read"]`
- **Total permissions:** `["users:read", "reports:write", "profile:read", "dashboard:read"]`

### Complex Inheritance Chain

```json
{
    "super_admin": {
        "permissions": ["system:admin"],
        "inherits": ["admin"]
    },
    "admin": {
        "permissions": ["users:write", "settings:write"],
        "inherits": ["manager"]
    },
    "manager": {
        "permissions": ["users:read", "reports:write"],
        "inherits": ["user"]
    },
    "user": {
        "permissions": ["profile:read"],
        "inherits": []
    }
}
```

**Result for super_admin role:**
- Direct: `["system:admin"]`
- From admin: `["users:write", "settings:write"]`
- From manager: `["users:read", "reports:write"]`
- From user: `["profile:read"]`
- **Total:** `["system:admin", "users:write", "settings:write", "users:read", "reports:write", "profile:read"]`

### Cycle Detection

The system automatically detects and prevents inheritance cycles:

```json
{
    "role_a": {
        "permissions": ["perm1"],
        "inherits": ["role_b"]
    },
    "role_b": {
        "permissions": ["perm2"], 
        "inherits": ["role_a"]  // ❌ Cycle detected!
    }
}
```

## Temporary Permissions Usage

Temporary permissions allow granting time-bound access to users or groups.

### Creating Temporary Permissions

```python
# POST /api/v1/rbac/temporary-permissions
{
    "entity_type": "user",
    "entity_id": "user_123",
    "permission_id": "reports:write",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-02T00:00:00Z"
}
```

### Permission Resolution

When checking permissions, the system combines:
1. **Static permissions** from roles and groups
2. **Active temporary permissions** within the time window

```python
# User has role "user" with permissions: ["profile:read"]
# User has temporary permission "reports:write" (active for 24 hours)
# 
# Result: ["profile:read", "reports:write"]
```

### Managing Temporary Permissions

```python
# Revoke temporary permission
# DELETE /api/v1/rbac/temporary-permissions/{temp_perm_id}

# List active temporary permissions
# GET /api/v1/rbac/users/{user_id}/permissions
```

## OAuth2 Setup

### Google OAuth Setup

1. **Create Google OAuth App:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URI: `http://localhost:8000/api/v1/oauth/google/callback`

2. **Configure OAuth Provider:**

```json
// config.d/oauth-config-global.json
{
    "oauth_providers": {
        "google": {
            "provider": "google",
            "client_id": "your-google-client-id",
            "client_secret": "your-google-client-secret", 
            "redirect_uri": "http://localhost:8000/api/v1/oauth/google/callback",
            "scopes": ["openid", "email", "profile"],
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo"
        }
    },
    "oauth_enabled": true
}
```

### Apple OAuth Setup

1. **Create Apple Developer Account**
2. **Create App ID and Service ID**
3. **Configure OAuth Provider:**

```json
{
    "oauth_providers": {
        "apple": {
            "provider": "apple",
            "client_id": "your-apple-service-id",
            "client_secret": "your-apple-client-secret",
            "redirect_uri": "http://localhost:8000/api/v1/oauth/apple/callback",
            "scopes": ["name", "email"],
            "authorization_url": "https://appleid.apple.com/auth/authorize",
            "token_url": "https://appleid.apple.com/auth/token",
            "userinfo_url": "https://appleid.apple.com/auth/userinfo"
        }
    }
}
```

### OAuth Flow

1. **Initiate Authorization:**
   ```
   GET /api/v1/oauth/google/authorize
   ```

2. **User Authorization:**
   - User redirected to Google
   - User authorizes application
   - Google redirects back with code

3. **Handle Callback:**
   ```
   GET /api/v1/oauth/google/callback?code=...&state=...
   ```

4. **Account Linking:**
   - System exchanges code for tokens
   - Retrieves user info from provider
   - Creates or links user account
   - Returns login response with tokens

## Session Management Guide

### Session Storage

Sessions use hybrid storage:
- **MongoDB**: Primary storage for persistence
- **Redis**: Caching layer for performance

### Session Lifecycle

1. **Session Creation:**
   - Created on first request or login
   - Stored with device information
   - TTL: 7 days (configurable)

2. **Session Extension:**
   - Extended on activity (configurable)
   - Device fingerprint verification
   - Last used timestamp updated

3. **Session Revocation:**
   - Individual session revocation
   - Bulk revocation (all devices)
   - Automatic cleanup of expired sessions

### Session Management API

```python
# List active sessions
GET /api/v1/sessions/active

# Revoke specific session  
DELETE /api/v1/sessions/{session_id}

# Revoke all sessions
DELETE /api/v1/sessions/all

# Get session details
GET /api/v1/sessions/{session_id}
```

### Device Tracking

Sessions track device information:
- **User Agent**: Browser/client information
- **IP Address**: Client IP address
- **Fingerprint**: Device fingerprint for security
- **Platform**: Device platform (extracted from user agent)
- **Browser**: Browser information (extracted from user agent)

## API Endpoints Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | User login | No |
| POST | `/api/v1/auth/refresh` | Refresh tokens | No |
| POST | `/api/v1/auth/logout` | Logout user | Yes |
| POST | `/api/v1/auth/logout-all` | Logout all devices | Yes |
| POST | `/api/v1/auth/reset-password-request` | Request password reset | No |
| POST | `/api/v1/auth/reset-password-confirm` | Confirm password reset | No |
| GET | `/api/v1/auth/me` | Get current user info | Yes |

### OAuth Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/oauth/{provider}/authorize` | Initiate OAuth flow | No |
| GET | `/api/v1/oauth/{provider}/callback` | Handle OAuth callback | No |
| POST | `/api/v1/oauth/{provider}/link` | Link OAuth account | Yes |
| DELETE | `/api/v1/oauth/{provider}/unlink` | Unlink OAuth account | Yes |

### RBAC Management Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/rbac/roles` | List roles | Yes (rbac:read) |
| GET | `/api/v1/rbac/permissions` | List permissions | Yes (rbac:read) |
| GET | `/api/v1/rbac/groups` | List groups | Yes (rbac:read) |
| POST | `/api/v1/rbac/users/{user_id}/roles` | Assign role | Yes (rbac:write) |
| DELETE | `/api/v1/rbac/users/{user_id}/roles/{role_id}` | Remove role | Yes (rbac:write) |
| POST | `/api/v1/rbac/users/{user_id}/groups` | Assign group | Yes (rbac:write) |
| POST | `/api/v1/rbac/temporary-permissions` | Create temp permission | Yes (rbac:write) |
| DELETE | `/api/v1/rbac/temporary-permissions/{id}` | Revoke temp permission | Yes (rbac:write) |
| GET | `/api/v1/rbac/users/{user_id}/permissions` | Get user permissions | Yes (rbac:read) |

### Session Management Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/sessions/active` | List active sessions | Yes |
| DELETE | `/api/v1/sessions/{session_id}` | Revoke session | Yes |
| DELETE | `/api/v1/sessions/all` | Revoke all sessions | Yes |
| GET | `/api/v1/sessions/{session_id}` | Get session details | Yes |

## Logging and Monitoring Guide

### Structured Logging

All authentication and RBAC operations are logged with structured context:

```json
{
    "timestamp": "2024-01-01T00:00:00Z",
    "level": "INFO",
    "message": "User logged in successfully: john_doe",
    "service": "auth",
    "action": "login_user",
    "user_id": "user_123",
    "username": "john_doe",
    "session_id": "session_456",
    "device_info": {
        "user_agent": "Mozilla/5.0...",
        "ip_address": "192.168.1.100",
        "fingerprint": "192.168.1.100:Mozilla/5.0"
    }
}
```

### Key Log Events

#### Authentication Events
- `register_user`: User registration
- `login_user`: User login
- `refresh_tokens`: Token refresh
- `logout_user`: User logout
- `logout_all_devices`: Bulk logout

#### RBAC Events
- `permission_check`: Permission verification
- `role_assignment`: Role assignment
- `group_assignment`: Group assignment
- `temp_permission_create`: Temporary permission creation
- `temp_permission_revoke`: Temporary permission revocation

#### Session Events
- `session_create`: Session creation
- `session_load`: Session loading
- `session_revoke`: Session revocation
- `device_info_update`: Device info update

### Monitoring Metrics

Key metrics to monitor:

1. **Authentication Metrics:**
   - Login success/failure rates
   - Token refresh frequency
   - Session creation/revocation rates

2. **RBAC Metrics:**
   - Permission check latency
   - Role assignment frequency
   - Temporary permission usage

3. **Security Metrics:**
   - Failed authentication attempts
   - Permission denied events
   - Device fingerprint mismatches

### Log Analysis Queries

#### Failed Authentication Attempts
```sql
SELECT COUNT(*) as failed_attempts, username, ip_address
FROM logs 
WHERE service = 'auth' AND action = 'login_user' AND level = 'WARNING'
GROUP BY username, ip_address
ORDER BY failed_attempts DESC;
```

#### Permission Denied Events
```sql
SELECT COUNT(*) as denied_count, permission, user_id
FROM logs
WHERE service = 'permissions' AND action = 'permission_check' AND result = 'denied'
GROUP BY permission, user_id
ORDER BY denied_count DESC;
```

#### Session Activity
```sql
SELECT COUNT(*) as session_count, DATE(created_at) as date
FROM logs
WHERE service = 'session' AND action = 'session_create'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## Security Best Practices

### 1. Password Security
- Use Argon2 for password hashing
- Enforce strong password policies
- Implement password reset with secure tokens

### 2. Token Security
- Short-lived access tokens (15 minutes)
- Long-lived refresh tokens (7 days)
- Refresh token rotation on use
- Secure token storage (hashed)

### 3. Session Security
- Device fingerprinting
- Session revocation capabilities
- Automatic session cleanup
- Secure session cookies

### 4. RBAC Security
- Principle of least privilege
- Regular permission audits
- Temporary permission time limits
- Role inheritance cycle detection

### 5. OAuth Security
- State parameter for CSRF protection
- Secure redirect URI validation
- Token validation and verification
- Account linking verification

### 6. Logging Security
- No sensitive data in logs
- Structured logging for analysis
- Log retention policies
- Security event monitoring

### 7. Infrastructure Security
- HTTPS enforcement (HSTS)
- Rate limiting on auth endpoints
- Input validation and sanitization
- Error handling without information leakage

## Troubleshooting

### Common Issues

#### 1. Permission Denied Errors
**Problem:** User getting 403 Forbidden errors
**Solution:** 
- Check user roles and permissions
- Verify RBAC configuration
- Check for temporary permission expiry

#### 2. Token Expired Errors
**Problem:** Access tokens expiring frequently
**Solution:**
- Implement token refresh logic
- Check token expiration settings
- Verify refresh token validity

#### 3. Session Not Found Errors
**Problem:** Sessions not persisting
**Solution:**
- Check MongoDB connection
- Verify Redis cache status
- Check session TTL settings

#### 4. OAuth Callback Errors
**Problem:** OAuth flow failing
**Solution:**
- Verify redirect URI configuration
- Check OAuth provider settings
- Validate state parameter

### Debug Mode

Enable debug logging for detailed troubleshooting:

```json
{
    "log_level": "DEBUG",
    "auth_debug": true,
    "rbac_debug": true,
    "session_debug": true
}
```

### Health Checks

Monitor system health with these endpoints:

```python
# Check authentication service
GET /api/v1/health/auth

# Check RBAC service  
GET /api/v1/health/rbac

# Check session service
GET /api/v1/health/sessions

# Check OAuth providers
GET /api/v1/health/oauth
```

---

## Conclusion

This authentication and RBAC system provides a robust, secure, and scalable foundation for user management and access control. The JSON-driven configuration allows for easy customization and hot-reloading, while the comprehensive logging ensures full auditability and monitoring capabilities.

For additional support or questions, refer to the code examples in `examples/auth_rbac_examples.py` or consult the API documentation at `/docs` when running the application.