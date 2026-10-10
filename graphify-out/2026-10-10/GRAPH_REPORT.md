# Graph Report - Fast-API-Boiler-Plate  (2026-10-10)

## Corpus Check
- 160 files · ~116,835 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 7, .example 2, .toml 1)

## Summary
- 2275 nodes · 5218 edges · 138 communities (74 shown, 64 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 582 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1a97b49e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_xlsx_patch.py
- CacheService
- e
- auth.py
- typing
- MongoDB
- Config
- test_files.py
- permissions.py
- app.py
- update_spreadsheet
- AuthService
- LocalStorage
- spreadsheet.py
- SpreadsheetProcessor
- middleware/base.py
- .upload_stream
- TemporaryPermissionsOps
- test_middleware.py
- Logger
- test_data_layer.py
- StorageInterface
- S3Storage
- UsersOps
- ChunkedUploadHandler
- run
- test_auth_flow.py
- RBACMiddleware
- TokenPayload
- DataService
- RBACService
- test_security_fixes.py
- README.md
- conftest.py
- PasswordService
- Services
- get_current_user
- test_route_access.py
- OAuthService
- FilesOps
- build_services
- FakeDatabase
- BaseMiddleware
- password.py
- not_found
- assign_group
- DatabaseInterface
- SessionsOps
- routes/rbac.py
- test_oauth_state.py
- test_operations.py
- Collections
- routes/sessions.py
- oauth/base.py
- Any
- Engineering standards
- .handle
- MemoryCache
- RedisCache
- OAuthProvider
- GoogleOAuthProvider
- .resolve_user_permissions
- test_features.py
- .__call__
- IdempotencyMiddleware
- DatabaseService
- require_any_role
- make_user
- OAuthOps
- tracing.py
- .handle
- .format_error
- Configuration reference
- test_cache_degradation.py
- .format
- Operations runbook
- FastAPI Boilerplate: production-ready FastAPI + MongoDB + Redis starter
- CSRFOriginMiddleware
- .handle
- utils.py
- Configure common features
- Getting started
- Add a resource
- .__init__
- Contributing
- run_migrations
- MeteredStream
- For decision makers
- role.py
- test_smtp_starttls_verifies_the_server_certificate
- .handle
- upload_new_version
- ensure_bootstrap_admin
- ._encode
- Code of Conduct
- Security model
- Deploy
- body_limit.py
- FileService
- FileResponse
- [1.0.0] - 2026-10-10
- data_service
- 0005: Scale-out file handling and cache resilience
- Documentation
- pull_request_template.md
- For designers
- Security policy
- .handle
- User
- test_streamed_oversize_body_without_content_length_is_rejected
- fastapi-boilerplate
- create_temporary_permission
- limited_client

## God Nodes (most connected - your core abstractions)
1. `Config` - 141 edges
2. `Logger` - 111 edges
3. `DataService` - 72 edges
4. `TokenPayload` - 70 edges
5. `AuthService` - 65 edges
6. `FileService` - 58 edges
7. `e()` - 50 edges
8. `RBACService` - 46 edges
9. `StorageInterface` - 42 edges
10. `run()` - 42 edges

## Surprising Connections (you probably didn't know these)
- `FAQ` --references--> `DatabaseInterface`  [INFERRED]
  README.md → app/core/interfaces/database_interface.py
- ``sessions` (`SessionsOps`)` --references--> `SessionsOps`  [INFERRED]
  docs/reference/data-model.md → app/services/data/sessions_ops.py
- ``temporary_permissions` (`TemporaryPermissionsOps`)` --references--> `TemporaryPermissionsOps`  [INFERRED]
  docs/reference/data-model.md → app/services/data/temp_permissions_ops.py
- ``users` (`UsersOps`)` --references--> `UsersOps`  [INFERRED]
  docs/reference/data-model.md → app/services/data/users_ops.py
- `0004: Plain service wiring and pluggable backends` --references--> `build_services()`  [INFERRED]
  docs/adr/0004-plain-wiring-and-pluggable-backends.md → app/services/registry.py

## Import Cycles
- 3-file cycle: `app/services/file/__init__.py -> app/services/file/file_service.py -> app/services/file/spreadsheet_processor.py -> app/services/file/__init__.py`

## Communities (138 total, 64 thin omitted)

### Community 0 - "test_xlsx_patch.py"
Cohesion: 0.06
Nodes (30): _add_sheet(), _delete_sheet(), _drop_calculation_state(), edit_xlsx(), _insert_before(), _Package, _parse_xml(), _sheet_parts() (+22 more)

### Community 1 - "CacheService"
Cohesion: 0.04
Nodes (4): CacheInterface, CacheUnavailableError, RateDecision, CacheService

### Community 2 - "e"
Cohesion: 0.06
Nodes (56): body(), body(), body(), infra(), body(), body(), body(), body() (+48 more)

### Community 3 - "auth.py"
Cohesion: 0.09
Nodes (14): register(), get_current_user_info(), update_my_profile(), get_user(), list_users(), _public(), set_user_status(), ProfileUpdate (+6 more)

### Community 6 - "Config"
Cohesion: 0.06
Nodes (18): main(), reference_markdown(), Settings, Config, ConfigError, Other common changes, main(), test_config_behaves_like_a_mapping_and_rejects_unknown_attributes() (+10 more)

### Community 7 - "test_files.py"
Cohesion: 0.11
Nodes (38): blue_png(), chunk(), create_sheet(), png_bytes(), signed_in(), test_a_second_user_cannot_inject_into_or_finish_anothers_upload(), test_abandoned_chunked_uploads_are_purged_once_older_than_the_session_lifetime(), test_active_content_types_are_rejected() (+30 more)

### Community 8 - "permissions.py"
Cohesion: 0.08
Nodes (16): get_auth_service(), get_data_service(), get_file_service(), get_oauth_service(), get_rbac_service(), get_services(), login(), logout() (+8 more)

### Community 9 - "app.py"
Cohesion: 0.08
Nodes (9): AppFactory, create_app(), AccessLogMiddleware, BodySizeLimitMiddleware, RateLimiter, RequestIDMiddleware, SecurityHeadersMiddleware, SessionMiddleware (+1 more)

### Community 10 - "update_spreadsheet"
Cohesion: 0.12
Nodes (10): _bad_request(), create_spreadsheet_file(), delete_sheet(), get_spreadsheet_info(), _info(), _owned_spreadsheet(), _processor(), read_spreadsheet() (+2 more)

### Community 11 - "AuthService"
Cohesion: 0.06
Nodes (7): logout_all_devices(), delete_user(), LoginResponse, DeviceInfo, AuthService, SessionManager, Threats and controls

### Community 13 - "spreadsheet.py"
Cohesion: 0.09
Nodes (10): _parse_metadata(), ChunkUploadResponse, FileListResponse, FileMetadata, FileUpdateRequest, SpreadsheetCreateRequest, SpreadsheetData, SpreadsheetReadResponse (+2 more)

### Community 14 - "SpreadsheetProcessor"
Cohesion: 0.11
Nodes (5): neutralize(), SpreadsheetProcessor, with_headers(), validate_sheet_name(), test_parsing_stops_at_the_cell_limit()

### Community 18 - "test_middleware.py"
Cohesion: 0.08
Nodes (7): ErrorHandlerMiddleware, TimeoutMiddleware, build(), stream(), test_escaping_exceptions_become_generic_problem_500s(), test_slow_requests_get_a_504(), test_streaming_responses_pass_through_intact()

### Community 19 - "Logger"
Cohesion: 0.16
Nodes (3): _JsonFormatter, Logger, _RequestIdFilter

### Community 20 - "test_data_layer.py"
Cohesion: 0.12
Nodes (7): file_record(), rbac(), test_deleted_file_leaves_the_listing_and_all_versions_are_flagged(), test_find_many_does_not_write_list_results_to_cache(), test_listing_returns_newest_version_of_each_file_paged_in_the_database(), test_migration_flags_the_newest_version_of_existing_files(), test_providers_resolve_builtin_names_and_dotted_paths()

### Community 21 - "StorageInterface"
Cohesion: 0.07
Nodes (4): StorageInterface, create_storage(), Bring your own backend, Layers

### Community 22 - "S3Storage"
Cohesion: 0.17
Nodes (4): _is_missing(), S3Storage, collect(), send_part()

### Community 23 - "UsersOps"
Cohesion: 0.11
Nodes (3): normalize_user(), UsersOps, test_legacy_user_fields_are_normalised()

### Community 24 - "ChunkedUploadHandler"
Cohesion: 0.11
Nodes (3): ChunkedUploadHandler, pieces(), UploadSizeMismatchError

### Community 25 - "run"
Cohesion: 0.15
Nodes (20): run(), chunked(), collect(), collect_from(), failing_after(), _pieces(), test_a_failing_stream_leaves_nothing_behind(), test_open_stream_of_a_missing_file_is_none() (+12 more)

### Community 26 - "test_auth_flow.py"
Cohesion: 0.20
Nodes (21): bearer(), login(), make_admin(), register(), test_access_token_cannot_be_used_as_a_refresh_token(), test_cookie_and_bearer_both_authenticate(), test_duplicate_email_is_rejected(), test_every_login_attempt_is_recorded_in_the_audit_log() (+13 more)

### Community 27 - "RBACMiddleware"
Cohesion: 0.11
Nodes (3): RBACMiddleware, AppExceptionError, UserFacingExceptionError

### Community 28 - "TokenPayload"
Cohesion: 0.13
Nodes (6): TokenPair, TokenPayload, TokenManager, require_admin(), require_role(), _silent_refresh()

### Community 31 - "test_security_fixes.py"
Cohesion: 0.14
Nodes (16): _ConsoleFormatter, bearer(), make_user(), test_a_file_cannot_collect_unbounded_versions(), test_bearer_requests_are_not_subject_to_the_origin_check(), test_chunks_much_larger_than_the_declared_average_are_refused(), test_console_log_lines_cannot_be_forged_by_request_text(), test_cookie_authenticated_writes_from_foreign_origins_are_refused() (+8 more)

### Community 32 - "README.md"
Cohesion: 0.24
Nodes (3): 0001: Tokens are bound to a server-side session, 0002: The service is API-only, 0004: Plain service wiring and pluggable backends

### Community 33 - "conftest.py"
Cohesion: 0.18
Nodes (4): _send_blocking(), send_email(), send_password_reset_email(), config()

### Community 34 - "PasswordService"
Cohesion: 0.07
Nodes (3): UserCreate, UserManager, PasswordService

### Community 35 - "Services"
Cohesion: 0.11
Nodes (15): health_check(), liveness_check(), metrics_endpoint(), _now(), readiness_check(), startup_check(), Services, Architecture (+7 more)

### Community 36 - "get_current_user"
Cohesion: 0.24
Nodes (4): set_user(), authenticate_request(), extract_access_token(), get_current_user()

### Community 37 - "test_route_access.py"
Cohesion: 0.13
Nodes (9): _compile_patterns(), path_matches(), permissions_of(), required_permissions(), test_every_authenticated_api_route_is_grantable_to_a_normal_user(), test_public_paths_match_whole_segments(), test_sensitive_surfaces_are_admin_only(), test_staff_only_permissions_are_held_by_managers_but_not_users() (+1 more)

### Community 38 - "OAuthService"
Cohesion: 0.12
Nodes (6): authorize_oauth(), link_oauth_account(), oauth_callback(), _state_cookie_name(), unlink_oauth_account(), OAuthService

### Community 40 - "build_services"
Cohesion: 0.07
Nodes (6): Where things go, ErrorService, MetricsService, build_services(), SentryService, Observability (optional, off by default)

### Community 43 - "password.py"
Cohesion: 0.09
Nodes (8): change_password(), confirm_password_reset(), request_password_reset(), ChangePasswordRequest, PasswordResetConfirm, PasswordResetRequest, AuthenticationError, hash_token()

### Community 44 - "not_found"
Cohesion: 0.15
Nodes (6): content_disposition(), not_found(), serve_stored_file(), download_file(), download_thumbnail(), get_file_metadata()

### Community 45 - "assign_group"
Cohesion: 0.22
Nodes (5): assign_group(), assign_role(), _not_found(), remove_role(), revoke_temporary_permission()

### Community 46 - "DatabaseInterface"
Cohesion: 0.12
Nodes (5): create_cache(), DatabaseInterface, load_backend_class(), create_database(), Ways to help

### Community 48 - "routes/rbac.py"
Cohesion: 0.24
Nodes (5): get_user_permissions(), list_groups(), list_permissions(), list_roles(), require_permission()

### Community 50 - "test_operations.py"
Cohesion: 0.15
Nodes (9): build_test_app(), cors_client(), metrics_env(), test_cors_preflight_is_answered_without_credentials(), test_probes_are_public_and_never_500(), test_rate_limit_answers_429_with_retry_after_and_is_per_client_tier(), test_security_headers_and_cors_are_present_even_on_rejections(), test_two_apps_in_one_process_do_not_collide_on_metric_names() (+1 more)

### Community 51 - "Collections"
Cohesion: 0.24
Nodes (11): Collections, `files` (`FilesOps`), `login_attempts`, `oauth_accounts` (`OAuthOps`), `password_reset_tokens`, `schema_migrations`, `sessions` (`SessionsOps`), `temporary_permissions` (`TemporaryPermissionsOps`) (+3 more)

### Community 52 - "routes/sessions.py"
Cohesion: 0.18
Nodes (6): get_session_details(), list_active_sessions(), _own_session(), _public_view(), revoke_all_sessions(), revoke_session()

### Community 53 - "oauth/base.py"
Cohesion: 0.18
Nodes (3): OAuthAccount, OAuthToken, UserRole

### Community 54 - "Any"
Cohesion: 0.12
Nodes (3): _convert_datetime_strings(), _default_cache_key(), _normalize_record()

### Community 55 - "Engineering standards"
Cohesion: 0.18
Nodes (11): 10. Style, docs and commits, 11. Definition of done, 12. AI-written contributions, 1. Before writing code, 2. Principles, 3. Architecture, 7. Security and configuration, 8. Errors and observability (+3 more)

### Community 57 - "MemoryCache"
Cohesion: 0.16
Nodes (3): MemoryCache, test_memory_cache_expiry_and_prefix_delete(), test_memory_cache_rate_limit_windows()

### Community 59 - "OAuthProvider"
Cohesion: 0.17
Nodes (5): OAuthProvider, OAuthUserInfo, OAuthBase, test_oauth_sign_in_does_not_inherit_a_pre_registered_unverified_account(), test_unlinked_provider_identity_cannot_sign_in()

### Community 61 - ".resolve_user_permissions"
Cohesion: 0.22
Nodes (3): expand(), Access control, 5. Code

### Community 62 - "test_features.py"
Cohesion: 0.25
Nodes (14): admin_client(), signed_in(), test_admins_cannot_disable_themselves_and_unknown_users_404(), test_change_password_needs_the_current_one_and_ends_other_sessions(), test_failed_requests_are_not_stored_so_a_retry_really_retries(), test_keys_are_scoped_per_user_and_validated(), test_large_json_bodies_are_streamed_through_not_buffered(), test_normal_users_cannot_list_users_but_admins_can_with_paging() (+6 more)

### Community 63 - ".__call__"
Cohesion: 0.18
Nodes (8): counting_receive(), tracking_send(), capture_send(), tracking_send(), test_a_stalled_request_body_is_cut_off(), app(), receive(), send()

### Community 64 - "IdempotencyMiddleware"
Cohesion: 0.19
Nodes (3): IdempotencyMiddleware, respond(), _problem()

### Community 65 - "DatabaseService"
Cohesion: 0.20
Nodes (4): _drop_superseded_indexes(), _flag_latest_file_versions(), Migration, DatabaseService

### Community 66 - "require_any_role"
Cohesion: 0.23
Nodes (8): _forbidden(), _log_denied(), require_any_permission(), dependency(), require_any_role(), dependency(), require_manager_or_admin(), dependency()

### Community 67 - "make_user"
Cohesion: 0.24
Nodes (10): make_user(), test_assignments_validate_against_definitions_and_take_effect_at_once(), test_changing_email_drops_the_old_email_lookup(), test_create_user_keeps_its_own_id(), test_deleted_user_is_not_served_from_cache(), test_group_grants_reach_members(), test_permissions_come_from_roles_groups_and_temporary_grants(), test_update_user_refreshes_every_cached_lookup_key() (+2 more)

### Community 72 - "Configuration reference"
Cohesion: 0.17
Nodes (12): Access control and OAuth, Application, Authentication, Cache, Configuration reference, Database, Email, Files (+4 more)

### Community 73 - "test_cache_degradation.py"
Cohesion: 0.18
Nodes (5): cache(), DownBackend, test_after_one_failure_the_backend_is_left_alone_until_the_cooldown_ends(), test_operations_without_a_fallback_say_so(), test_reads_become_misses_and_writes_are_skipped()

### Community 75 - "Operations runbook"
Cohesion: 0.18
Nodes (11): 503 "Server overloaded" or 504 timeouts, A user is locked out, An account or token may be compromised, Disk filling up, Everyone gets 429 Too Many Requests, MongoDB is down or refuses credentials, Operations runbook, Redis is down (+3 more)

### Community 76 - "FastAPI Boilerplate: production-ready FastAPI + MongoDB + Redis starter"
Cohesion: 0.18
Nodes (11): Contributing, Documentation, FAQ, FastAPI Boilerplate: production-ready FastAPI + MongoDB + Redis starter, Features, License, Project structure, Quick start (+3 more)

### Community 80 - "Configure common features"
Cohesion: 0.20
Nodes (10): Change roles, groups and limits, Configure common features, Let a browser front end call the API, Run behind a reverse proxy, Send password-reset email, Sign in with Google, Store files in S3 (or MinIO, R2, ...), Turn on observability (+2 more)

### Community 81 - "Getting started"
Cohesion: 0.20
Nodes (10): 1. Set up, 2. Start the databases, 3. Create the first administrator, 4. Run the API, 5. Register and sign in, 6. Upload and list a file, 7. See access control at work, 8. Explore and test (+2 more)

### Community 82 - "Add a resource"
Cohesion: 0.22
Nodes (6): 1. Model: `app/models/part.py`, 3. Rules: `app/services/part_service.py` (only if needed), 4. Routes: `app/api/routes/parts.py`, 5. Permissions: `config.toml`, 6. Test it through the real app, Add a resource

### Community 84 - ".__init__"
Cohesion: 0.22
Nodes (5): Rules worth knowing, 2. Data: `app/services/data/parts_ops.py`, Data model, Migrations, Rules that keep the data honest

### Community 85 - "Contributing"
Cohesion: 0.22
Nodes (9): Code of Conduct, Commits, Contributing, Conventions, Documentation, Pull request checklist, Releases, Set up (about ten minutes) (+1 more)

### Community 88 - "For decision makers"
Cohesion: 0.25
Nodes (8): Decisions to make before building on it, For decision makers, How it helps the business, Scope: what it leaves to you, What it costs to run, What you can build with it, What you get on day one, Why it can be trusted

### Community 93 - "upload_new_version"
Cohesion: 0.14
Nodes (7): list_files(), upload_new_version(), complete_chunked_upload(), _parse_tags(), _read_limited(), upload_chunk(), upload_file()

### Community 94 - "ensure_bootstrap_admin"
Cohesion: 0.47
Nodes (5): ensure_bootstrap_admin(), make_auth_service(), test_bootstrap_admin_created_only_when_configured_and_empty(), test_bootstrap_admin_skipped_when_users_exist(), test_no_default_admin_without_explicit_config()

### Community 97 - "Code of Conduct"
Cohesion: 0.33
Nodes (5): Code of Conduct, Expected behaviour, Our pledge, Scope and enforcement, Unacceptable behaviour

### Community 98 - "Security model"
Cohesion: 0.33
Nodes (6): Browser defences, Google sign-in, Not covered, Security model, Sessions and tokens, Sign-in protection

### Community 99 - "Deploy"
Cohesion: 0.33
Nodes (6): Build the image, Deploy, Probes, Production checklist, Start-up sequence, Try the whole stack locally

### Community 102 - "FileResponse"
Cohesion: 0.15
Nodes (3): get_file_versions(), update_file(), FileResponse

### Community 104 - "[1.0.0] - 2026-10-10"
Cohesion: 0.40
Nodes (5): [1.0.0] - 2026-10-10, Added, Changelog, [Unreleased], Upgrading from 0.x

### Community 105 - "data_service"
Cohesion: 0.20
Nodes (7): Commands, Rules, What this is, Tests, 6. Tests, data_service(), env()

### Community 116 - "Documentation"
Cohesion: 0.50
Nodes (4): Diagrams, Documentation, Every document, Start here, by role

### Community 117 - "pull_request_template.md"
Cohesion: 0.50
Nodes (3): Checklist, How it was tested, What and why

### Community 118 - "For designers"
Cohesion: 0.25
Nodes (6): Copy rules from security, For designers, Patterns the API expects, Screens and the states they need, The account journey, Turning errors into states

### Community 119 - "Security policy"
Cohesion: 0.50
Nodes (4): Reporting a vulnerability, Scope, Security policy, Supported versions

## Knowledge Gaps
- **123 isolated node(s):** `fastapi-boilerplate`, `What and why`, `How it was tested`, `Checklist`, `What this is` (+118 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1002 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **64 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Config` to `CacheService`, `typing`, `permissions.py`, `app.py`, `AuthService`, `LocalStorage`, `SpreadsheetProcessor`, `middleware/base.py`, `test_middleware.py`, `Logger`, `StorageInterface`, `S3Storage`, `ChunkedUploadHandler`, `TokenPayload`, `DataService`, `RBACService`, `conftest.py`, `PasswordService`, `Services`, `test_route_access.py`, `OAuthService`, `build_services`, `BaseMiddleware`, `DatabaseInterface`, `test_operations.py`, `oauth/base.py`, `OAuthProvider`, `GoogleOAuthProvider`, `DatabaseService`, `tracing.py`, `Any`, `.__init__`, `ensure_bootstrap_admin`, `FileService`?**
  _High betweenness centrality (0.223) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `Config` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Config` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fastapi-boilerplate`, `What and why`, `How it was tested` to the rest of the system?**
  _123 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_xlsx_patch.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06128364389233954 - nodes in this community are weakly interconnected._
- **Why does `Logger` connect `Logger` to `CacheService`, `typing`, `Config`, `app.py`, `AuthService`, `LocalStorage`, `SpreadsheetProcessor`, `middleware/base.py`, `StorageInterface`, `S3Storage`, `ChunkedUploadHandler`, `TokenPayload`, `DataService`, `RBACService`, `conftest.py`, `PasswordService`, `Services`, `OAuthService`, `build_services`, `BaseMiddleware`, `DatabaseInterface`, `oauth/base.py`, `OAuthProvider`, `GoogleOAuthProvider`, `DatabaseService`, `tracing.py`, `Any`, `.__init__`, `run_migrations`, `ensure_bootstrap_admin`, `FileService`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `Logger` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Logger` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Should `CacheService` be split into smaller, more focused modules?**
  _Cohesion score 0.0438715513342379 - nodes in this community are weakly interconnected._