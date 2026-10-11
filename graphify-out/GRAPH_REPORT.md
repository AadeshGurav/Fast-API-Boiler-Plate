# Graph Report - Fast-API-Boiler-Plate  (2026-10-11)

## Corpus Check
- 204 files · ~177,085 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 7, .example 2, .toml 1)

## Summary
- 2845 nodes · 6862 edges · 147 communities (87 shown, 60 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 755 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6c0a6b46`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- xlsx_package.py
- StorageInterface
- e
- auth.py
- config.py
- MongoDB
- test_jwt_secret.py
- test_files.py
- permissions.py
- app.py
- update_spreadsheet
- get_session_details
- LocalStorage
- TokenPayload
- SpreadsheetProcessor
- middleware/base.py
- FileService
- MFAService
- test_middleware.py
- mailer.py
- test_data_layer.py
- tests/conftest.py
- S3Storage
- UsersOps
- ChunkedUploadHandler
- run
- test_auth_flow.py
- middleware/rbac.py
- CookieManager
- typing
- require_any_role
- test_security_fixes.py
- README.md
- xlsx_patch.py
- AuthService
- Services
- PostgresDatabase
- test_route_access.py
- OAuthProvider
- registry.py
- FakeDatabase
- BaseMiddleware
- JobService
- not_found
- test_xlsx_patch.py
- pytest
- SessionsOps
- Config
- ods.py
- test_operations.py
- routes/auth/mfa.py
- Operations runbook
- .refresh_tokens
- spreadsheet.py
- Engineering standards
- SecurityHeadersMiddleware
- MemoryCache
- RedisCache
- test_jobs.py
- signed_in
- .__call__
- IdempotencyMiddleware
- Any
- OAuthBase
- asyncio
- routes/tokens.py
- ErrorHandlerMiddleware
- .format_error
- Configuration reference
- contract/conftest.py
- _ConsoleFormatter
- test_mfa.py
- FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter
- CSRFOriginMiddleware
- utils.py
- Configure common features
- Getting started
- totp.py
- Add a resource
- test_api_tokens.py
- RBACService
- MeteredStream
- For decision makers
- 3. Recommendations
- role.py
- ._authorize
- .handle
- free_port.py
- routes/rbac.py
- 0007-background-jobs-on-the-database.md
- ._encode
- Code of Conduct
- Security model
- Deploy
- body_limit.py
- delete_file
- get_file_versions
- assign_group
- [Unreleased]
- Any
- For designers
- models/oauth.py
- Contributing
- Architecture
- Competitive analysis and roadmap proposal (October 2026)
- .record
- ApiTokenError
- .allows
- 0005: Scale-out file handling and cache resilience
- Documentation
- pull_request_template.md
- A database backend
- Security policy
- ensure_bootstrap_admin
- RBACMiddleware
- test_streamed_oversize_body_without_content_length_is_rejected
- fastapi-boilerplate
- create_temporary_permission
- Generate a typed client
- limited_client
- Clock
- _compile_patterns
- UserRole
- test_two_workers_never_run_the_same_job

## God Nodes (most connected - your core abstractions)
1. `Config` - 164 edges
2. `Logger` - 120 edges
3. `TokenPayload` - 88 edges
4. `AuthService` - 86 edges
5. `DataService` - 80 edges
6. `e()` - 60 edges
7. `FileService` - 58 edges
8. `run()` - 58 edges
9. `RBACService` - 50 edges
10. `signed_in()` - 50 edges

## Surprising Connections (you probably didn't know these)
- `The methods` --references--> `DuplicateRecordError`  [INFERRED]
  docs/how-to/write-a-backend.md → app/core/interfaces/database_interface.py
- `0006: PostgreSQL ships as a JSONB document backend` --references--> `DatabaseInterface`  [INFERRED]
  docs/adr/0006-postgresql-as-jsonb-documents.md → app/core/interfaces/database_interface.py
- `P1-1. PostgreSQL backend (built in, optional)` --references--> `DatabaseInterface`  [INFERRED]
  docs/proposals/2026-10-competitive-analysis.md → app/core/interfaces/database_interface.py
- `P2-2. Generic OpenID Connect provider` --references--> `OAuthProvider`  [INFERRED]
  docs/proposals/2026-10-competitive-analysis.md → app/models/oauth.py
- ``audit_events` (`AuditService`)` --references--> `AuditService`  [INFERRED]
  docs/reference/data-model.md → app/services/audit.py

## Import Cycles
- 3-file cycle: `app/services/file/__init__.py -> app/services/file/file_service.py -> app/services/file/spreadsheet_processor.py -> app/services/file/__init__.py`

## Communities (147 total, 60 thin omitted)

### Community 0 - "xlsx_package.py"
Cohesion: 0.15
Nodes (7): _add_sheet(), _delete_sheet(), _drop_calculation_state(), edit_xlsx(), _Package, _parse_xml(), _sheet_parts()

### Community 1 - "StorageInterface"
Cohesion: 0.03
Nodes (15): What this is, CacheInterface, CacheUnavailableError, RateDecision, DatabaseInterface, StorageInterface, CacheService, Ways to help (+7 more)

### Community 2 - "e"
Cohesion: 0.07
Nodes (48): body(), body(), body(), infra(), body(), body(), body(), body() (+40 more)

### Community 3 - "auth.py"
Cohesion: 0.06
Nodes (20): register(), get_current_user_info(), update_my_profile(), get_user(), list_users(), _public(), set_user_status(), ChangePasswordRequest (+12 more)

### Community 4 - "config.py"
Cohesion: 0.08
Nodes (5): BaseService, ImageProcessor, iter_bytes(), _JsonFormatter, _RequestIdFilter

### Community 6 - "test_jwt_secret.py"
Cohesion: 0.09
Nodes (16): reference_markdown(), ConfigError, main(), test_config_behaves_like_a_mapping_and_rejects_unknown_attributes(), test_configured_secret_is_left_alone(), test_debug_dependent_defaults(), test_generated_reference_is_current(), test_layers_override_in_documented_order() (+8 more)

### Community 7 - "test_files.py"
Cohesion: 0.11
Nodes (38): blue_png(), chunk(), create_sheet(), png_bytes(), signed_in(), test_a_second_user_cannot_inject_into_or_finish_anothers_upload(), test_abandoned_chunked_uploads_are_purged_once_older_than_the_session_lifetime(), test_active_content_types_are_rejected() (+30 more)

### Community 8 - "permissions.py"
Cohesion: 0.12
Nodes (11): get_audit_service(), get_auth_service(), get_data_service(), get_file_service(), get_job_service(), get_oauth_service(), get_rbac_service(), get_services() (+3 more)

### Community 9 - "app.py"
Cohesion: 0.08
Nodes (9): AppFactory, create_app(), AccessLogMiddleware, BodySizeLimitMiddleware, RateLimiter, RequestIDMiddleware, SessionMiddleware, The request pipeline (+1 more)

### Community 10 - "update_spreadsheet"
Cohesion: 0.13
Nodes (9): _bad_request(), create_spreadsheet_file(), delete_sheet(), get_spreadsheet_info(), _info(), _owned_spreadsheet(), _processor(), read_spreadsheet() (+1 more)

### Community 11 - "get_session_details"
Cohesion: 0.11
Nodes (6): get_session_details(), list_active_sessions(), _own_session(), _public_view(), revoke_all_sessions(), revoke_session()

### Community 13 - "TokenPayload"
Cohesion: 0.09
Nodes (8): list_files(), upload_new_version(), _parse_metadata(), _parse_tags(), _read_limited(), upload_chunk(), TokenPayload, iter_upload()

### Community 14 - "SpreadsheetProcessor"
Cohesion: 0.11
Nodes (5): neutralize(), SpreadsheetProcessor, with_headers(), validate_sheet_name(), test_parsing_stops_at_the_cell_limit()

### Community 15 - "middleware/base.py"
Cohesion: 0.11
Nodes (3): add_timing(), set_headers(), ErrorService

### Community 16 - "FileService"
Cohesion: 0.10
Nodes (4): complete_chunked_upload(), upload_file(), FileResponse, FileService

### Community 17 - "MFAService"
Cohesion: 0.05
Nodes (23): MFAError, MFAService, MFAStateError, _new_recovery_codes(), _normalize_recovery_code(), provisioning_uri(), TemporaryPermissionsOps, `api_tokens` (`ApiTokenManager`) (+15 more)

### Community 18 - "test_middleware.py"
Cohesion: 0.10
Nodes (7): TimeoutMiddleware, tracking_send(), build(), stream(), test_escaping_exceptions_become_generic_problem_500s(), test_slow_requests_get_a_504(), test_streaming_responses_pass_through_intact()

### Community 19 - "mailer.py"
Cohesion: 0.08
Nodes (12): _send_blocking(), send_email(), send_password_reset_email(), register_job_handlers(), send_email_job(), Background jobs, 1. Register a handler, 2. Enqueue from a service (+4 more)

### Community 20 - "test_data_layer.py"
Cohesion: 0.10
Nodes (16): file_record(), make_user(), rbac(), test_assignments_validate_against_definitions_and_take_effect_at_once(), test_changing_email_drops_the_old_email_lookup(), test_create_user_keeps_its_own_id(), test_deleted_file_leaves_the_listing_and_all_versions_are_flagged(), test_deleted_user_is_not_served_from_cache() (+8 more)

### Community 21 - "tests/conftest.py"
Cohesion: 0.06
Nodes (6): create_database(), _drop_superseded_indexes(), Migration, run_migrations(), DatabaseService, data_service()

### Community 22 - "S3Storage"
Cohesion: 0.17
Nodes (4): _is_missing(), S3Storage, collect(), send_part()

### Community 23 - "UsersOps"
Cohesion: 0.11
Nodes (3): normalize_user(), UsersOps, test_legacy_user_fields_are_normalised()

### Community 24 - "ChunkedUploadHandler"
Cohesion: 0.12
Nodes (3): ChunkedUploadHandler, pieces(), UploadSizeMismatchError

### Community 25 - "run"
Cohesion: 0.13
Nodes (23): run(), test_after_one_failure_the_backend_is_left_alone_until_the_cooldown_ends(), test_operations_without_a_fallback_say_so(), test_reads_become_misses_and_writes_are_skipped(), test_chunks_much_larger_than_the_declared_average_are_refused(), chunked(), collect(), collect_from() (+15 more)

### Community 26 - "test_auth_flow.py"
Cohesion: 0.13
Nodes (24): test_accounts_two_factor_files_audit_and_jobs(), bearer(), login(), make_admin(), register(), test_access_token_cannot_be_used_as_a_refresh_token(), test_cookie_and_bearer_both_authenticate(), test_duplicate_email_is_rejected() (+16 more)

### Community 28 - "CookieManager"
Cohesion: 0.09
Nodes (11): login(), logout(), logout_all_devices(), refresh_tokens(), login_with_mfa_code(), CookieManager, default_cookie_secure(), get_token_cookie_names() (+3 more)

### Community 29 - "typing"
Cohesion: 0.06
Nodes (5): FilesOps, OAuthOps, CachePolicy, set_request_id(), main()

### Community 30 - "require_any_role"
Cohesion: 0.14
Nodes (11): _forbidden(), get_session_user(), _log_denied(), require_admin(), require_any_permission(), dependency(), require_any_role(), dependency() (+3 more)

### Community 31 - "test_security_fixes.py"
Cohesion: 0.13
Nodes (14): Settings, bearer(), make_user(), test_a_file_cannot_collect_unbounded_versions(), test_bearer_requests_are_not_subject_to_the_origin_check(), test_cookie_authenticated_writes_from_foreign_origins_are_refused(), test_downloads_are_not_cacheable_by_shared_caches(), test_manager_cannot_suspend_an_administrator_but_can_suspend_a_user() (+6 more)

### Community 32 - "README.md"
Cohesion: 0.25
Nodes (3): 0001: Tokens are bound to a server-side session, 0002: The service is API-only, 0006: PostgreSQL ships as a JSONB document backend

### Community 33 - "xlsx_patch.py"
Cohesion: 0.11
Nodes (12): _insert_before(), _cell_xml(), column_index(), column_letters(), new_sheet_xml(), _parse_rows(), patch_sheet_xml(), reject_unsafe_markup() (+4 more)

### Community 34 - "AuthService"
Cohesion: 0.05
Nodes (11): change_password(), confirm_password_reset(), request_password_reset(), delete_user(), LoginResponse, DeviceInfo, User, UserInDB (+3 more)

### Community 35 - "Services"
Cohesion: 0.11
Nodes (12): build_schema(), render(), health_check(), liveness_check(), metrics_endpoint(), _now(), readiness_check(), startup_check() (+4 more)

### Community 36 - "PostgresDatabase"
Cohesion: 0.08
Nodes (21): PostgresDatabase, _compare(), decode(), _default(), dumps(), _encode_datetime(), _equals(), field() (+13 more)

### Community 37 - "test_route_access.py"
Cohesion: 0.15
Nodes (9): path_matches(), 5. Permissions: `config.toml`, permissions_of(), required_permissions(), test_every_authenticated_api_route_is_grantable_to_a_normal_user(), test_public_paths_match_whole_segments(), test_sensitive_surfaces_are_admin_only(), test_staff_only_permissions_are_held_by_managers_but_not_users() (+1 more)

### Community 38 - "OAuthProvider"
Cohesion: 0.12
Nodes (7): authorize_oauth(), link_oauth_account(), oauth_callback(), _state_cookie_name(), unlink_oauth_account(), OAuthProvider, OAuthService

### Community 40 - "registry.py"
Cohesion: 0.06
Nodes (13): Where things go, create_storage(), MetricsService, build_services(), sentry(), tracing(), SentryService, set_user() (+5 more)

### Community 43 - "JobService"
Cohesion: 0.06
Nodes (13): list_audit_events(), list_jobs(), reset_user_mfa(), retry_job(), AuditEvent, AuditEventListResponse, Job, JobListResponse (+5 more)

### Community 44 - "not_found"
Cohesion: 0.13
Nodes (7): content_disposition(), not_found(), serve_stored_file(), download_file(), download_thumbnail(), get_file_metadata(), update_file()

### Community 45 - "test_xlsx_patch.py"
Cohesion: 0.25
Nodes (11): media_and_charts(), names(), test_calc_chain_is_dropped_and_recalculation_requested(), test_cell_edit_keeps_charts_images_formulas_styles_and_other_sheets(), test_deleting_a_sheet_removes_only_that_sheet(), test_documents_with_a_dtd_are_refused(), test_new_sheet_is_added_and_the_package_stays_loadable(), test_overwriting_a_cell_keeps_its_style_and_clearing_keeps_the_cell() (+3 more)

### Community 46 - "pytest"
Cohesion: 0.11
Nodes (22): DuplicateRecordError, seed(), test_compound_unique_index_is_on_the_combination(), test_concurrent_increments_never_lose_or_repeat_a_value(), test_conditional_update_has_exactly_one_winner(), test_datetimes_come_back_timezone_aware_utc(), test_delete_removes_one_record_and_reports_it(), test_equality_on_a_list_field_means_contains() (+14 more)

### Community 48 - "Config"
Cohesion: 0.04
Nodes (12): create_cache(), AuditService, ApiTokenManager, _fernet(), TokenManager, UserManager, DataService, hash_token() (+4 more)

### Community 49 - "ods.py"
Cohesion: 0.12
Nodes (14): _cell(), read(), _read_table(), _repeat(), _too_big(), _value(), write(), Permissions (+6 more)

### Community 50 - "test_operations.py"
Cohesion: 0.15
Nodes (9): build_test_app(), cors_client(), metrics_env(), test_cors_preflight_is_answered_without_credentials(), test_probes_are_public_and_never_500(), test_rate_limit_answers_429_with_retry_after_and_is_per_client_tier(), test_security_headers_and_cors_are_present_even_on_rejections(), test_two_apps_in_one_process_do_not_collide_on_metric_names() (+1 more)

### Community 51 - "routes/auth/mfa.py"
Cohesion: 0.15
Nodes (13): confirm_totp_setup(), disable_totp(), get_mfa_status(), _refused(), regenerate_recovery_codes(), start_totp_setup(), MFACode, MFALoginRequest (+5 more)

### Community 52 - "Operations runbook"
Cohesion: 0.06
Nodes (31): 503 "Server overloaded" or 504 timeouts, A user is locked out, A user lost their authenticator phone, An account or token may be compromised, Background jobs are failing, Disk filling up, Everyone gets 429 Too Many Requests, MongoDB is down or refuses credentials (+23 more)

### Community 53 - ".refresh_tokens"
Cohesion: 0.10
Nodes (6): TokenPair, is_api_token(), authenticate_request(), extract_access_token(), _remember(), _silent_refresh()

### Community 54 - "spreadsheet.py"
Cohesion: 0.14
Nodes (9): ChunkUploadResponse, FileListResponse, FileMetadata, FileUpdateRequest, SpreadsheetCreateRequest, SpreadsheetData, SpreadsheetInfo, SpreadsheetReadResponse (+1 more)

### Community 55 - "Engineering standards"
Cohesion: 0.10
Nodes (18): Commands, Navigate with the code graph, not by reading everything, Rule zero: the standards are a gate, Rules that are checked in review, Tests, 10. Style, docs and commits, 11. Definition of done, 12. AI-written contributions (+10 more)

### Community 57 - "MemoryCache"
Cohesion: 0.16
Nodes (3): MemoryCache, test_memory_cache_expiry_and_prefix_delete(), test_memory_cache_rate_limit_windows()

### Community 59 - "test_jobs.py"
Cohesion: 0.13
Nodes (15): job(), make_due(), records(), test_a_handler_name_is_registered_once(), test_a_job_that_keeps_killing_its_worker_goes_dead(), test_a_job_without_a_handler_goes_dead_at_once(), test_a_queued_job_runs_once_and_is_marked_done(), test_administrators_see_dead_jobs_and_can_retry_them() (+7 more)

### Community 62 - "signed_in"
Cohesion: 0.14
Nodes (26): collection_indexes(), events(), test_a_failing_audit_write_does_not_block_the_change(), test_admin_changes_are_recorded_as_the_admin(), test_audit_events_expire_after_the_configured_retention(), test_filters_and_paging(), test_only_administrators_can_read_the_log(), test_password_change_is_recorded_with_actor_ip_and_request_id() (+18 more)

### Community 63 - ".__call__"
Cohesion: 0.18
Nodes (8): counting_receive(), tracking_send(), tracking_send(), capture_send(), test_a_stalled_request_body_is_cut_off(), app(), receive(), send()

### Community 64 - "IdempotencyMiddleware"
Cohesion: 0.19
Nodes (3): IdempotencyMiddleware, respond(), _problem()

### Community 66 - "OAuthBase"
Cohesion: 0.15
Nodes (5): OAuthAccount, OAuthUserInfo, OAuthBase, test_oauth_sign_in_does_not_inherit_a_pre_registered_unverified_account(), test_unlinked_provider_identity_cannot_sign_in()

### Community 67 - "asyncio"
Cohesion: 0.13
Nodes (4): main(), test_concurrent_adds_have_exactly_one_winner(), test_concurrent_hits_never_exceed_the_limit(), test_value_expires_after_its_ttl()

### Community 69 - "routes/tokens.py"
Cohesion: 0.18
Nodes (7): create_api_token(), list_api_tokens(), revoke_api_token(), ApiToken, ApiTokenCreate, ApiTokenCreated, ApiTokenListResponse

### Community 72 - "Configuration reference"
Cohesion: 0.15
Nodes (13): Access control and OAuth, Application, Authentication, Background jobs and audit, Cache, Configuration reference, Database, Email (+5 more)

### Community 73 - "contract/conftest.py"
Cohesion: 0.08
Nodes (10): load_backend_class(), cache(), _config(), database(), _drop(), _selected(), client(), test_providers_resolve_builtin_names_and_dotted_paths() (+2 more)

### Community 74 - "_ConsoleFormatter"
Cohesion: 0.25
Nodes (3): _ConsoleFormatter, _one_line(), test_console_log_lines_cannot_be_forged_by_request_text()

### Community 75 - "test_mfa.py"
Cohesion: 0.35
Nodes (16): challenge(), code(), enrol(), finish(), test_a_code_works_only_once(), test_an_administrator_can_reset_a_lost_second_factor(), test_an_expired_challenge_is_refused(), test_challenge_tokens_are_not_access_tokens_and_vice_versa() (+8 more)

### Community 76 - "FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter"
Cohesion: 0.22
Nodes (9): Contributing, Documentation, FAQ, FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter, License, Project structure, Quick start, Tech stack (+1 more)

### Community 80 - "Configure common features"
Cohesion: 0.18
Nodes (11): Change roles, groups and limits, Configure common features, Let a browser front end call the API, Run behind a reverse proxy, Send password-reset email, Sign in with Google, Store files in S3 (or MinIO, R2, ...), Turn on observability (+3 more)

### Community 81 - "Getting started"
Cohesion: 0.20
Nodes (10): 1. Set up, 2. Start the databases, 3. Create the first administrator, 4. Run the API, 5. Register and sign in, 6. Upload and list a file, 7. See access control at work, 8. Explore and test (+2 more)

### Community 82 - "totp.py"
Cohesion: 0.23
Nodes (6): code_at(), current_step(), generate_secret(), matching_step(), test_codes_match_the_rfc_6238_vectors(), test_one_step_of_clock_skew_is_accepted_and_two_are_not()

### Community 84 - "Add a resource"
Cohesion: 0.50
Nodes (4): 1. Model: `app/models/part.py`, 3. Rules: `app/services/part_service.py` (only if needed), 6. Test it through the real app, Add a resource

### Community 85 - "test_api_tokens.py"
Cohesion: 0.31
Nodes (13): as_token(), create(), stored(), test_a_token_never_exceeds_its_owner(), test_invalid_requests_are_refused_with_a_reason(), test_last_used_is_updated(), test_other_users_cannot_revoke_your_token(), test_revoked_expired_and_unknown_tokens_are_refused() (+5 more)

### Community 88 - "For decision makers"
Cohesion: 0.25
Nodes (8): Decisions to make before building on it, For decision makers, How it helps the business, Scope: what it leaves to you, What it costs to run, What you can build with it, What you get on day one, Why it can be trusted

### Community 89 - "3. Recommendations"
Cohesion: 0.14
Nodes (14): 3. Recommendations, P0-1. Pin `ruff` and add the hygiene CI jobs, P0-2. Remove pandas and numpy (use odfpy directly), P1-1. PostgreSQL backend (built in, optional), P1-3. MFA: TOTP plus recovery codes, P1-4. Personal access tokens / API keys, P1-5. Security audit log of changes, P1-6. OpenAPI snapshot plus a generated TypeScript client (+6 more)

### Community 94 - "routes/rbac.py"
Cohesion: 0.24
Nodes (5): get_user_permissions(), list_groups(), list_permissions(), list_roles(), require_permission()

### Community 97 - "Code of Conduct"
Cohesion: 0.33
Nodes (5): Code of Conduct, Expected behaviour, Our pledge, Scope and enforcement, Unacceptable behaviour

### Community 98 - "Security model"
Cohesion: 0.22
Nodes (9): API tokens, Audit trail, Browser defences, Google sign-in, Not covered, Security model, Sessions and tokens, Sign-in protection (+1 more)

### Community 99 - "Deploy"
Cohesion: 0.33
Nodes (6): Build the image, Deploy, Probes, Production checklist, Start-up sequence, Try the whole stack locally

### Community 103 - "assign_group"
Cohesion: 0.22
Nodes (5): assign_group(), assign_role(), _not_found(), remove_role(), revoke_temporary_permission()

### Community 104 - "[Unreleased]"
Cohesion: 0.22
Nodes (9): [1.0.0] - 2026-10-10, Added, Added, Changed, Changelog, Fixed, [Unreleased], Upgrading (+1 more)

### Community 105 - "Any"
Cohesion: 0.09
Nodes (6): _convert_datetime_strings(), _default_cache_key(), _normalize_record(), Layers, Rules worth knowing, 2. Data: `app/services/data/parts_ops.py`

### Community 106 - "For designers"
Cohesion: 0.18
Nodes (7): expand(), Copy rules from security, For designers, Patterns the API expects, Screens and the states they need, The account journey, Turning errors into states

### Community 108 - "Contributing"
Cohesion: 0.20
Nodes (10): Code of Conduct, Commits, Contributing, Conventions, Documentation, Find your way with the code graph, Pull request checklist, Releases (+2 more)

### Community 109 - "Architecture"
Cohesion: 0.22
Nodes (9): Architecture, Authentication model, Files, Known limits, Resilience, Wiring, P2-3. Move to uv with a lockfile; Python 3.12+, s3() (+1 more)

### Community 110 - "Competitive analysis and roadmap proposal (October 2026)"
Cohesion: 0.20
Nodes (9): 1. Who we compete with, 2. Gaps found in our own repository while checking, 4. What not to add, and why, 5. What to remove or reconsider, 6. Suggested order of work, 7. Decisions needed from the maintainer, Competitive analysis and roadmap proposal (October 2026), Progress (+1 more)

### Community 116 - "Documentation"
Cohesion: 0.50
Nodes (4): Diagrams, Documentation, Every document, Start here, by role

### Community 117 - "pull_request_template.md"
Cohesion: 0.40
Nodes (4): AI assistance, Checklist, How it was tested, What and why

### Community 118 - "A database backend"
Cohesion: 0.25
Nodes (6): A database backend, Index declarations, Prove it, The filter vocabulary, The methods, The record model

### Community 119 - "Security policy"
Cohesion: 0.50
Nodes (4): Reporting a vulnerability, Scope, Security policy, Supported versions

### Community 126 - "ensure_bootstrap_admin"
Cohesion: 0.47
Nodes (5): ensure_bootstrap_admin(), make_auth_service(), test_bootstrap_admin_created_only_when_configured_and_empty(), test_bootstrap_admin_skipped_when_users_exist(), test_no_default_admin_without_explicit_config()

### Community 135 - "Generate a typed client"
Cohesion: 0.40
Nodes (5): Calling the API from a browser, Generate a typed client, Other languages, TypeScript (web and React Native), When you change the API

### Community 136 - "limited_client"
Cohesion: 0.50
Nodes (3): limited_client(), size(), small_chunks()

## Knowledge Gaps
- **152 isolated node(s):** `fastapi-boilerplate`, `What and why`, `How it was tested`, `Checklist`, `AI assistance` (+147 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1192 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Config` to `StorageInterface`, `config.py`, `test_jwt_secret.py`, `permissions.py`, `app.py`, `LocalStorage`, `SpreadsheetProcessor`, `middleware/base.py`, `FileService`, `MFAService`, `test_middleware.py`, `mailer.py`, `tests/conftest.py`, `S3Storage`, `ChunkedUploadHandler`, `CookieManager`, `typing`, `test_security_fixes.py`, `AuthService`, `Services`, `test_route_access.py`, `OAuthProvider`, `registry.py`, `BaseMiddleware`, `JobService`, `test_operations.py`, `OAuthBase`, `asyncio`, `contract/conftest.py`, `.reload`, `RBACService`, `Any`, `ensure_bootstrap_admin`?**
  _High betweenness centrality (0.204) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `Config` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Config` has 47 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fastapi-boilerplate`, `What and why`, `How it was tested` to the rest of the system?**
  _152 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `xlsx_package.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14624505928853754 - nodes in this community are weakly interconnected._
- **Why does `Logger` connect `Config` to `StorageInterface`, `config.py`, `app.py`, `LocalStorage`, `SpreadsheetProcessor`, `middleware/base.py`, `FileService`, `MFAService`, `mailer.py`, `tests/conftest.py`, `S3Storage`, `ChunkedUploadHandler`, `typing`, `AuthService`, `Services`, `OAuthProvider`, `registry.py`, `BaseMiddleware`, `JobService`, `OAuthBase`, `RBACService`, `Any`, `models/oauth.py`, `ensure_bootstrap_admin`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `Logger` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Logger` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Should `StorageInterface` be split into smaller, more focused modules?**
  _Cohesion score 0.030427819720887667 - nodes in this community are weakly interconnected._