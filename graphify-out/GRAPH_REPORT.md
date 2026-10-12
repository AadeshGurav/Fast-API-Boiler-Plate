# Graph Report - wt  (2026-10-12)

## Corpus Check
- 218 files · ~216,678 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 8, .example 2, .toml 1)

## Summary
- 3061 nodes · 7539 edges · 170 communities (96 shown, 74 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 813 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c4160f7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- xlsx_package.py
- test_passkeys.py
- e
- routes/users.py
- config.py
- MongoDB
- Config
- test_files.py
- permissions.py
- app.py
- spreadsheet.py
- routes/auth/passkeys.py
- LocalStorage
- upload.py
- SpreadsheetProcessor
- BaseMiddleware
- FileService
- MFAService
- ErrorHandlerMiddleware
- test_webhooks.py
- test_data_layer.py
- tests/conftest.py
- S3Storage
- UsersOps
- .get_upload_info
- run
- test_auth_flow.py
- middleware/rbac.py
- routes/oauth.py
- DataService
- get_session_details
- test_security_fixes.py
- docs/README.md
- xlsx_patch.py
- DeviceInfo
- test_jobs.py
- PostgresDatabase
- test_route_access.py
- base64
- registry.py
- FakeDatabase
- JobService
- download.py
- test_xlsx_patch.py
- pytest
- SessionsOps
- Logger
- ods.py
- build_test_app
- routes/auth/mfa.py
- RedisCache
- TokenPayload
- OIDCClient
- Engineering standards
- SecurityHeadersMiddleware
- MemoryCache
- test_oidc.py
- WebhookService
- PasswordService
- CacheUnavailableError
- BodySizeLimitMiddleware
- IdempotencyMiddleware
- AuthService
- OAuthService
- test_cache_contract.py
- routes/tokens.py
- PasskeyManager
- .format_error
- Configuration reference
- Any
- _ConsoleFormatter
- signed_in
- FastAPI Foundation: the production-grade chassis for serious FastAPI back ends
- CSRFOriginMiddleware
- RateLimiter
- test_mfa.py
- Configure common features
- Getting started
- CacheInterface
- create_webhook
- test_cache_degradation.py
- normalize_user
- RBACService
- MeteredStream
- For decision makers
- _flag_latest_file_versions
- role.py
- Endpoints
- asyncio
- free_port.py
- routes/rbac.py
- run-background-jobs.md
- ._encode
- Code of Conduct
- Security model
- Deploy
- RateDecision
- delete_file
- manage.py
- remove_role
- Changed
- .update
- For designers
- utils.py
- Contributing
- test_middleware.py
- Architecture
- _default_cache_key
- test_api_tokens.py
- Documentation
- pull_request_template.md
- Collections
- Security policy
- ensure_bootstrap_admin
- admin.py
- TemporaryPermissionsOps
- fastapi-boilerplate
- assign_group
- retry_job
- generate-a-client.md
- AGENTS.md
- AccessLogMiddleware
- create_app
- Add a resource
- DatabaseInterface
- oauth/__init__.py
- test_smtp_starttls_verifies_the_server_certificate
- remove_webhook
- Send webhooks to other systems
- .resolve_user_permissions
- A database backend
- Conventions
- Clock
- 0005: Scale-out file handling and cache resilience
- test_two_workers_never_run_the_same_job
- 0001-session-bound-tokens.md
- test_traversal_is_refused

## God Nodes (most connected - your core abstractions)
1. `Config` - 167 edges
2. `Logger` - 117 edges
3. `TokenPayload` - 96 edges
4. `AuthService` - 95 edges
5. `DataService` - 83 edges
6. `e()` - 70 edges
7. `run()` - 68 edges
8. `signed_in()` - 60 edges
9. `FileService` - 58 edges
10. `RBACService` - 50 edges

## Surprising Connections (you probably didn't know these)
- `The methods` --references--> `DuplicateRecordError`  [INFERRED]
  docs/how-to/write-a-backend.md → app/core/interfaces/database_interface.py
- ``audit_events` (`AuditService`)` --references--> `AuditService`  [INFERRED]
  docs/reference/data-model.md → app/services/audit.py
- ``sessions` (`SessionsOps`)` --references--> `SessionsOps`  [INFERRED]
  docs/reference/data-model.md → app/services/data/sessions_ops.py
- `Permissions` --references--> `write()`  [INFERRED]
  docs/reference/api.md → app/services/file/ods.py
- `Wiring` --references--> `Services`  [INFERRED]
  docs/ARCHITECTURE.md → app/services/registry.py

## Import Cycles
- 3-file cycle: `app/services/file/__init__.py -> app/services/file/file_service.py -> app/services/file/spreadsheet_processor.py -> app/services/file/__init__.py`

## Communities (170 total, 74 thin omitted)

### Community 0 - "xlsx_package.py"
Cohesion: 0.15
Nodes (7): _add_sheet(), _delete_sheet(), _drop_calculation_state(), edit_xlsx(), _Package, _parse_xml(), _sheet_parts()

### Community 1 - "test_passkeys.py"
Cohesion: 0.19
Nodes (14): b64(), enrol(), sign_in(), signed_in(), SoftAuthenticator, test_a_cloned_authenticator_is_caught_by_its_signature_counter(), test_a_passkey_from_another_site_or_origin_is_refused(), test_api_tokens_cannot_manage_passkeys() (+6 more)

### Community 2 - "e"
Cohesion: 0.09
Nodes (50): body(), body(), body(), infra(), body(), body(), body(), body() (+42 more)

### Community 3 - "routes/users.py"
Cohesion: 0.10
Nodes (12): get_current_user_info(), update_my_profile(), get_user(), list_users(), _public(), set_user_status(), UserListResponse, UserPublic (+4 more)

### Community 4 - "config.py"
Cohesion: 0.04
Nodes (5): StorageInterface, BaseService, CacheService, ChunkedUploadHandler, ImageProcessor

### Community 6 - "Config"
Cohesion: 0.06
Nodes (19): main(), reference_markdown(), Settings, Config, ConfigError, main(), test_config_behaves_like_a_mapping_and_rejects_unknown_attributes(), test_configured_secret_is_left_alone() (+11 more)

### Community 7 - "test_files.py"
Cohesion: 0.09
Nodes (42): blue_png(), chunk(), create_sheet(), limited_client(), size(), png_bytes(), signed_in(), small_chunks() (+34 more)

### Community 8 - "permissions.py"
Cohesion: 0.10
Nodes (20): get_audit_service(), get_auth_service(), get_data_service(), get_file_service(), get_job_service(), get_oauth_service(), get_rbac_service(), get_services() (+12 more)

### Community 9 - "app.py"
Cohesion: 0.06
Nodes (12): AppFactory, SessionMiddleware, add_cookies(), problem_responses(), ProblemDetail, The request pipeline, 1. Model: `app/models/part.py`, 4. Routes: `app/api/routes/parts.py` (+4 more)

### Community 10 - "spreadsheet.py"
Cohesion: 0.08
Nodes (18): _bad_request(), create_spreadsheet_file(), delete_sheet(), get_spreadsheet_info(), _info(), _owned_spreadsheet(), _processor(), read_spreadsheet() (+10 more)

### Community 11 - "routes/auth/passkeys.py"
Cohesion: 0.11
Nodes (14): list_passkeys(), login_with_passkey(), passkey_login_options(), passkey_registration_options(), _refused(), register_passkey(), remove_passkey(), Passkey (+6 more)

### Community 13 - "upload.py"
Cohesion: 0.13
Nodes (9): upload_new_version(), complete_chunked_upload(), _parse_metadata(), _parse_tags(), _read_limited(), upload_chunk(), upload_file(), UploadSizeMismatchError (+1 more)

### Community 14 - "SpreadsheetProcessor"
Cohesion: 0.11
Nodes (5): neutralize(), SpreadsheetProcessor, with_headers(), validate_sheet_name(), test_parsing_stops_at_the_cell_limit()

### Community 15 - "BaseMiddleware"
Cohesion: 0.11
Nodes (4): BaseMiddleware, set_headers(), RequestIDMiddleware, create_log_context()

### Community 16 - "FileService"
Cohesion: 0.12
Nodes (3): FileResponse, FileService, iter_bytes()

### Community 17 - "MFAService"
Cohesion: 0.05
Nodes (23): ApiTokenError, public_view(), MFAError, MFAService, MFAStateError, _new_recovery_codes(), _normalize_recovery_code(), provisioning_uri() (+15 more)

### Community 19 - "test_webhooks.py"
Cohesion: 0.15
Nodes (13): collection_indexes(), test_audit_events_expire_after_the_configured_retention(), hooks(), jobs(), subscribe(), test_a_failing_receiver_is_retried_with_the_same_message_id(), test_audit_events_are_published_to_matching_subscriptions(), test_deliveries_to_a_removed_webhook_are_dropped() (+5 more)

### Community 20 - "test_data_layer.py"
Cohesion: 0.10
Nodes (17): file_record(), make_user(), rbac(), test_assignments_validate_against_definitions_and_take_effect_at_once(), test_changing_email_drops_the_old_email_lookup(), test_create_user_keeps_its_own_id(), test_deleted_file_leaves_the_listing_and_all_versions_are_flagged(), test_deleted_user_is_not_served_from_cache() (+9 more)

### Community 21 - "tests/conftest.py"
Cohesion: 0.06
Nodes (12): create_cache(), load_backend_class(), create_database(), _drop_superseded_indexes(), Migration, run_migrations(), DatabaseService, data_service() (+4 more)

### Community 22 - "S3Storage"
Cohesion: 0.17
Nodes (4): _is_missing(), S3Storage, collect(), send_part()

### Community 25 - "run"
Cohesion: 0.16
Nodes (19): run(), chunked(), collect(), collect_from(), failing_after(), _pieces(), test_a_failing_stream_leaves_nothing_behind(), test_open_stream_of_a_missing_file_is_none() (+11 more)

### Community 26 - "test_auth_flow.py"
Cohesion: 0.15
Nodes (23): _selected(), test_accounts_two_factor_files_audit_and_jobs(), bearer(), login(), make_admin(), register(), test_access_token_cannot_be_used_as_a_refresh_token(), test_cookie_and_bearer_both_authenticate() (+15 more)

### Community 27 - "middleware/rbac.py"
Cohesion: 0.09
Nodes (6): RBACMiddleware, AuditActor, set_audit_actor(), AppExceptionError, UserFacingExceptionError, client_ip()

### Community 28 - "routes/oauth.py"
Cohesion: 0.07
Nodes (14): login(), logout(), logout_all_devices(), refresh_tokens(), authorize_oauth(), _cookie_name(), link_oauth_account(), list_providers() (+6 more)

### Community 29 - "DataService"
Cohesion: 0.05
Nodes (9): AuditService, ApiTokenManager, _fernet(), DataService, FilesOps, OAuthOps, CachePolicy, _challenge() (+1 more)

### Community 30 - "get_session_details"
Cohesion: 0.27
Nodes (4): get_session_details(), list_active_sessions(), _own_session(), _public_view()

### Community 31 - "test_security_fixes.py"
Cohesion: 0.15
Nodes (14): bearer(), make_user(), test_a_file_cannot_collect_unbounded_versions(), test_bearer_requests_are_not_subject_to_the_origin_check(), test_chunks_much_larger_than_the_declared_average_are_refused(), test_cookie_authenticated_writes_from_foreign_origins_are_refused(), test_downloads_are_not_cacheable_by_shared_caches(), test_manager_cannot_suspend_an_administrator_but_can_suspend_a_user() (+6 more)

### Community 33 - "xlsx_patch.py"
Cohesion: 0.11
Nodes (12): _insert_before(), _cell_xml(), column_index(), column_letters(), new_sheet_xml(), _parse_rows(), patch_sheet_xml(), reject_unsafe_markup() (+4 more)

### Community 34 - "DeviceInfo"
Cohesion: 0.08
Nodes (4): DeviceInfo, AuthenticationError, MFARequiredError, Threats and controls

### Community 35 - "test_jobs.py"
Cohesion: 0.13
Nodes (15): job(), jobs(), make_due(), records(), test_a_handler_name_is_registered_once(), test_a_job_that_keeps_killing_its_worker_goes_dead(), test_a_job_without_a_handler_goes_dead_at_once(), test_a_queued_job_runs_once_and_is_marked_done() (+7 more)

### Community 36 - "PostgresDatabase"
Cohesion: 0.07
Nodes (25): PostgresDatabase, _compare(), decode(), _default(), dumps(), _encode_datetime(), _equals(), field() (+17 more)

### Community 37 - "test_route_access.py"
Cohesion: 0.13
Nodes (9): _compile_patterns(), path_matches(), permissions_of(), required_permissions(), test_every_authenticated_api_route_is_grantable_to_a_normal_user(), test_public_paths_match_whole_segments(), test_sensitive_surfaces_are_admin_only(), test_staff_only_permissions_are_held_by_managers_but_not_users() (+1 more)

### Community 38 - "base64"
Cohesion: 0.18
Nodes (8): code_at(), current_step(), generate_secret(), matching_step(), sign(), test_codes_match_the_rfc_6238_vectors(), test_one_step_of_clock_skew_is_accepted_and_two_are_not(), unb64()

### Community 40 - "registry.py"
Cohesion: 0.05
Nodes (20): Where things go, ErrorService, create_storage(), MetricsService, build_services(), sentry(), tracing(), register_job_handlers() (+12 more)

### Community 43 - "JobService"
Cohesion: 0.14
Nodes (3): JobService, 0007: Background jobs live in the configured database, test_an_expired_lease_runs_the_job_again_and_drops_the_stale_result()

### Community 44 - "download.py"
Cohesion: 0.14
Nodes (6): content_disposition(), not_found(), serve_stored_file(), download_file(), download_thumbnail(), get_file_metadata()

### Community 45 - "test_xlsx_patch.py"
Cohesion: 0.27
Nodes (11): media_and_charts(), names(), test_calc_chain_is_dropped_and_recalculation_requested(), test_cell_edit_keeps_charts_images_formulas_styles_and_other_sheets(), test_deleting_a_sheet_removes_only_that_sheet(), test_documents_with_a_dtd_are_refused(), test_new_sheet_is_added_and_the_package_stays_loadable(), test_overwriting_a_cell_keeps_its_style_and_clearing_keeps_the_cell() (+3 more)

### Community 46 - "pytest"
Cohesion: 0.12
Nodes (22): DuplicateRecordError, seed(), test_compound_unique_index_is_on_the_combination(), test_concurrent_increments_never_lose_or_repeat_a_value(), test_conditional_update_has_exactly_one_winner(), test_datetimes_come_back_timezone_aware_utc(), test_delete_removes_one_record_and_reports_it(), test_equality_on_a_list_field_means_contains() (+14 more)

### Community 49 - "ods.py"
Cohesion: 0.13
Nodes (13): _cell(), read(), _read_table(), _repeat(), _too_big(), _value(), write(), build() (+5 more)

### Community 50 - "build_test_app"
Cohesion: 0.07
Nodes (15): build_test_app(), api_schema(), app(), test_every_operation_honours_its_contract(), test_a_provider_without_required_settings_stops_start_up(), cors_client(), metrics_env(), test_cors_preflight_is_answered_without_credentials() (+7 more)

### Community 51 - "routes/auth/mfa.py"
Cohesion: 0.12
Nodes (14): confirm_totp_setup(), disable_totp(), get_mfa_status(), login_with_mfa_code(), _refused(), regenerate_recovery_codes(), start_totp_setup(), MFACode (+6 more)

### Community 53 - "TokenPayload"
Cohesion: 0.09
Nodes (8): TokenPair, TokenPayload, is_api_token(), TokenManager, authenticate_request(), extract_access_token(), _remember(), _silent_refresh()

### Community 54 - "OIDCClient"
Cohesion: 0.19
Nodes (4): OIDCClient, OIDCError, Upgrading, Sign in with Google, Microsoft, Okta or any OpenID Connect provider

### Community 55 - "Engineering standards"
Cohesion: 0.20
Nodes (10): 10. Style, docs and commits, 11. Definition of done, 12. AI-written contributions, 1. Before writing code, 2. Principles, 3. Architecture, 7. Security and configuration, 8. Errors and observability (+2 more)

### Community 56 - "SecurityHeadersMiddleware"
Cohesion: 0.10
Nodes (3): SecurityHeadersMiddleware, add_headers(), set_request_id()

### Community 57 - "MemoryCache"
Cohesion: 0.17
Nodes (3): MemoryCache, test_memory_cache_expiry_and_prefix_delete(), test_memory_cache_rate_limit_windows()

### Community 58 - "test_oidc.py"
Cohesion: 0.08
Nodes (19): health_check(), liveness_check(), metrics_endpoint(), _now(), readiness_check(), startup_check(), client(), FakeIdP (+11 more)

### Community 59 - "WebhookService"
Cohesion: 0.16
Nodes (5): list_webhooks(), WebhookError, WebhookService, Background jobs, `webhooks` (`WebhookService`)

### Community 60 - "PasswordService"
Cohesion: 0.05
Nodes (6): User, UserCreate, UserInDB, SessionManager, UserManager, PasswordService

### Community 63 - "BodySizeLimitMiddleware"
Cohesion: 0.10
Nodes (12): send_wrapper(), BodySizeLimitMiddleware, counting_receive(), tracking_send(), _BodyStalled, _BodyTooLarge, tracking_send(), capture_send() (+4 more)

### Community 64 - "IdempotencyMiddleware"
Cohesion: 0.19
Nodes (3): IdempotencyMiddleware, respond(), _problem()

### Community 65 - "AuthService"
Cohesion: 0.05
Nodes (17): change_password(), confirm_password_reset(), request_password_reset(), register(), revoke_all_sessions(), revoke_session(), delete_user(), ChangePasswordRequest (+9 more)

### Community 66 - "OAuthService"
Cohesion: 0.11
Nodes (7): unlink_oauth_account(), OAuthAccount, OAuthUserInfo, UserRole, OAuthService, test_oauth_sign_in_does_not_inherit_a_pre_registered_unverified_account(), test_unlinked_provider_identity_cannot_sign_in()

### Community 67 - "test_cache_contract.py"
Cohesion: 0.15
Nodes (3): test_concurrent_adds_have_exactly_one_winner(), test_concurrent_hits_never_exceed_the_limit(), test_value_expires_after_its_ttl()

### Community 69 - "routes/tokens.py"
Cohesion: 0.18
Nodes (7): create_api_token(), list_api_tokens(), revoke_api_token(), ApiToken, ApiTokenCreate, ApiTokenCreated, ApiTokenListResponse

### Community 70 - "PasskeyManager"
Cohesion: 0.28
Nodes (3): _b64url_decode(), PasskeyManager, public_view()

### Community 72 - "Configuration reference"
Cohesion: 0.15
Nodes (13): Access control and OAuth, Application, Authentication, Background jobs and audit, Cache, Configuration reference, Database, Email (+5 more)

### Community 74 - "_ConsoleFormatter"
Cohesion: 0.22
Nodes (5): _ConsoleFormatter, _JsonFormatter, _one_line(), _RequestIdFilter, test_console_log_lines_cannot_be_forged_by_request_text()

### Community 75 - "signed_in"
Cohesion: 0.13
Nodes (29): events(), test_a_failing_audit_write_does_not_block_the_change(), test_admin_changes_are_recorded_as_the_admin(), test_filters_and_paging(), test_only_administrators_can_read_the_log(), test_password_change_is_recorded_with_actor_ip_and_request_id(), test_refused_changes_are_not_recorded(), test_registration_is_attributed_to_the_new_account() (+21 more)

### Community 76 - "FastAPI Foundation: the production-grade chassis for serious FastAPI back ends"
Cohesion: 0.18
Nodes (11): Contributing, Documentation, FAQ, FastAPI Foundation: the production-grade chassis for serious FastAPI back ends, Features, License, Project structure, Quick start (+3 more)

### Community 79 - "test_mfa.py"
Cohesion: 0.35
Nodes (16): challenge(), code(), enrol(), finish(), test_a_code_works_only_once(), test_an_administrator_can_reset_a_lost_second_factor(), test_an_expired_challenge_is_refused(), test_challenge_tokens_are_not_access_tokens_and_vice_versa() (+8 more)

### Community 80 - "Configure common features"
Cohesion: 0.18
Nodes (11): Change roles, groups and limits, Configure common features, Let a browser front end call the API, Run behind a reverse proxy, Send password-reset email, Store files in S3 (or MinIO, R2, ...), Turn on observability, Turn on passkeys (+3 more)

### Community 81 - "Getting started"
Cohesion: 0.20
Nodes (10): 1. Set up, 2. Start the databases, 3. Create the first administrator, 4. Run the API, 5. Register and sign in, 6. Upload and list a file, 7. See access control at work, 8. Explore and test (+2 more)

### Community 83 - "create_webhook"
Cohesion: 0.36
Nodes (4): create_webhook(), Webhook, WebhookCreate, WebhookCreated

### Community 84 - "test_cache_degradation.py"
Cohesion: 0.17
Nodes (5): cache(), DownBackend, test_after_one_failure_the_backend_is_left_alone_until_the_cooldown_ends(), test_operations_without_a_fallback_say_so(), test_reads_become_misses_and_writes_are_skipped()

### Community 88 - "For decision makers"
Cohesion: 0.25
Nodes (8): Decisions to make before building on it, For decision makers, How it helps the business, Scope: what it leaves to you, What it costs to run, What you can build with it, What you get on day one, Why it can be trusted

### Community 91 - "Endpoints"
Cohesion: 0.18
Nodes (11): Access control (administrators), API tokens (your own), Authentication, Endpoints, Files (your own), Health (public), Passkeys, Sessions (your own) (+3 more)

### Community 92 - "asyncio"
Cohesion: 0.17
Nodes (4): main(), _send_blocking(), send_email(), send_password_reset_email()

### Community 94 - "routes/rbac.py"
Cohesion: 0.24
Nodes (5): get_user_permissions(), list_groups(), list_permissions(), list_roles(), require_permission()

### Community 95 - "run-background-jobs.md"
Cohesion: 0.22
Nodes (6): 0004: Plain service wiring and pluggable backends, 1. Register a handler, 2. Enqueue from a service, 3. Choose where the worker runs, 4. Watch it, Run background jobs

### Community 97 - "Code of Conduct"
Cohesion: 0.33
Nodes (5): Code of Conduct, Expected behaviour, Our pledge, Scope and enforcement, Unacceptable behaviour

### Community 98 - "Security model"
Cohesion: 0.20
Nodes (10): API tokens, Audit trail, Browser defences, Not covered, Passkeys, Security model, Sessions and tokens, Sign-in protection (+2 more)

### Community 99 - "Deploy"
Cohesion: 0.33
Nodes (6): Build the image, Deploy, Probes, Production checklist, Start-up sequence, Try the whole stack locally

### Community 100 - "RateDecision"
Cohesion: 0.15
Nodes (4): RateDecision, A cache backend, A storage backend, Bring your own database, cache or storage

### Community 102 - "manage.py"
Cohesion: 0.18
Nodes (3): get_file_versions(), list_files(), update_file()

### Community 103 - "remove_role"
Cohesion: 0.29
Nodes (4): assign_role(), _not_found(), remove_role(), revoke_temporary_permission()

### Community 104 - "Changed"
Cohesion: 0.25
Nodes (8): [1.0.0] - 2026-10-10, Added, Added, Changed, Changelog, Fixed, [Unreleased], Upgrading from 0.x

### Community 105 - ".update"
Cohesion: 0.25
Nodes (6): Conventions, Rules worth knowing, 2. Data: `app/services/data/parts_ops.py`, Data model, Migrations, Rules that keep the data honest

### Community 106 - "For designers"
Cohesion: 0.18
Nodes (7): expand(), Copy rules from security, For designers, Patterns the API expects, Screens and the states they need, The account journey, Turning errors into states

### Community 108 - "Contributing"
Cohesion: 0.20
Nodes (10): Code of Conduct, Commits, Contributing, Documentation, Find your way with the code graph, Pull request checklist, Releases, Set up (about ten minutes) (+2 more)

### Community 109 - "test_middleware.py"
Cohesion: 0.11
Nodes (7): TimeoutMiddleware, tracking_send(), build(), stream(), test_escaping_exceptions_become_generic_problem_500s(), test_slow_requests_get_a_504(), test_streaming_responses_pass_through_intact()

### Community 110 - "Architecture"
Cohesion: 0.20
Nodes (10): Architecture, Authentication model, Bring your own backend, Files, Known limits, Resilience, Wiring, 9. Dependencies (+2 more)

### Community 115 - "test_api_tokens.py"
Cohesion: 0.31
Nodes (13): as_token(), create(), stored(), test_a_token_never_exceeds_its_owner(), test_invalid_requests_are_refused_with_a_reason(), test_last_used_is_updated(), test_other_users_cannot_revoke_your_token(), test_revoked_expired_and_unknown_tokens_are_refused() (+5 more)

### Community 116 - "Documentation"
Cohesion: 0.50
Nodes (4): Diagrams, Documentation, Every document, Start here, by role

### Community 117 - "pull_request_template.md"
Cohesion: 0.40
Nodes (4): AI assistance, Checklist, How it was tested, What and why

### Community 118 - "Collections"
Cohesion: 0.18
Nodes (15): Sign in with a provider, `api_tokens` (`ApiTokenManager`), `audit_events` (`AuditService`), Collections, `files` (`FilesOps`), `jobs` (`JobService`), `login_attempts`, `mfa_totp` (`MFAService`) (+7 more)

### Community 119 - "Security policy"
Cohesion: 0.50
Nodes (4): Reporting a vulnerability, Scope, Security policy, Supported versions

### Community 126 - "ensure_bootstrap_admin"
Cohesion: 0.47
Nodes (5): ensure_bootstrap_admin(), make_auth_service(), test_bootstrap_admin_created_only_when_configured_and_empty(), test_bootstrap_admin_skipped_when_users_exist(), test_no_default_admin_without_explicit_config()

### Community 127 - "admin.py"
Cohesion: 0.12
Nodes (8): list_audit_events(), list_jobs(), _paged(), AuditEvent, AuditEventListResponse, Job, JobListResponse, InvalidCursorError

### Community 135 - "generate-a-client.md"
Cohesion: 0.33
Nodes (5): Calling the API from a browser, Generate a typed client, Other languages, TypeScript (web and React Native), When you change the API

### Community 136 - "AGENTS.md"
Cohesion: 0.18
Nodes (9): Commands, Navigate with the code graph, not by reading everything, Rule zero: the standards are a gate, Rules that are checked in review, Skills, What this is, Tests, 6. Tests (+1 more)

### Community 141 - "create_app"
Cohesion: 0.19
Nodes (7): create_app(), build_schema(), render(), client(), operations(), test_committed_snapshot_matches_the_application(), test_operation_ids_are_unique_and_readable()

### Community 150 - "Send webhooks to other systems"
Cohesion: 0.40
Nodes (5): Safety, Send webhooks to other systems, Subscribe, Verify the signature, What the receiver gets

### Community 153 - ".resolve_user_permissions"
Cohesion: 0.18
Nodes (3): _clip(), Access control, 5. Code

### Community 154 - "A database backend"
Cohesion: 0.25
Nodes (6): A database backend, Index declarations, Prove it, The filter vocabulary, The methods, The record model

### Community 156 - "Conventions"
Cohesion: 0.29
Nodes (7): API reference, Authentication, Conventions, Errors, Idempotency, Permissions, Response headers

## Knowledge Gaps
- **140 isolated node(s):** `fastapi-boilerplate`, `Done when`, `What and why`, `How it was tested`, `Checklist` (+135 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1254 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **74 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Config` to `config.py`, `app.py`, `LocalStorage`, `create_app`, `SpreadsheetProcessor`, `BaseMiddleware`, `DatabaseInterface`, `MFAService`, `FileService`, `tests/conftest.py`, `S3Storage`, `test_auth_flow.py`, `routes/oauth.py`, `DataService`, `test_route_access.py`, `registry.py`, `JobService`, `Logger`, `build_test_app`, `TokenPayload`, `WebhookService`, `PasswordService`, `AuthService`, `OAuthService`, `PasskeyManager`, `_ConsoleFormatter`, `CacheInterface`, `RBACService`, `asyncio`, `test_middleware.py`, `.__init__`, `ensure_bootstrap_admin`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `Config` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Config` has 48 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fastapi-boilerplate`, `Done when`, `What and why` to the rest of the system?**
  _140 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `xlsx_package.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14624505928853754 - nodes in this community are weakly interconnected._
- **Why does `Logger` connect `Logger` to `config.py`, `Config`, `app.py`, `LocalStorage`, `SpreadsheetProcessor`, `BaseMiddleware`, `DatabaseInterface`, `MFAService`, `FileService`, `tests/conftest.py`, `S3Storage`, `DataService`, `registry.py`, `JobService`, `TokenPayload`, `WebhookService`, `PasswordService`, `AuthService`, `OAuthService`, `_ConsoleFormatter`, `CacheInterface`, `RBACService`, `asyncio`, `.__init__`, `ensure_bootstrap_admin`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `Logger` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Logger` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Should `e` be split into smaller, more focused modules?**
  _Cohesion score 0.08837209302325581 - nodes in this community are weakly interconnected._