"""Every setting of the application, declared once, with type, default and description.

Values are resolved in this order (later wins):

1. the defaults below
2. ``config.toml``            committed defaults for the project (also holds RBAC roles)
3. ``config.local.toml``      your overrides; git-ignored
4. ``config.secrets.toml``    generated secrets (JWT key); git-ignored
5. ``.env``                   ``FABP_<NAME>=value`` lines; git-ignored
6. environment variables      ``FABP_<NAME>=value``

Unknown names and invalid values stop the application at startup with a message naming the
setting and the file it came from. ``python -m app.settings`` prints this reference.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogLevelLower = Literal["critical", "error", "warning", "info", "debug", "trace"]
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseModel):
    """The complete, validated configuration."""

    model_config = ConfigDict(extra="forbid", validate_default=True)

    # ------------------------------------------------------------------ application
    app_title: str = Field(
        "fastapi_boilerplate", description="Service name (logs, traces, cookie prefix)."
    )
    app_version: str = Field("1.0.0", description="Version reported by the API and monitoring.")
    app_description: str = Field("FastAPI Boilerplate API", description="OpenAPI description.")
    environment: str = Field(
        "production", description="Free-form label: development, staging, production."
    )
    app_debug: bool = Field(
        False,
        description="Development mode: enables /docs, relaxes Secure cookies and CSP. Never in production.",
    )
    app_host: str = Field(
        "127.0.0.1",
        description="Interface to bind. Use 0.0.0.0 only behind a proxy/in a container.",
    )
    app_port: int = Field(8000, ge=1, le=65535, description="Port to listen on.")
    app_workers: int = Field(
        1, ge=1, description="Worker processes. More than 1 requires a shared cache (not 'memory')."
    )
    app_reload: bool = Field(False, description="Restart on code changes (development).")
    uvicorn_log_level: LogLevelLower = Field("warning", description="Uvicorn server log level.")
    log_uvicorn: bool = Field(False, description="Print an access-log line per request.")
    trusted_proxy_count: int = Field(
        0,
        ge=0,
        description="Reverse proxies in front of the app. >0 trusts X-Forwarded-For for client IPs. Set it behind any proxy: with 0 every client shares the proxy's address, so one client can exhaust the login rate limit for everyone.",
    )

    # ---------------------------------------------------------------------- http/api
    cors_origins: list[str] = Field(
        default_factory=list,
        description="Allowed browser origins, e.g. ['https://app.example.com']. localhost origins are trusted only when app_debug is on.",
    )
    cors_allow_credentials: bool = Field(
        True, description="Allow cookies on cross-origin requests."
    )
    cors_expose_headers: list[str] = Field(
        default_factory=lambda: [
            "X-Request-ID",
            "Retry-After",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Idempotent-Replayed",
        ],
        description="Response headers browsers may read.",
    )
    public_paths: list[str] = Field(
        default_factory=lambda: [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/live",
            "/api/v1/ready",
            "/api/v1/startup",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/reset-password-request",
            "/api/v1/auth/reset-password-confirm",
            "/api/v1/oauth/{provider}/authorize",
            "/api/v1/oauth/{provider}/callback",
        ],
        description="Paths that need no login. Whole path segments; {name} matches one segment.",
    )
    admin_only_paths: list[str] = Field(
        default_factory=lambda: ["/api/v1/rbac", "/api/v1/admin", "/api/v1/metrics"],
        description="Paths that need the '*' permission (administrators).",
    )
    request_timeout_seconds: float = Field(
        30.0, gt=0, description="Default per-request time limit."
    )
    endpoint_timeouts: dict[str, float] = Field(
        default_factory=dict,
        description="Per-path-prefix time limits, e.g. {'/api/v1/files/upload' = 600}.",
    )
    timeout_enabled: bool = Field(True, description="Enforce the time limit and concurrency cap.")
    max_concurrent_requests: int = Field(
        100, ge=1, description="In-flight request cap before queueing/503."
    )
    queue_wait_seconds: float = Field(
        5.0, ge=0, description="How long a request waits for a slot before 503."
    )
    max_request_body_bytes: int | None = Field(
        None, description="Largest accepted request body. Default: file_max_size + 1 MiB."
    )
    request_body_idle_timeout_seconds: float = Field(
        15.0,
        gt=0,
        description="A client that sends no body bytes for this long is cut off (408).",
    )
    csrf_origin_check: bool = Field(
        True,
        description="Refuse cookie-authenticated writes whose Origin/Referer is not an allowed origin.",
    )
    request_id_header: str = Field("X-Request-ID", description="Header carrying the request id.")
    idempotency_ttl_seconds: int = Field(
        86400, ge=60, description="How long a POST's Idempotency-Key result is replayed."
    )

    # ------------------------------------------------------------------ rate limiting
    rate_limit_enabled: bool = Field(True, description="Throttle requests per client and tier.")
    rate_limit_algorithm: Literal["sliding_window", "fixed_window"] = Field(
        "sliding_window", description="Window algorithm."
    )
    rate_limit_requests: int = Field(100, ge=1, description="Default requests per window.")
    rate_limit_window: int = Field(60, ge=1, description="Default window in seconds.")
    rate_limit_prefix: str = Field("rate_limit:", description="Cache key prefix for counters.")
    rate_limit_tiers: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "auth": {
                "requests": 10,
                "window": 300,
                "patterns": ["/auth/login", "/auth/register", "/auth/reset"],
            }
        },
        description="Stricter limits for paths containing any of 'patterns'.",
    )

    # ---------------------------------------------------------------------- security
    enable_security_headers: bool = Field(True, description="Send X-Frame-Options, nosniff, etc.")
    enable_hsts: bool = Field(True, description="Send Strict-Transport-Security over HTTPS.")
    hsts_max_age: int = Field(31536000, ge=0, description="HSTS lifetime in seconds.")
    hsts_include_subdomains: bool = Field(True, description="HSTS applies to subdomains.")
    hsts_preload: bool = Field(False, description="Mark HSTS for browser preload lists.")
    frame_options: str = Field("DENY", description="X-Frame-Options value.")
    content_type_nosniff: bool = Field(True, description="Send X-Content-Type-Options: nosniff.")
    xss_protection: bool = Field(
        True, description="Send X-XSS-Protection: 0 (disables the legacy auditor)."
    )
    referrer_policy: str = Field(
        "strict-origin-when-cross-origin", description="Referrer-Policy value."
    )
    csp_enabled: bool | None = Field(
        None, description="Send a Content-Security-Policy. Default: on unless app_debug."
    )
    csp_directives: dict[str, list[str]] | None = Field(
        None, description="Override the default CSP directives."
    )
    permissions_policy_enabled: bool = Field(True, description="Send Permissions-Policy.")
    permissions_policy: dict[str, list[str]] | None = Field(
        None, description="Override the default Permissions-Policy."
    )

    # -------------------------------------------------------------------------- auth
    jwt_secret: str | None = Field(
        None,
        repr=False,
        description=f"Token signing key (>= {MIN_JWT_SECRET_LENGTH} chars). Generated into config.secrets.toml if unset.",
    )
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = Field(
        "HS256", description="Token signing algorithm."
    )
    access_token_minutes: int = Field(15, ge=1, description="Access token lifetime.")
    refresh_token_days: int = Field(7, ge=1, description="Refresh token / session lifetime.")
    remember_me_days: int = Field(
        30, ge=1, description="Refresh token / session lifetime with 'remember me'."
    )
    auth_max_failed_logins: int = Field(
        5, ge=1, description="Failed logins before the account locks."
    )
    auth_lockout_minutes: int = Field(
        15, ge=1, description="How long a locked account stays locked."
    )
    mfa_encryption_key: str | None = Field(
        None,
        repr=False,
        description="Encrypts two-factor secrets at rest. Generated into config.secrets.toml if unset; changing it disables everyone's two-factor setup.",
    )
    mfa_issuer: str | None = Field(
        None, description="Name authenticator apps show next to the account. Default: app_title."
    )
    mfa_recovery_codes: int = Field(
        10,
        ge=1,
        le=20,
        description="Single-use recovery codes issued when two-factor is turned on.",
    )
    mfa_challenge_minutes: int = Field(
        5,
        ge=1,
        le=15,
        description="How long the password step of a two-factor sign-in stays valid.",
    )
    api_token_max_days: int = Field(
        365, ge=1, description="Longest lifetime a personal access token may be given."
    )
    api_tokens_per_user: int = Field(
        20, ge=1, description="Most personal access tokens one user may hold at once."
    )
    auth_refresh_reuse_grace_seconds: int = Field(
        30, ge=0, description="A rotated refresh token still works this long (parallel tabs)."
    )
    password_min_length: int = Field(8, ge=1, description="Minimum password length.")
    password_require_uppercase: bool = Field(
        True, description="Passwords need an uppercase letter."
    )
    password_require_lowercase: bool = Field(True, description="Passwords need a lowercase letter.")
    password_require_digit: bool = Field(True, description="Passwords need a digit.")
    password_require_special: bool = Field(True, description="Passwords need a special character.")
    password_reset_token_lifetime: int = Field(
        3600, ge=60, description="Reset link validity in seconds."
    )
    password_reset_url_template: str | None = Field(
        None,
        description="Link emailed to users, with {token}, e.g. 'https://app/reset?token={token}'.",
    )
    cookie_httponly: bool = Field(True, description="Auth cookies are invisible to JavaScript.")
    cookie_secure: bool | None = Field(
        None, description="Cookies only over HTTPS. Default: on unless app_debug."
    )
    cookie_samesite: Literal["lax", "strict", "none"] = Field(
        "lax", description="SameSite attribute of cookies."
    )
    bootstrap_admin_username: str | None = Field(
        None, description="First administrator (created once if no users exist)."
    )
    bootstrap_admin_email: str | None = Field(None, description="First administrator's email.")
    bootstrap_admin_password: str | None = Field(
        None, repr=False, description="First administrator's password."
    )

    # ------------------------------------------------------ background jobs and audit
    jobs_run_in_api: bool = Field(
        True,
        description="Run the background job worker inside each API process. Turn off when running `python -m app.jobs` separately.",
    )
    jobs_poll_seconds: float = Field(
        2.0, gt=0, description="How often an idle job worker looks for due jobs."
    )
    jobs_batch_size: int = Field(10, ge=1, le=500, description="Jobs one worker claims per pass.")
    jobs_max_attempts: int = Field(
        5, ge=1, description="Attempts before a failing job is moved to 'dead'."
    )
    jobs_timeout_seconds: float = Field(
        300.0, gt=0, description="Time limit for one job attempt; the lease is twice this."
    )
    jobs_retry_base_seconds: float = Field(
        10.0, gt=0, description="Base of the exponential retry delay (with full jitter)."
    )
    jobs_retention_days: int = Field(
        14, ge=1, description="How long finished (done or dead) jobs are kept."
    )
    audit_retention_days: int = Field(
        365, ge=1, description="How long security audit events are kept before they expire."
    )

    # ---------------------------------------------------------------------- database
    app_database_provider: str = Field(
        "mongodb", description="'mongodb', 'postgres' or 'package.module:YourDatabase'."
    )
    app_database: str = Field(
        "fastapi_boilerplate", description="Database name (MongoDB) or schema name (PostgreSQL)."
    )
    mongo_host: str = Field("localhost", description="MongoDB host.")
    mongo_port: int = Field(27017, ge=1, le=65535, description="MongoDB port.")
    mongo_username: str = Field("", description="MongoDB user (empty = no authentication).")
    mongo_password: str = Field("", repr=False, description="MongoDB password.")
    mongo_auth_source: str = Field("admin", description="Database holding the MongoDB user.")
    mongo_direct_connection: bool = Field(
        False, description="Skip replica-set discovery (single-node dev only)."
    )
    mongo_pool_size: int = Field(100, ge=1, description="Maximum pooled connections.")
    mongo_min_pool_size: int = Field(10, ge=0, description="Connections kept open.")
    mongo_max_idle_time_ms: int = Field(
        30000, ge=0, description="Close pooled connections idle this long."
    )
    mongo_timeout_ms: int = Field(
        5000, ge=100, description="Server selection, connect and socket timeout."
    )
    mongo_wait_queue_timeout_ms: int = Field(
        5000, ge=0, description="Wait for a free connection this long."
    )

    postgres_host: str = Field(
        "localhost", description="PostgreSQL host (app_database_provider = 'postgres')."
    )
    postgres_port: int = Field(5432, ge=1, le=65535, description="PostgreSQL port.")
    postgres_username: str = Field("fabp", description="PostgreSQL user.")
    postgres_password: str = Field("", repr=False, description="PostgreSQL password.")
    postgres_database: str = Field(
        "fabp", description="PostgreSQL database; each app_database is a schema inside it."
    )
    postgres_pool_size: int = Field(
        20, ge=1, description="Most PostgreSQL connections per process."
    )
    postgres_min_pool_size: int = Field(1, ge=0, description="Connections kept open when idle.")
    postgres_timeout_seconds: float = Field(
        10.0, gt=0, description="Connect and per-statement time limit."
    )
    postgres_ttl_purge_seconds: int = Field(
        60,
        ge=0,
        description="Seconds between deletions of records past their time-to-live (0 = never).",
    )

    # ------------------------------------------------------------------------- cache
    app_cache_provider: str = Field(
        "redis", description="'redis', 'memory' or 'package.module:YourCache'."
    )
    cache_default_ttl: int = Field(
        300, ge=1, description="Default cache entry lifetime in seconds."
    )
    cache_prefix: str = Field("cache:", description="Key prefix for cached values.")
    cache_timeout_seconds: float = Field(
        1.0, gt=0, description="Redis connect/read timeout. Short: the database is the fallback."
    )
    cache_failure_cooldown_seconds: int = Field(
        10,
        ge=1,
        description="After a cache failure, skip the cache this long instead of retrying every request.",
    )
    redis_host: str = Field("localhost", description="Redis host.")
    redis_port: int = Field(6379, ge=1, le=65535, description="Redis port.")
    redis_password: str | None = Field(None, repr=False, description="Redis password.")
    redis_max_connections: int = Field(50, ge=1, description="Redis connection pool size.")

    # ------------------------------------------------------------------------- files
    file_storage_backend: str = Field(
        "local",
        description="'local' (one host), 's3' (shared, S3-compatible) or 'package.module:YourStorage'.",
    )
    file_storage_base_path: str = Field(
        "uploads", description="Directory for the local storage backend."
    )
    s3_bucket: str = Field("", description="Bucket for file_storage_backend = 's3'.")
    s3_key_prefix: str = Field("", description="Folder inside the bucket (empty = bucket root).")
    s3_region: str | None = Field(None, description="Bucket region (empty = boto3's default).")
    s3_endpoint_url: str | None = Field(
        None, description="Endpoint of an S3-compatible service (MinIO, R2, ...); empty = AWS."
    )
    s3_access_key_id: str | None = Field(
        None, description="Empty = boto3's credential chain (env vars, IAM role, ...)."
    )
    s3_secret_access_key: str | None = Field(None, repr=False, description="Secret for the key id.")
    s3_part_size: int = Field(
        8388608, ge=5242880, description="Multipart upload part size (S3 minimum 5 MiB)."
    )
    s3_max_connections: int = Field(50, ge=1, description="HTTP connections kept to the store.")
    file_download_redirect: bool = Field(
        False,
        description="Redirect downloads to a short-lived direct URL when the storage backend "
        "offers one (S3), so file bytes bypass the API.",
    )
    file_download_url_ttl: int = Field(
        300, ge=1, description="Lifetime in seconds of direct download URLs."
    )
    file_cleanup_interval: int = Field(
        3600,
        ge=0,
        description="Seconds between purges of abandoned chunked-upload data (0 = never).",
    )
    file_max_size: int = Field(
        104857600, ge=1, description="Largest single file in bytes (100 MB)."
    )
    file_user_quota_bytes: int = Field(
        5_368_709_120,
        ge=0,
        description="Total stored bytes per user, soft-deleted files included (0 = unlimited).",
    )
    file_max_versions: int = Field(100, ge=1, description="Most versions one file may accumulate.")
    file_chunk_size: int = Field(
        5242880, ge=1, description="Largest chunk of a chunked upload (5 MB)."
    )
    file_upload_ttl: int = Field(
        3600, ge=60, description="Abandoned chunked uploads expire after this many seconds."
    )
    file_allowed_types: list[str] = Field(
        default_factory=lambda: [
            "image/*",
            "application/pdf",
            "text/*",
            "application/json",
            "application/xml",
            "application/yaml",
            "application/x-yaml",
            "application/zip",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.oasis.opendocument.spreadsheet",
        ],
        description="Accepted MIME types ('type/*' wildcards allowed). Empty = everything not blocked.",
    )
    file_blocked_types: list[str] = Field(
        default_factory=lambda: ["text/html", "application/xhtml+xml", "image/svg+xml"],
        description="Never accepted: browsers would run these as active content.",
    )
    file_versioning_enabled: bool = Field(True, description="Allow multiple versions per file.")
    file_deduplication_enabled: bool = Field(
        True, description="Re-uploading identical bytes returns your existing file."
    )
    file_image_processing_enabled: bool = Field(True, description="Generate thumbnails for images.")
    file_thumbnail_sizes: list[int] = Field(
        default_factory=lambda: [150, 300, 600], description="Thumbnail sizes in px."
    )
    file_spreadsheet_processing_enabled: bool = Field(
        True, description="Enable spreadsheet read/edit endpoints."
    )
    file_spreadsheet_max_cells: int = Field(
        1_000_000, ge=1, description="Largest spreadsheet accepted for edits."
    )

    # ---------------------------------------------------------------------- rbac/oauth
    rbac_permission_cache_ttl: int = Field(
        300, ge=1, description="Seconds a user's resolved permissions are cached."
    )
    rbac_roles: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {"admin": {"permissions": ["*"]}, "user": {"permissions": []}},
        description="Role definitions: permissions, optional 'inherits'. Edit in config.toml.",
    )
    rbac_groups: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Group definitions: {'roles': [...]}. Edit in config.toml.",
    )
    default_role: str = Field("user", description="Role given to users who register themselves.")
    oauth_enabled: bool = Field(False, description="Enable sign-in with an identity provider.")
    oauth_providers: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Provider settings (client_id, client_secret, urls). See config.toml.",
    )

    # ------------------------------------------------------------------- observability
    log_level: LogLevel = Field("INFO", description="Minimum log level.")
    logs_path: str = Field("logs", description="Directory for log files.")
    log_to_file: bool = Field(True, description="Also write JSON lines to <logs_path>/app.log.")
    log_max_bytes: int = Field(10_485_760, ge=1024, description="Rotate the log file at this size.")
    log_backup_count: int = Field(5, ge=0, description="Rotated log files to keep.")
    log_enable_trace_correlation: bool = Field(
        True, description="Put the trace id into the request id in logs."
    )
    metrics_enabled: bool = Field(
        False, description="Collect Prometheus metrics (served at /api/v1/metrics, admin only)."
    )
    tracing_enabled: bool = Field(False, description="Export OpenTelemetry traces.")
    otlp_endpoint: str | None = Field(
        None, description="OTLP collector, e.g. 'http://localhost:4317'."
    )
    otlp_insecure: bool = Field(True, description="Plain-text connection to the collector.")
    tracing_sample_rate: float = Field(0.1, ge=0, le=1, description="Fraction of requests traced.")
    tracing_redis: bool = Field(True, description="Trace Redis calls.")
    tracing_mongodb: bool = Field(True, description="Trace MongoDB calls.")
    sentry_enabled: bool = Field(False, description="Report errors to Sentry.")
    sentry_dsn: str | None = Field(None, repr=False, description="Sentry project DSN.")
    sentry_environment: str | None = Field(
        None, description="Sentry environment label. Default: environment."
    )
    sentry_traces_sample_rate: float = Field(
        0.1, ge=0, le=1, description="Fraction of requests traced by Sentry."
    )
    sentry_profiles_sample_rate: float = Field(
        0.0, ge=0, le=1, description="Fraction profiled by Sentry."
    )

    # ------------------------------------------------------------------------- email
    smtp_host: str | None = Field(
        None, description="SMTP server for password-reset mail (unset = mail is only logged)."
    )
    smtp_port: int = Field(587, ge=1, le=65535, description="SMTP port.")
    smtp_starttls: bool = Field(True, description="Upgrade the SMTP connection with STARTTLS.")
    smtp_username: str | None = Field(None, description="SMTP user.")
    smtp_password: str | None = Field(None, repr=False, description="SMTP password.")
    smtp_from: str = Field("no-reply@localhost", description="From address.")

    @field_validator("jwt_secret", "mfa_encryption_key")
    @classmethod
    def _long_enough(cls, value: str | None) -> str | None:
        if value is not None and len(value) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(f"must be at least {MIN_JWT_SECRET_LENGTH} characters")
        if value is not None and value.lower().startswith("change-me"):
            raise ValueError("is still the placeholder from .env.example; run `make setup`")
        return value

    @model_validator(mode="after")
    def _derive_environment_dependent_defaults(self) -> Settings:
        """Fill the settings whose default depends on app_debug."""
        if self.cookie_secure is None:
            self.cookie_secure = not self.app_debug
        if self.csp_enabled is None:
            self.csp_enabled = not self.app_debug
        if self.sentry_environment is None:
            self.sentry_environment = self.environment
        if self.max_request_body_bytes is None:
            self.max_request_body_bytes = self.file_max_size + 1_048_576
        for role_id, role in self.rbac_roles.items():
            for parent in role.get("inherits", []):
                if parent not in self.rbac_roles:
                    raise ValueError(f"rbac_roles.{role_id} inherits unknown role '{parent}'")
        for group_id, group in self.rbac_groups.items():
            for role_id in group.get("roles", []):
                if role_id not in self.rbac_roles:
                    raise ValueError(f"rbac_groups.{group_id} references unknown role '{role_id}'")
        if self.default_role not in self.rbac_roles:
            raise ValueError(f"default_role '{self.default_role}' is not defined in rbac_roles")
        if self.file_storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("file_storage_backend = 's3' needs s3_bucket")
        if self.app_workers > 1 and self.app_cache_provider == "memory":
            # Each worker would keep its own rate-limit counters, sessions and
            # idempotency claims, silently multiplying every limit by the worker count.
            raise ValueError(
                "app_cache_provider = 'memory' is per process and cannot be used with "
                f"app_workers = {self.app_workers}; set app_cache_provider = 'redis'"
            )
        return self


# Section headings for the generated reference: heading -> first setting in that section.
SECTIONS = {
    "app_title": "Application",
    "cors_origins": "HTTP and API",
    "rate_limit_enabled": "Rate limiting",
    "enable_security_headers": "Security headers",
    "jwt_secret": "Authentication",
    "jobs_run_in_api": "Background jobs and audit",
    "app_database_provider": "Database",
    "app_cache_provider": "Cache",
    "file_storage_backend": "Files",
    "rbac_permission_cache_ttl": "Access control and OAuth",
    "log_level": "Logging, metrics, tracing, Sentry",
    "smtp_host": "Email",
}


def reference_markdown() -> str:
    """The settings reference (docs/CONFIGURATION.md), generated from the model."""
    lines = [
        "# Configuration reference",
        "",
        "_Generated by `python -m app.settings docs`; do not edit by hand._",
        "",
        (Settings.__doc__ or "").strip(),
        "",
        (__doc__ or "").split("Unknown names")[0].strip().split("\n\n", 1)[1],
        "",
    ]
    for name, field in Settings.model_fields.items():
        if name in SECTIONS:
            lines += [
                "",
                f"## {SECTIONS[name]}",
                "",
                "| Setting | Type | Default | Description |",
                "| --- | --- | --- | --- |",
            ]
        default = "_unset_" if field.default is None else f"`{field.default!r}`"
        if field.default_factory is not None:
            default = f"`{field.default_factory()!r}`"
        if len(default) > 70:
            default = (
                "_see config.toml_"
                if name.startswith("rbac") or name.startswith("oauth")
                else default[:67] + "..`"
            )
        kind = (
            str(field.annotation).replace("typing.", "").replace("<class '", "").replace("'>", "")
        )
        lines.append(f"| `{name}` | {kind} | {default} | {field.description or ''} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """``python -m app.settings [docs|show|check]``."""
    import sys

    from config import Config, ConfigError

    command = (argv if argv is not None else sys.argv[1:] or ["show"])[0]
    if command == "docs":
        print(reference_markdown(), end="")
        return 0
    try:
        config = Config()
    except ConfigError as e:
        print(f"Configuration is invalid:\n{e}", file=sys.stderr)
        return 1
    if command == "check":
        print("Configuration OK")
        return 0
    if command == "show":
        for key, value in config.items():
            shown = (
                "***" if value and any(w in key for w in ("secret", "password", "dsn")) else value
            )
            origin = config.origins.get(key, "default")
            print(f"{key} = {shown!r}   # {origin}")
        return 0
    print("usage: python -m app.settings [show|check|docs]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
