# Robust Authentication & RBAC System Implementation

## Architecture Principles

**Simply Clever**: Leverage existing patterns (Config, Logger, Interface-Service) to build a secure, extensible, platform-agnostic auth system.

**Key Design Decisions:**

- Use existing `config.py` for all JSON configuration loading (RBAC roles, permissions, OAuth)
- Extend existing `logger.py` for comprehensive event logging
- Follow interface-service pattern for complete database abstraction
- All repositories implement interfaces for easy platform switching
- No business logic in middleware; delegate to services

---

## Phase 1: Foundation - Models & Configuration

### 1.0 DynamicConfig Base Class

Create `app/core/dynamic_config.py`:

- Inherits from Pydantic `BaseModel` for validation trust
- Adds class methods to load from existing `Config` instance (leverages config.py)
- Provides `reload()` method for runtime updates
- All RBAC models (Role, Permission, Group) will extend this for JSON-driven flexibility
```python
from pydantic import BaseModel
from typing import TypeVar, Type
from config import Config

T = TypeVar('T', bound='DynamicConfig')

class DynamicConfig(BaseModel):
    """Base class combining Pydantic validation with JSON config flexibility."""
    
    @classmethod
    def load_from_config(cls: Type[T], config: Config, config_key: str) -> T:
        """Load from existing Config instance (uses config.py)."""
        data = config.get(config_key, {})
        return cls(**data)
    
    def reload_from_config(self, config: Config, config_key: str) -> None:
        """Hot-reload: update instance from Config without recreating."""
        data = config.get(config_key, {})
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
```


### 1.1 Pydantic Models (Schema Validation + JSON Flexibility)

Create `app/models/` directory with Pydantic models:

**`app/models/user.py`:**

- `UserRole` enum: ADMIN, MANAGER, USER, GUEST
- `User` (BaseModel): id, username, email, password_hash, roles[], groups[], status, metadata, created_at, updated_at
- `UserCreate` (BaseModel): username, email, password, roles, groups
- `UserUpdate` (BaseModel): email, roles, groups, status
- `UserInDB` (BaseModel): extends User with password_hash
- `UserPublic` (BaseModel): safe user data (no password_hash)

**`app/models/role.py`:**

- **All RBAC models extend `DynamicConfig` for JSON-driven runtime updates**
- `Permission` (DynamicConfig): id, name, description, resource, action
- `Role` (DynamicConfig): id, name, permissions[], inherits[], metadata
- `Group` (DynamicConfig): id, name, roles[], metadata
- `TemporaryPermission` (BaseModel): id, entity_type, entity_id, permission_id, start_time, end_time, created_by
- **All models inherit from `DynamicConfig` to enable JSON-driven runtime flexibility**:
  ```python
  class DynamicConfig(BaseModel):
      @classmethod
      def load_from_json(cls, path: str):
          data = json.load(open(path))
          return cls(**data)
  
      def refresh(self, path: str):
          data = json.load(open(path))
          for k, v in data.items():
              setattr(self, k, v)
  ```


**`app/models/session.py`:**

- `DeviceInfo`: user_agent, ip_address, fingerprint, platform, browser
- `RefreshToken`: token_hash, user_id, device_info, issued_at, expires_at, last_used_at, revoked_at
- `Session`: id, user_id, refresh_token_id, device_info, created_at, expires_at, revoked_at

**`app/models/auth.py`:**

- `TokenPair`: access_token, refresh_token, token_type, expires_in
- `TokenPayload`: user_id, username, roles[], permissions[], exp, iat, type (access/refresh)
- `LoginRequest`: username, password, device_info
- `LoginResponse`: user, tokens, permissions
- `RefreshRequest`: refresh_token, device_info
- `PasswordResetRequest`: email
- `PasswordResetConfirm`: token, new_password

**`app/models/oauth.py`:**

- `OAuthProvider` enum: GOOGLE, APPLE
- `OAuthConfig`: provider, client_id, client_secret, redirect_uri, scopes[], authorization_url, token_url, userinfo_url
- `OAuthToken`: access_token, refresh_token, expires_in, token_type, scope
- `OAuthUserInfo`: provider_user_id, email, name, picture
- `OAuthAccount`: user_id, provider, provider_user_id, access_token, refresh_token, created_at, updated_at

### 1.2 JSON Configuration Files

Create in `config.d/` using existing Config pattern:

**`config.d/rbac-roles-global.json`:**

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

**`config.d/rbac-permissions-global.json`:**

```json
{
  "rbac_permissions": {
    "users:read": {"id": "users:read", "name": "Read Users", "description": "View user information", "resource": "users", "action": "read"},
    "users:write": {"id": "users:write", "name": "Write Users", "description": "Create/update users", "resource": "users", "action": "write"}
  }
}
```

**`config.d/rbac-groups-global.json`:**

```json
{
  "rbac_groups": {
    "admins": {"id": "admins", "name": "Administrators", "roles": ["admin"], "metadata": {}},
    "staff": {"id": "staff", "name": "Staff Members", "roles": ["manager", "user"], "metadata": {}}
  }
}
```

**`config.d/oauth-config-global.json`:**

```json
{
  "oauth_providers": {
    "google": {
      "provider": "google",
      "client_id": "",
      "client_secret": "",
      "redirect_uri": "http://localhost:8000/oauth/google/callback",
      "scopes": ["openid", "email", "profile"],
      "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
      "token_url": "https://oauth2.googleapis.com/token",
      "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo"
    }
  },
  "oauth_enabled": false
}
```

---

## Phase 2: Database Layer (Platform-Agnostic)

### 2.1 Repository Interfaces

Create `app/core/interfaces/` following existing pattern:

**`app/core/interfaces/user_repository_interface.py`:**

```python
class UserRepositoryInterface(BaseInterface):
    @abstractmethod
    async def create_user(user_data: dict) -> dict
    @abstractmethod
    async def get_user_by_id(user_id: str) -> Optional[dict]
    @abstractmethod
    async def get_user_by_username(username: str) -> Optional[dict]
    @abstractmethod
    async def get_user_by_email(email: str) -> Optional[dict]
    @abstractmethod
    async def update_user(user_id: str, updates: dict) -> bool
    @abstractmethod
    async def delete_user(user_id: str) -> bool
    @abstractmethod
    async def assign_roles(user_id: str, roles: list[str]) -> bool
    @abstractmethod
    async def assign_groups(user_id: str, groups: list[str]) -> bool
```

**`app/core/interfaces/session_repository_interface.py`:**

```python
class SessionRepositoryInterface(BaseInterface):
    @abstractmethod
    async def create_session(session_data: dict) -> str
    @abstractmethod
    async def get_session(session_id: str) -> Optional[dict]
    @abstractmethod
    async def get_user_sessions(user_id: str) -> list[dict]
    @abstractmethod
    async def update_session(session_id: str, updates: dict) -> bool
    @abstractmethod
    async def revoke_session(session_id: str) -> bool
    @abstractmethod
    async def revoke_user_sessions(user_id: str, except_session_id: str = None) -> int
    @abstractmethod
    async def cleanup_expired_sessions() -> int
```

**`app/core/interfaces/rbac_repository_interface.py`:**

```python
class RBACRepositoryInterface(BaseInterface):
    @abstractmethod
    async def sync_roles_to_db(roles: dict) -> bool
    @abstractmethod
    async def sync_permissions_to_db(permissions: dict) -> bool
    @abstractmethod
    async def sync_groups_to_db(groups: dict) -> bool
    @abstractmethod
    async def get_role(role_id: str) -> Optional[dict]
    @abstractmethod
    async def get_permission(permission_id: str) -> Optional[dict]
    @abstractmethod
    async def get_group(group_id: str) -> Optional[dict]
    @abstractmethod
    async def create_temporary_permission(temp_perm: dict) -> str
    @abstractmethod
    async def get_active_temporary_permissions(entity_type: str, entity_id: str) -> list[dict]
    @abstractmethod
    async def revoke_temporary_permission(temp_perm_id: str) -> bool
```

**`app/core/interfaces/oauth_repository_interface.py`:**

```python
class OAuthRepositoryInterface(BaseInterface):
    @abstractmethod
    async def link_oauth_account(oauth_account: dict) -> bool
    @abstractmethod
    async def get_oauth_account(provider: str, provider_user_id: str) -> Optional[dict]
    @abstractmethod
    async def get_user_oauth_accounts(user_id: str) -> list[dict]
    @abstractmethod
    async def unlink_oauth_account(user_id: str, provider: str) -> bool
    @abstractmethod
    async def update_oauth_tokens(user_id: str, provider: str, tokens: dict) -> bool
```

### 2.2 MongoDB Repository Implementations

Create `app/database/repositories/` with concrete implementations:

**`app/database/repositories/user_repository.py`:**

- Implements `UserRepositoryInterface`
- Uses `DatabaseService` (already wraps MongoDB)
- Extensive logging via `logger.info/debug/error`
- All CRUD operations log: action, user_id, timestamp, result

**`app/database/repositories/session_repository.py`:**

- Implements `SessionRepositoryInterface`
- Hybrid storage: MongoDB (primary) + Redis (caching via `cache_service`)
- Hash refresh tokens before storage (using hashlib.sha256)
- Log all session operations: create, get, revoke, cleanup

**`app/database/repositories/rbac_repository.py`:**

- Implements `RBACRepositoryInterface`
- Syncs JSON config data to MongoDB collections
- Logs every sync operation with counts
- Caches role/permission lookups in Redis

**`app/database/repositories/oauth_repository.py`:**

- Implements `OAuthRepositoryInterface`
- Stores OAuth account links and tokens
- Logs all OAuth account operations

### 2.3 Update MongoDB Initialization

Extend `app/database/mongodb.py` `initialize_db()`:

- Add collections: `sessions`, `roles`, `permissions`, `groups`, `temporary_permissions`, `oauth_accounts`
- Create indexes:
  - `sessions`: user_id, expires_at, revoked_at
  - `roles`: name (unique)
  - `permissions`: name (unique)
  - `temporary_permissions`: entity_id, end_time
  - `oauth_accounts`: (user_id, provider) unique compound

---

## Phase 3: Service Layer (Business Logic)

### 3.1 Password Service

Create `app/services/password_service.py`:

- Implements `app/core/interfaces/password_service_interface.py`
- Uses Argon2 (already in requirements) for hashing
- Methods:
  - `hash_password(password: str) -> str`
  - `verify_password(password: str, hash: str) -> bool`
  - `validate_password_strength(password: str) -> bool`
  - `generate_reset_token(user_id: str) -> str`
  - `verify_reset_token(token: str) -> Optional[str]` (returns user_id)
- Logs: all hashing attempts, verification attempts, token generation
- Uses `Config` for password policy (min length, complexity)

### 3.2 Enhanced AuthService

Extend `app/services/auth.py`:

- Add `session_repository`, `password_service` dependencies
- New methods:
  - `register_user(user_data: UserCreate) -> User`
  - `login(username: str, password: str, device_info: DeviceInfo) -> LoginResponse`
  - `refresh_tokens(refresh_token: str, device_info: DeviceInfo) -> TokenPair`
  - `logout(session_id: str) -> bool`
  - `logout_all_devices(user_id: str, except_session_id: str) -> int`
  - `verify_device_fingerprint(session_id: str, device_info: DeviceInfo) -> bool`
- Refresh token rotation: generate new refresh token, invalidate old one
- Store session in hybrid storage (MongoDB + Redis)
- Log every auth event: login, logout, token refresh, registration

### 3.3 RBAC Service

Create `app/services/rbac_service.py` implementing `app/core/interfaces/rbac_service_interface.py`:

- Dependencies: `config`, `logger`, `rbac_repository`, `cache_service`
- Initialization:
  - Load roles/permissions/groups from `Config` (leverages existing config.py)
  - Validate JSON structure with Pydantic models
  - Sync to database via repository
  - Log: "RBAC loaded from config: X roles, Y permissions, Z groups"
- Core methods:
  - `load_rbac_config() -> None`: Load from Config, sync to DB
  - `refresh_rbac_config() -> None`: Reload from Config, update DB
  - `resolve_user_permissions(user_id: str) -> list[str]`: Compute all permissions from roles + groups + inherited + temporary
  - `check_permission(user_id: str, permission: str) -> bool`: Verify permission
  - `resolve_role_inheritance(role_id: str) -> list[str]`: Recursive permission resolution
  - `get_active_temporary_permissions(entity_type: str, entity_id: str) -> list[dict]`: Filter by time window
  - `assign_role(user_id: str, role_id: str) -> bool`
  - `remove_role(user_id: str, role_id: str) -> bool`
  - `assign_group(user_id: str, group_id: str) -> bool`
  - `create_temporary_permission(temp_perm: TemporaryPermission) -> str`
  - `revoke_temporary_permission(temp_perm_id: str) -> bool`
- Caching strategy: Cache resolved permissions per user with TTL
- Logging: Every permission check, role assignment, inheritance resolution

### 3.4 OAuth Service

Create `app/services/oauth_service.py` implementing `app/core/interfaces/oauth_service_interface.py`:

- Dependencies: `config`, `logger`, `oauth_repository`, `user_repository`
- Load OAuth provider configs from `Config` (oauth_providers)
- Methods:
  - `get_authorization_url(provider: OAuthProvider, state: str) -> str`
  - `exchange_code_for_token(provider: OAuthProvider, code: str) -> OAuthToken`
  - `get_user_info(provider: OAuthProvider, access_token: str) -> OAuthUserInfo`
  - `create_or_link_user(oauth_user_info: OAuthUserInfo, provider: OAuthProvider) -> User`
  - `unlink_oauth_account(user_id: str, provider: OAuthProvider) -> bool`
- Implementations for Google and Apple providers
- Log every OAuth flow step: authorization, token exchange, user info fetch, account link

---

## Phase 4: Middleware Refactoring

### 4.1 Refactor RBACMiddleware

Update `app/api/middleware/rbac.py`:

- Remove hardcoded UserRole and users_db imports
- Inject `rbac_service` via Container
- Remove `app.models.user` and `app.database.users_db` imports (these don't exist yet)
- Delegate permission checking to `rbac_service.check_permission()`
- Log every request: path, method, user_id, role, permission check result
- On denied access, log: "Permission denied: user={user_id}, role={role}, path={path}, reason={reason}"

### 4.2 Refactor SessionMiddleware

Update `app/api/middleware/session.py`:

- Use `session_repository` for hybrid MongoDB+Redis storage
- Track device info from request headers
- Extend session TTL on activity
- Log: session creation, session load, session extension, session errors

### 4.3 Create Missing User Model

Create `app/models/user.py` with `UserRole` enum to fix import error in `rbac.py`

---

## Phase 5: API Routes

### 5.1 Authentication Routes

Create `app/api/routes/auth.py`:

- `POST /auth/register`: Register new user → log: "User registered: {username}"
- `POST /auth/login`: Login → log: "User logged in: {username}, device: {device_info}"
- `POST /auth/refresh`: Refresh tokens → log: "Tokens refreshed: {user_id}, session: {session_id}"
- `POST /auth/logout`: Logout → log: "User logged out: {user_id}, session: {session_id}"
- `POST /auth/logout-all`: Logout all devices → log: "All sessions revoked: {user_id}, count: {count}"
- `POST /auth/reset-password-request`: Request reset → log: "Password reset requested: {email}"
- `POST /auth/reset-password-confirm`: Confirm reset → log: "Password reset completed: {user_id}"
- `GET /auth/me`: Get current user with resolved permissions → log: "User info requested: {user_id}"

### 5.2 OAuth Routes

Create `app/api/routes/oauth.py`:

- `GET /oauth/{provider}/authorize`: Redirect to provider → log: "OAuth authorization initiated: {provider}, state: {state}"
- `GET /oauth/{provider}/callback`: Handle callback → log: "OAuth callback received: {provider}, user: {user_id}"
- `POST /oauth/{provider}/link`: Link account → log: "OAuth account linked: {user_id}, provider: {provider}"
- `DELETE /oauth/{provider}/unlink`: Unlink → log: "OAuth account unlinked: {user_id}, provider: {provider}"

### 5.3 RBAC Management Routes

Create `app/api/routes/rbac.py`:

- `GET /rbac/roles`: List roles
- `GET /rbac/permissions`: List permissions
- `GET /rbac/groups`: List groups
- `POST /rbac/users/{user_id}/roles`: Assign role → log: "Role assigned: user={user_id}, role={role_id}, by={admin_id}"
- `DELETE /rbac/users/{user_id}/roles/{role_id}`: Remove role → log: "Role removed: user={user_id}, role={role_id}"
- `POST /rbac/users/{user_id}/groups`: Assign group → log: "Group assigned: user={user_id}, group={group_id}"
- `POST /rbac/temporary-permissions`: Create temp permission → log: "Temp permission created: {entity_id}, {permission_id}, expires: {end_time}"
- `DELETE /rbac/temporary-permissions/{id}`: Revoke → log: "Temp permission revoked: {id}"
- `GET /rbac/users/{user_id}/permissions`: Get resolved permissions → log: "Permissions resolved: {user_id}, count: {count}"
- All endpoints require admin permission, logged

### 5.4 Session Management Routes

Create `app/api/routes/sessions.py`:

- `GET /sessions/active`: List active sessions → log: "Active sessions listed: {user_id}"
- `DELETE /sessions/{session_id}`: Revoke session → log: "Session revoked: {session_id}, user: {user_id}"
- `DELETE /sessions/all`: Revoke all → log: "All sessions revoked except current: {user_id}"

---

## Phase 6: Dependency Injection & Integration

### 6.1 Update Container

Update `app/core/container.py`:

- Register repositories as singletons:
  - `user_repository = providers.Singleton(UserRepository, ...)`
  - `session_repository = providers.Singleton(SessionRepository, ...)`
  - `rbac_repository = providers.Singleton(RBACRepository, ...)`
  - `oauth_repository = providers.Singleton(OAuthRepository, ...)`
- Register services:
  - `password_service = providers.Singleton(PasswordService, ...)`
  - `rbac_service = providers.Singleton(RBACService, ...)`
  - `oauth_service = providers.Singleton(OAuthService, ...)`
- Wire auth_service with new dependencies
- Log container initialization: "Container initialized with X services, Y repositories"

### 6.2 Update Startup Logic

Update `app/utils/utils.py` lifespan function:

- On startup:
  - Initialize RBAC: `rbac_service.load_rbac_config()`
  - Log: "RBAC initialized: {roles_count} roles, {permissions_count} permissions"
  - Schedule periodic RBAC refresh (every 5 minutes): `asyncio.create_task(periodic_rbac_refresh())`
  - Log: "RBAC refresh scheduled: every 5 minutes"
  - Initialize OAuth providers if enabled
  - Log: "OAuth providers initialized: {providers}"
- On shutdown:
  - Cleanup expired sessions
  - Log: "Expired sessions cleaned up: {count}"

### 6.3 Periodic RBAC Refresh Task

Create background task:

```python
async def periodic_rbac_refresh():
    while True:
        await asyncio.sleep(300)  # 5 minutes
        logger.info("Starting periodic RBAC refresh")
        await rbac_service.refresh_rbac_config()
        logger.info("RBAC refresh completed")
```

---

## Phase 7: Permission Utilities

Create `app/utils/permissions.py`:

- `@require_permission(permission: str)`: Decorator that checks permission via RBAC service, logs denied access
- `@require_role(role: str)`: Decorator for role check, logs denied access
- `@require_any_permission(permissions: list[str])`: Check if user has any of the permissions
- `get_current_active_user()`: FastAPI dependency that decodes JWT, resolves permissions, attaches to request
- Log every decorator usage: permission checked, result, user_id

---

## Phase 8: Configuration Updates

### 8.1 Extend Existing Configs

Update `config.d/auth-config-global.json`:

```json
{
  "jwt_secret": "...",
  "jwt_algo": "HS256",
  "jwt_access_token_expiry": 15,
  "jwt_refresh_token_expiry": 10080,
  "password_min_length": 8,
  "password_require_uppercase": true,
  "password_require_lowercase": true,
  "password_require_digit": true,
  "password_require_special": true,
  "max_login_attempts": 5,
  "login_lockout_duration": 900
}
```

Update `config.d/session-config-global.json`:

```json
{
  "session_ttl": 604800,
  "session_extend_on_activity": true,
  "session_cleanup_interval": 3600,
  "max_sessions_per_user": 5,
  "track_device_info": true
}
```

---

## Phase 9: Testing & Documentation

### 9.1 Example Flows

Create `examples/auth_rbac_examples.py`:

- User registration and login example
- Token refresh example
- Permission checking in route example
- OAuth2 flow example
- Temporary permission example
- Role inheritance example

### 9.2 Update Documentation

Update `USAGE_README.md`:

- Authentication flow diagrams
- RBAC configuration guide
- Role inheritance examples
- Temporary permissions usage
- OAuth2 setup (Google, Apple)
- Session management guide
- Logging and monitoring guide

---

## Phase 10: Code Quality

### 10.1 Format & Lint

- Run Black, Ruff, Flake8 on all modified files
- Fix all linting issues
- Ensure all files <300 lines

### 10.2 Logging Audit

- Verify every service method logs appropriately
- Ensure sensitive data (passwords, tokens) not logged
- Add structured logging context (user_id, session_id, request_id)

### 10.3 Security Review

- Verify all passwords hashed with Argon2
- Verify refresh tokens hashed before storage
- Verify JWT secrets loaded from config
- Verify rate limiting on auth endpoints
- Verify HTTPS enforcement in production
