# Graph Report - Fast-API-Boiler-Plate  (2026-10-10)

## Corpus Check
- 161 files · ~118,686 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 7, .example 2, .toml 1)

## Summary
- 2290 nodes · 5259 edges · 131 communities (61 shown, 70 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 597 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1a97b49e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- xlsx_package.py
- CacheUnavailableError
- e
- DataService
- MongoDB
- Config
- test_files.py
- permissions.py
- app.py
- spreadsheet.py
- change_password
- LocalStorage
- upload.py
- SpreadsheetProcessor
- middleware/base.py
- FileService
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
- .refresh_tokens
- data_service.py
- TokenPayload
- test_security_fixes.py
- README.md
- xlsx_patch.py
- AuthService
- health.py
- sentry.py
- test_route_access.py
- OAuthProvider
- FilesOps
- registry.py
- FakeDatabase
- BaseMiddleware
- hash_token
- download.py
- test_xlsx_patch.py
- cache/__init__.py
- SessionsOps
- CacheService
- interface.py
- test_operations.py
- Collections
- Endpoints
- Any
- Engineering standards
- .handle
- MemoryCache
- RedisCache
- test_features.py
- .__call__
- IdempotencyMiddleware
- DatabaseService
- .handle
- .format_error
- Configuration reference
- test_cache_degradation.py
- _ConsoleFormatter
- Operations runbook
- FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter
- CSRFOriginMiddleware
- .handle
- utils.py
- Configure common features
- Getting started
- .__init__
- run_migrations
- MeteredStream
- For decision makers
- role.py
- test_smtp_starttls_verifies_the_server_certificate
- .handle
- free_port.py
- 0004-plain-wiring-and-pluggable-backends.md
- ImageProcessor
- Code of Conduct
- Security model
- Deploy
- body_limit.py
- delete_file
- get_file_versions
- rbac
- [1.0.0] - 2026-10-10
- 0005: Scale-out file handling and cache resilience
- Documentation
- pull_request_template.md
- Security policy
- AccessLogMiddleware
- test_streamed_oversize_body_without_content_length_is_rejected
- fastapi-boilerplate
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
9. `StorageInterface` - 45 edges
10. `run()` - 42 edges

## Surprising Connections (you probably didn't know these)
- ``sessions` (`SessionsOps`)` --references--> `SessionsOps`  [INFERRED]
  docs/reference/data-model.md → app/services/data/sessions_ops.py
- ``users` (`UsersOps`)` --references--> `UsersOps`  [INFERRED]
  docs/reference/data-model.md → app/services/data/users_ops.py
- `Wiring` --references--> `Services`  [INFERRED]
  docs/ARCHITECTURE.md → app/services/registry.py
- `0004: Plain service wiring and pluggable backends` --references--> `build_services()`  [INFERRED]
  docs/adr/0004-plain-wiring-and-pluggable-backends.md → app/services/registry.py
- `Files (your own)` --references--> `chunk()`  [INFERRED]
  docs/reference/api.md → tests/test_files.py

## Import Cycles
- 3-file cycle: `app/services/file/__init__.py -> app/services/file/file_service.py -> app/services/file/spreadsheet_processor.py -> app/services/file/__init__.py`

## Communities (131 total, 70 thin omitted)

### Community 0 - "xlsx_package.py"
Cohesion: 0.12
Nodes (9): _add_sheet(), _delete_sheet(), _drop_calculation_state(), edit_xlsx(), _insert_before(), _Package, _parse_xml(), _sheet_parts() (+1 more)

### Community 2 - "e"
Cohesion: 0.10
Nodes (39): body(), body(), body(), infra(), body(), body(), body(), body() (+31 more)

### Community 3 - "DataService"
Cohesion: 0.06
Nodes (15): Where things go, get_current_user_info(), update_my_profile(), get_session_details(), list_active_sessions(), _own_session(), _public_view(), revoke_all_sessions() (+7 more)

### Community 6 - "Config"
Cohesion: 0.05
Nodes (17): main(), reference_markdown(), Settings, Config, ConfigError, main(), test_config_behaves_like_a_mapping_and_rejects_unknown_attributes(), test_configured_secret_is_left_alone() (+9 more)

### Community 7 - "test_files.py"
Cohesion: 0.11
Nodes (38): blue_png(), chunk(), create_sheet(), png_bytes(), signed_in(), test_a_second_user_cannot_inject_into_or_finish_anothers_upload(), test_abandoned_chunked_uploads_are_purged_once_older_than_the_session_lifetime(), test_active_content_types_are_rejected() (+30 more)

### Community 8 - "permissions.py"
Cohesion: 0.08
Nodes (16): get_auth_service(), get_data_service(), get_file_service(), get_oauth_service(), get_rbac_service(), get_services(), ChangePasswordRequest, LoginRequest (+8 more)

### Community 9 - "app.py"
Cohesion: 0.07
Nodes (11): AppFactory, create_app(), BodySizeLimitMiddleware, ErrorHandlerMiddleware, RateLimiter, RequestIDMiddleware, SecurityHeadersMiddleware, SessionMiddleware (+3 more)

### Community 10 - "spreadsheet.py"
Cohesion: 0.10
Nodes (15): _bad_request(), create_spreadsheet_file(), delete_sheet(), get_spreadsheet_info(), _info(), _owned_spreadsheet(), _processor(), read_spreadsheet() (+7 more)

### Community 11 - "change_password"
Cohesion: 0.10
Nodes (4): change_password(), confirm_password_reset(), request_password_reset(), delete_user()

### Community 13 - "upload.py"
Cohesion: 0.09
Nodes (13): list_files(), upload_new_version(), complete_chunked_upload(), _parse_metadata(), _parse_tags(), _read_limited(), upload_chunk(), upload_file() (+5 more)

### Community 14 - "SpreadsheetProcessor"
Cohesion: 0.10
Nodes (5): neutralize(), SpreadsheetProcessor, with_headers(), validate_sheet_name(), test_parsing_stops_at_the_cell_limit()

### Community 16 - "FileService"
Cohesion: 0.09
Nodes (4): update_file(), FileResponse, FileService, iter_bytes()

### Community 18 - "test_middleware.py"
Cohesion: 0.24
Nodes (5): build(), stream(), test_escaping_exceptions_become_generic_problem_500s(), test_slow_requests_get_a_504(), test_streaming_responses_pass_through_intact()

### Community 19 - "Logger"
Cohesion: 0.10
Nodes (4): Logger, _send_blocking(), send_email(), send_password_reset_email()

### Community 20 - "test_data_layer.py"
Cohesion: 0.11
Nodes (16): file_record(), make_user(), test_assignments_validate_against_definitions_and_take_effect_at_once(), test_changing_email_drops_the_old_email_lookup(), test_create_user_keeps_its_own_id(), test_deleted_file_leaves_the_listing_and_all_versions_are_flagged(), test_deleted_user_is_not_served_from_cache(), test_find_many_does_not_write_list_results_to_cache() (+8 more)

### Community 21 - "StorageInterface"
Cohesion: 0.06
Nodes (14): What this is, CacheInterface, DatabaseInterface, StorageInterface, create_storage(), Ways to help, Bring your own backend, Layers (+6 more)

### Community 22 - "S3Storage"
Cohesion: 0.17
Nodes (4): _is_missing(), S3Storage, collect(), send_part()

### Community 23 - "UsersOps"
Cohesion: 0.11
Nodes (3): normalize_user(), UsersOps, test_legacy_user_fields_are_normalised()

### Community 25 - "run"
Cohesion: 0.14
Nodes (20): run(), chunked(), collect(), collect_from(), failing_after(), _pieces(), test_a_failing_stream_leaves_nothing_behind(), test_open_stream_of_a_missing_file_is_none() (+12 more)

### Community 26 - "test_auth_flow.py"
Cohesion: 0.21
Nodes (20): bearer(), login(), make_admin(), register(), test_access_token_cannot_be_used_as_a_refresh_token(), test_cookie_and_bearer_both_authenticate(), test_duplicate_email_is_rejected(), test_every_login_attempt_is_recorded_in_the_audit_log() (+12 more)

### Community 27 - "RBACMiddleware"
Cohesion: 0.11
Nodes (3): RBACMiddleware, AppExceptionError, UserFacingExceptionError

### Community 28 - ".refresh_tokens"
Cohesion: 0.05
Nodes (13): login(), logout(), logout_all_devices(), refresh_tokens(), TokenPair, TokenManager, CookieManager, default_cookie_secure() (+5 more)

### Community 30 - "TokenPayload"
Cohesion: 0.06
Nodes (23): assign_group(), assign_role(), create_temporary_permission(), get_user_permissions(), list_groups(), list_permissions(), list_roles(), _not_found() (+15 more)

### Community 31 - "test_security_fixes.py"
Cohesion: 0.16
Nodes (14): bearer(), make_user(), test_a_file_cannot_collect_unbounded_versions(), test_bearer_requests_are_not_subject_to_the_origin_check(), test_chunks_much_larger_than_the_declared_average_are_refused(), test_cookie_authenticated_writes_from_foreign_origins_are_refused(), test_downloads_are_not_cacheable_by_shared_caches(), test_manager_cannot_suspend_an_administrator_but_can_suspend_a_user() (+6 more)

### Community 33 - "xlsx_patch.py"
Cohesion: 0.13
Nodes (10): _cell_xml(), column_index(), column_letters(), _parse_rows(), patch_sheet_xml(), reject_unsafe_markup(), _replace_cell(), UnsupportedWorkbookError (+2 more)

### Community 34 - "AuthService"
Cohesion: 0.05
Nodes (16): register(), LoginResponse, DeviceInfo, User, UserCreate, UserInDB, UserListResponse, UserPublic (+8 more)

### Community 35 - "health.py"
Cohesion: 0.21
Nodes (6): health_check(), liveness_check(), metrics_endpoint(), _now(), readiness_check(), startup_check()

### Community 37 - "test_route_access.py"
Cohesion: 0.13
Nodes (9): _compile_patterns(), path_matches(), permissions_of(), required_permissions(), test_every_authenticated_api_route_is_grantable_to_a_normal_user(), test_public_paths_match_whole_segments(), test_sensitive_surfaces_are_admin_only(), test_staff_only_permissions_are_held_by_managers_but_not_users() (+1 more)

### Community 38 - "OAuthProvider"
Cohesion: 0.05
Nodes (15): authorize_oauth(), link_oauth_account(), oauth_callback(), _state_cookie_name(), unlink_oauth_account(), OAuthAccount, OAuthProvider, OAuthToken (+7 more)

### Community 40 - "registry.py"
Cohesion: 0.11
Nodes (9): BaseService, ErrorService, MetricsService, build_services(), Services, SentryService, TracingService, Observability (optional, off by default) (+1 more)

### Community 41 - "FakeDatabase"
Cohesion: 0.06
Nodes (24): Commands, Navigate with the code graph, not by reading everything, Rule zero: the standards are a gate, Rules that are checked in review, Code of Conduct, Commits, Contributing, Documentation (+16 more)

### Community 44 - "download.py"
Cohesion: 0.14
Nodes (6): content_disposition(), not_found(), serve_stored_file(), download_file(), download_thumbnail(), get_file_metadata()

### Community 45 - "test_xlsx_patch.py"
Cohesion: 0.25
Nodes (11): media_and_charts(), names(), test_calc_chain_is_dropped_and_recalculation_requested(), test_cell_edit_keeps_charts_images_formulas_styles_and_other_sheets(), test_deleting_a_sheet_removes_only_that_sheet(), test_documents_with_a_dtd_are_refused(), test_new_sheet_is_added_and_the_package_stays_loadable(), test_overwriting_a_cell_keeps_its_style_and_clearing_keeps_the_cell() (+3 more)

### Community 46 - "cache/__init__.py"
Cohesion: 0.13
Nodes (3): create_cache(), load_backend_class(), create_database()

### Community 50 - "test_operations.py"
Cohesion: 0.15
Nodes (9): build_test_app(), cors_client(), metrics_env(), test_cors_preflight_is_answered_without_credentials(), test_probes_are_public_and_never_500(), test_rate_limit_answers_429_with_retry_after_and_is_per_client_tier(), test_security_headers_and_cors_are_present_even_on_rejections(), test_two_apps_in_one_process_do_not_collide_on_metric_names() (+1 more)

### Community 51 - "Collections"
Cohesion: 0.27
Nodes (10): Collections, `files` (`FilesOps`), `login_attempts`, `oauth_accounts` (`OAuthOps`), `password_reset_tokens`, `schema_migrations`, `sessions` (`SessionsOps`), `users` (`UsersOps`) (+2 more)

### Community 52 - "Endpoints"
Cohesion: 0.12
Nodes (16): Access control (administrators), API reference, Authentication, Authentication, Conventions, Endpoints, Errors, Files (your own) (+8 more)

### Community 54 - "Any"
Cohesion: 0.12
Nodes (3): _convert_datetime_strings(), _default_cache_key(), _normalize_record()

### Community 55 - "Engineering standards"
Cohesion: 0.06
Nodes (28): expand(), Access control, Architecture, Authentication model, Files, Known limits, Resilience, Wiring (+20 more)

### Community 57 - "MemoryCache"
Cohesion: 0.16
Nodes (3): MemoryCache, test_memory_cache_expiry_and_prefix_delete(), test_memory_cache_rate_limit_windows()

### Community 62 - "test_features.py"
Cohesion: 0.25
Nodes (14): admin_client(), signed_in(), test_admins_cannot_disable_themselves_and_unknown_users_404(), test_change_password_needs_the_current_one_and_ends_other_sessions(), test_failed_requests_are_not_stored_so_a_retry_really_retries(), test_keys_are_scoped_per_user_and_validated(), test_large_json_bodies_are_streamed_through_not_buffered(), test_normal_users_cannot_list_users_but_admins_can_with_paging() (+6 more)

### Community 63 - ".__call__"
Cohesion: 0.11
Nodes (8): counting_receive(), tracking_send(), capture_send(), tracking_send(), test_a_stalled_request_body_is_cut_off(), app(), receive(), send()

### Community 64 - "IdempotencyMiddleware"
Cohesion: 0.19
Nodes (3): IdempotencyMiddleware, respond(), _problem()

### Community 65 - "DatabaseService"
Cohesion: 0.18
Nodes (4): _drop_superseded_indexes(), _flag_latest_file_versions(), Migration, DatabaseService

### Community 72 - "Configuration reference"
Cohesion: 0.17
Nodes (12): Access control and OAuth, Application, Authentication, Cache, Configuration reference, Database, Email, Files (+4 more)

### Community 73 - "test_cache_degradation.py"
Cohesion: 0.10
Nodes (8): cache(), DownBackend, test_after_one_failure_the_backend_is_left_alone_until_the_cooldown_ends(), test_app_still_serves_authenticated_requests_with_the_cache_down(), test_operations_without_a_fallback_say_so(), test_reads_become_misses_and_writes_are_skipped(), client(), test_callback_rejects_missing_or_mismatched_state()

### Community 74 - "_ConsoleFormatter"
Cohesion: 0.22
Nodes (5): _ConsoleFormatter, _JsonFormatter, _one_line(), _RequestIdFilter, test_console_log_lines_cannot_be_forged_by_request_text()

### Community 75 - "Operations runbook"
Cohesion: 0.18
Nodes (11): 503 "Server overloaded" or 504 timeouts, A user is locked out, An account or token may be compromised, Disk filling up, Everyone gets 429 Too Many Requests, MongoDB is down or refuses credentials, Operations runbook, Redis is down (+3 more)

### Community 76 - "FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter"
Cohesion: 0.22
Nodes (9): Contributing, Documentation, FAQ, FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter, License, Project structure, Quick start, Tech stack (+1 more)

### Community 79 - "utils.py"
Cohesion: 0.18
Nodes (7): ensure_bootstrap_admin(), lifespan(), purge_abandoned_uploads_forever(), make_auth_service(), test_bootstrap_admin_created_only_when_configured_and_empty(), test_bootstrap_admin_skipped_when_users_exist(), test_no_default_admin_without_explicit_config()

### Community 80 - "Configure common features"
Cohesion: 0.20
Nodes (10): Change roles, groups and limits, Configure common features, Let a browser front end call the API, Run behind a reverse proxy, Send password-reset email, Sign in with Google, Store files in S3 (or MinIO, R2, ...), Turn on observability (+2 more)

### Community 81 - "Getting started"
Cohesion: 0.20
Nodes (10): 1. Set up, 2. Start the databases, 3. Create the first administrator, 4. Run the API, 5. Register and sign in, 6. Upload and list a file, 7. See access control at work, 8. Explore and test (+2 more)

### Community 84 - ".__init__"
Cohesion: 0.14
Nodes (10): Conventions, Rules worth knowing, 1. Model: `app/models/part.py`, 2. Data: `app/services/data/parts_ops.py`, 5. Permissions: `config.toml`, 6. Test it through the real app, Add a resource, Data model (+2 more)

### Community 88 - "For decision makers"
Cohesion: 0.25
Nodes (8): Decisions to make before building on it, For decision makers, How it helps the business, Scope: what it leaves to you, What it costs to run, What you can build with it, What you get on day one, Why it can be trusted

### Community 97 - "Code of Conduct"
Cohesion: 0.33
Nodes (5): Code of Conduct, Expected behaviour, Our pledge, Scope and enforcement, Unacceptable behaviour

### Community 98 - "Security model"
Cohesion: 0.33
Nodes (6): Browser defences, Google sign-in, Not covered, Security model, Sessions and tokens, Sign-in protection

### Community 99 - "Deploy"
Cohesion: 0.33
Nodes (6): Build the image, Deploy, Probes, Production checklist, Start-up sequence, Try the whole stack locally

### Community 104 - "[1.0.0] - 2026-10-10"
Cohesion: 0.33
Nodes (6): [1.0.0] - 2026-10-10, Added, Added, Changelog, [Unreleased], Upgrading from 0.x

### Community 116 - "Documentation"
Cohesion: 0.50
Nodes (4): Diagrams, Documentation, Every document, Start here, by role

### Community 117 - "pull_request_template.md"
Cohesion: 0.40
Nodes (4): AI assistance, Checklist, How it was tested, What and why

### Community 119 - "Security policy"
Cohesion: 0.50
Nodes (4): Reporting a vulnerability, Scope, Security policy, Supported versions

## Knowledge Gaps
- **128 isolated node(s):** `fastapi-boilerplate`, `What and why`, `How it was tested`, `Checklist`, `AI assistance` (+123 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1007 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **70 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Config` to `DataService`, `typing`, `permissions.py`, `app.py`, `LocalStorage`, `SpreadsheetProcessor`, `middleware/base.py`, `FileService`, `test_middleware.py`, `Logger`, `StorageInterface`, `S3Storage`, `ChunkedUploadHandler`, `.refresh_tokens`, `data_service.py`, `TokenPayload`, `AuthService`, `sentry.py`, `test_route_access.py`, `OAuthProvider`, `registry.py`, `BaseMiddleware`, `cache/__init__.py`, `CacheService`, `interface.py`, `test_operations.py`, `error_service.py`, `DatabaseService`, `tracing.py`, `.format_error`, `_ConsoleFormatter`, `utils.py`, `Any`, `.__init__`, `ImageProcessor`?**
  _High betweenness centrality (0.215) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `Config` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Config` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fastapi-boilerplate`, `What and why`, `How it was tested` to the rest of the system?**
  _128 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `xlsx_package.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1225071225071225 - nodes in this community are weakly interconnected._
- **Why does `Logger` connect `Logger` to `DataService`, `typing`, `Config`, `permissions.py`, `app.py`, `LocalStorage`, `SpreadsheetProcessor`, `middleware/base.py`, `FileService`, `StorageInterface`, `S3Storage`, `ChunkedUploadHandler`, `.refresh_tokens`, `data_service.py`, `TokenPayload`, `AuthService`, `sentry.py`, `OAuthProvider`, `registry.py`, `BaseMiddleware`, `cache/__init__.py`, `CacheService`, `interface.py`, `error_service.py`, `DatabaseService`, `tracing.py`, `.format_error`, `_ConsoleFormatter`, `utils.py`, `Any`, `.__init__`, `run_migrations`, `ImageProcessor`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `Logger` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Logger` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Should `e` be split into smaller, more focused modules?**
  _Cohesion score 0.1039426523297491 - nodes in this community are weakly interconnected._