# Graph Report - Fast-API-Boiler-Plate  (2026-10-11)

## Corpus Check
- 219 files · ~220,089 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 7, .example 2, .toml 1)

## Summary
- 3088 nodes · 7580 edges · 166 communities (93 shown, 73 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 827 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ca92e4ce`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- xlsx_package.py
- StorageInterface
- e
- user.py
- typing
- MongoDB
- Config
- test_files.py
- permissions.py
- BaseMiddleware
- spreadsheet.py
- routes/auth/passkeys.py
- upload.py
- SpreadsheetProcessor
- base.py
- FileService
- MFAService
- .handle
- test_webhooks.py
- test_data_layer.py
- DatabaseService
- S3Storage
- UsersOps
- ChunkedUploadHandler
- run
- test_auth_flow.py
- middleware/rbac.py
- auth.py
- DataService
- get_session_details
- test_security_fixes.py
- docs/README.md
- xlsx_patch.py
- AuthService
- health.py
- PostgresDatabase
- test_route_access.py
- routes/oauth.py
- build_services
- FakeDatabase
- .__call__
- JobService
- download.py
- test_xlsx_patch.py
- pytest
- SessionsOps
- Logger
- ods.py
- build_test_app
- routes/auth/mfa.py
- Operations runbook
- TokenPayload
- oidc.py
- Engineering standards
- .handle
- MemoryCache
- test_passkeys.py
- WebhookService
- PasswordService
- CacheService
- .__call__
- IdempotencyMiddleware
- OAuthService
- test_cache_contract.py
- routes/tokens.py
- services/auth/passkeys.py
- .format_error
- Configuration reference
- contract/conftest.py
- .__init__
- signed_in
- FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter
- CSRFOriginMiddleware
- test_mfa.py
- Configure common features
- Getting started
- services/auth/mfa.py
- webhook.py
- .__setup_routes
- normalize_user
- RBACService
- MeteredStream
- For decision makers
- 3. Recommendations
- role.py
- Endpoints
- .handle
- test_optional_packages.py
- routes/rbac.py
- run-background-jobs.md
- ._encode
- Code of Conduct
- Security model
- Deploy
- json
- delete_file
- manage.py
- assign_group
- Changed
- Any
- For designers
- test_oidc.py
- Contributing
- test_middleware.py
- ProblemDetail
- body_limit.py
- AuditService
- .allows
- 0005: Scale-out file handling and cache resilience
- Documentation
- pull_request_template.md
- Collections
- Security policy
- ensure_bootstrap_admin
- admin.py
- TemporaryPermissionsOps
- fastapi-boilerplate
- create_temporary_permission
- retry_job
- generate-a-client.md
- test_cache_degradation.py
- .handle
- run_migrations
- rbac
- oauth/__init__.py
- test_smtp_starttls_verifies_the_server_certificate
- remove_webhook
- Send webhooks to other systems
- Competitive analysis and roadmap proposal (October 2026)
- Rows
- neutralize
- FakeIdP
- Clock
- ._parse

## God Nodes (most connected - your core abstractions)
1. `Config` - 167 edges
2. `Logger` - 117 edges
3. `TokenPayload` - 96 edges
4. `AuthService` - 95 edges
5. `DataService` - 84 edges
6. `e()` - 70 edges
7. `run()` - 68 edges
8. `signed_in()` - 60 edges
9. `FileService` - 58 edges
10. `RBACService` - 50 edges

## Surprising Connections (you probably didn't know these)
- `The methods` --references--> `DuplicateRecordError`  [INFERRED]
  docs/how-to/write-a-backend.md → app/core/interfaces/database_interface.py
- `0006: PostgreSQL ships as a JSONB document backend` --references--> `DatabaseInterface`  [INFERRED]
  docs/adr/0006-postgresql-as-jsonb-documents.md → app/core/interfaces/database_interface.py
- `P1-1. PostgreSQL backend (built in, optional)` --references--> `DatabaseInterface`  [INFERRED]
  docs/proposals/2026-10-competitive-analysis.md → app/core/interfaces/database_interface.py
- `P1-2. Durable background jobs, with no new dependency` --references--> `DatabaseInterface`  [INFERRED]
  docs/proposals/2026-10-competitive-analysis.md → app/core/interfaces/database_interface.py
- `P3 (only when a real user needs it)` --references--> `DataService`  [INFERRED]
  docs/proposals/2026-10-competitive-analysis.md → app/services/data/data_service.py

## Import Cycles
- 3-file cycle: `app/services/file/__init__.py -> app/services/file/file_service.py -> app/services/file/spreadsheet_processor.py -> app/services/file/__init__.py`

## Communities (166 total, 73 thin omitted)

### Community 0 - "xlsx_package.py"
Cohesion: 0.15
Nodes (7): _add_sheet(), _delete_sheet(), _drop_calculation_state(), edit_xlsx(), _Package, _parse_xml(), _sheet_parts()

### Community 1 - "StorageInterface"
Cohesion: 0.04
Nodes (13): What this is, CacheInterface, RateDecision, DatabaseInterface, StorageInterface, Ways to help, Bring your own backend, Other common changes (+5 more)

### Community 2 - "e"
Cohesion: 0.09
Nodes (50): body(), body(), body(), infra(), body(), body(), body(), body() (+42 more)

### Community 3 - "user.py"
Cohesion: 0.08
Nodes (11): register(), get_current_user_info(), update_my_profile(), User, UserCreate, UserInDB, UserListResponse, UserPublic (+3 more)

### Community 6 - "Config"
Cohesion: 0.06
Nodes (19): main(), reference_markdown(), Settings, Config, ConfigError, main(), test_config_behaves_like_a_mapping_and_rejects_unknown_attributes(), test_configured_secret_is_left_alone() (+11 more)

### Community 7 - "test_files.py"
Cohesion: 0.09
Nodes (42): blue_png(), chunk(), create_sheet(), limited_client(), size(), png_bytes(), signed_in(), small_chunks() (+34 more)

### Community 8 - "permissions.py"
Cohesion: 0.09
Nodes (20): get_audit_service(), get_auth_service(), get_data_service(), get_file_service(), get_job_service(), get_oauth_service(), get_rbac_service(), get_services() (+12 more)

### Community 9 - "BaseMiddleware"
Cohesion: 0.06
Nodes (13): AppFactory, create_app(), AccessLogMiddleware, BaseMiddleware, BodySizeLimitMiddleware, ErrorHandlerMiddleware, RateLimiter, RequestIDMiddleware (+5 more)

### Community 10 - "spreadsheet.py"
Cohesion: 0.08
Nodes (18): _bad_request(), create_spreadsheet_file(), delete_sheet(), get_spreadsheet_info(), _info(), _owned_spreadsheet(), _processor(), read_spreadsheet() (+10 more)

### Community 11 - "routes/auth/passkeys.py"
Cohesion: 0.11
Nodes (13): list_passkeys(), login_with_passkey(), passkey_login_options(), passkey_registration_options(), _refused(), register_passkey(), remove_passkey(), Passkey (+5 more)

### Community 13 - "upload.py"
Cohesion: 0.13
Nodes (9): upload_new_version(), complete_chunked_upload(), _parse_metadata(), _parse_tags(), _read_limited(), upload_chunk(), upload_file(), UploadSizeMismatchError (+1 more)

### Community 17 - "MFAService"
Cohesion: 0.16
Nodes (5): MFAError, MFAService, MFAStateError, _new_recovery_codes(), hash_token()

### Community 19 - "test_webhooks.py"
Cohesion: 0.15
Nodes (13): collection_indexes(), test_audit_events_expire_after_the_configured_retention(), hooks(), jobs(), subscribe(), test_a_failing_receiver_is_retried_with_the_same_message_id(), test_audit_events_are_published_to_matching_subscriptions(), test_deliveries_to_a_removed_webhook_are_dropped() (+5 more)

### Community 20 - "test_data_layer.py"
Cohesion: 0.11
Nodes (16): file_record(), make_user(), test_assignments_validate_against_definitions_and_take_effect_at_once(), test_changing_email_drops_the_old_email_lookup(), test_create_user_keeps_its_own_id(), test_deleted_file_leaves_the_listing_and_all_versions_are_flagged(), test_deleted_user_is_not_served_from_cache(), test_find_many_does_not_write_list_results_to_cache() (+8 more)

### Community 21 - "DatabaseService"
Cohesion: 0.20
Nodes (4): _drop_superseded_indexes(), _flag_latest_file_versions(), Migration, DatabaseService

### Community 22 - "S3Storage"
Cohesion: 0.07
Nodes (16): _clip(), _is_missing(), S3Storage, collect(), send_part(), Access control, Architecture, Authentication model (+8 more)

### Community 25 - "run"
Cohesion: 0.07
Nodes (36): run(), job(), jobs(), make_due(), records(), test_a_handler_name_is_registered_once(), test_a_job_that_keeps_killing_its_worker_goes_dead(), test_a_job_without_a_handler_goes_dead_at_once() (+28 more)

### Community 26 - "test_auth_flow.py"
Cohesion: 0.11
Nodes (26): test_accounts_two_factor_files_audit_and_jobs(), bearer(), login(), make_admin(), register(), test_access_token_cannot_be_used_as_a_refresh_token(), test_cookie_and_bearer_both_authenticate(), test_duplicate_email_is_rejected() (+18 more)

### Community 27 - "middleware/rbac.py"
Cohesion: 0.09
Nodes (6): RBACMiddleware, AuditActor, set_audit_actor(), AppExceptionError, UserFacingExceptionError, client_ip()

### Community 28 - "auth.py"
Cohesion: 0.05
Nodes (15): login(), logout(), logout_all_devices(), refresh_tokens(), ChangePasswordRequest, LoginRequest, PasswordResetConfirm, PasswordResetRequest (+7 more)

### Community 29 - "DataService"
Cohesion: 0.10
Nodes (5): DataService, FilesOps, OAuthOps, CachePolicy, is_session_active()

### Community 30 - "get_session_details"
Cohesion: 0.13
Nodes (6): get_session_details(), list_active_sessions(), _own_session(), _public_view(), revoke_all_sessions(), revoke_session()

### Community 31 - "test_security_fixes.py"
Cohesion: 0.14
Nodes (16): _ConsoleFormatter, bearer(), make_user(), test_a_file_cannot_collect_unbounded_versions(), test_bearer_requests_are_not_subject_to_the_origin_check(), test_chunks_much_larger_than_the_declared_average_are_refused(), test_console_log_lines_cannot_be_forged_by_request_text(), test_cookie_authenticated_writes_from_foreign_origins_are_refused() (+8 more)

### Community 32 - "docs/README.md"
Cohesion: 0.26
Nodes (3): 0001: Tokens are bound to a server-side session, 0002: The service is API-only, 0006: PostgreSQL ships as a JSONB document backend

### Community 33 - "xlsx_patch.py"
Cohesion: 0.11
Nodes (12): _insert_before(), _cell_xml(), column_index(), column_letters(), new_sheet_xml(), _parse_rows(), patch_sheet_xml(), reject_unsafe_markup() (+4 more)

### Community 34 - "AuthService"
Cohesion: 0.06
Nodes (8): change_password(), confirm_password_reset(), request_password_reset(), LoginResponse, DeviceInfo, AuthenticationError, AuthService, MFARequiredError

### Community 35 - "health.py"
Cohesion: 0.12
Nodes (11): build_schema(), render(), health_check(), liveness_check(), metrics_endpoint(), _now(), readiness_check(), startup_check() (+3 more)

### Community 36 - "PostgresDatabase"
Cohesion: 0.08
Nodes (21): PostgresDatabase, _compare(), decode(), _default(), dumps(), _encode_datetime(), _equals(), field() (+13 more)

### Community 37 - "test_route_access.py"
Cohesion: 0.13
Nodes (10): _compile_patterns(), path_matches(), 5. Permissions: `config.toml`, permissions_of(), required_permissions(), test_every_authenticated_api_route_is_grantable_to_a_normal_user(), test_public_paths_match_whole_segments(), test_sensitive_surfaces_are_admin_only() (+2 more)

### Community 38 - "routes/oauth.py"
Cohesion: 0.12
Nodes (7): authorize_oauth(), _cookie_name(), list_providers(), oauth_callback(), _unknown(), default_cookie_secure(), purge_abandoned_uploads_forever()

### Community 40 - "build_services"
Cohesion: 0.06
Nodes (17): main(), ErrorService, MetricsService, build_services(), sentry(), tracing(), Services, SentryService (+9 more)

### Community 41 - "FakeDatabase"
Cohesion: 0.06
Nodes (9): RedisCache, A database backend, Index declarations, Prove it, The filter vocabulary, The methods, The record model, P0-3. Run the backend contract tests against real engines (+1 more)

### Community 44 - "download.py"
Cohesion: 0.12
Nodes (7): content_disposition(), not_found(), serve_stored_file(), download_file(), download_thumbnail(), get_file_metadata(), Threats and controls

### Community 45 - "test_xlsx_patch.py"
Cohesion: 0.25
Nodes (11): media_and_charts(), names(), test_calc_chain_is_dropped_and_recalculation_requested(), test_cell_edit_keeps_charts_images_formulas_styles_and_other_sheets(), test_deleting_a_sheet_removes_only_that_sheet(), test_documents_with_a_dtd_are_refused(), test_new_sheet_is_added_and_the_package_stays_loadable(), test_overwriting_a_cell_keeps_its_style_and_clearing_keeps_the_cell() (+3 more)

### Community 46 - "pytest"
Cohesion: 0.11
Nodes (23): DuplicateRecordError, seed(), test_compound_unique_index_is_on_the_combination(), test_concurrent_increments_never_lose_or_repeat_a_value(), test_conditional_update_has_exactly_one_winner(), test_datetimes_come_back_timezone_aware_utc(), test_delete_removes_one_record_and_reports_it(), test_equality_on_a_list_field_means_contains() (+15 more)

### Community 48 - "Logger"
Cohesion: 0.06
Nodes (9): create_cache(), ImageProcessor, LocalStorage, Logger, _send_blocking(), send_email(), send_password_reset_email(), register_job_handlers() (+1 more)

### Community 49 - "ods.py"
Cohesion: 0.09
Nodes (20): _cell(), read(), _read_table(), _repeat(), _too_big(), _value(), write(), API reference (+12 more)

### Community 50 - "build_test_app"
Cohesion: 0.09
Nodes (11): build_test_app(), api_schema(), app(), test_every_operation_honours_its_contract(), test_a_provider_without_required_settings_stops_start_up(), metrics_env(), test_rate_limit_answers_429_with_retry_after_and_is_per_client_tier(), test_two_apps_in_one_process_do_not_collide_on_metric_names() (+3 more)

### Community 51 - "routes/auth/mfa.py"
Cohesion: 0.12
Nodes (14): confirm_totp_setup(), disable_totp(), get_mfa_status(), login_with_mfa_code(), _refused(), regenerate_recovery_codes(), start_totp_setup(), MFACode (+6 more)

### Community 52 - "Operations runbook"
Cohesion: 0.12
Nodes (14): 503 "Server overloaded" or 504 timeouts, A user is locked out, A user lost their authenticator phone, An account or token may be compromised, Background jobs are failing, Disk filling up, Everyone gets 429 Too Many Requests, MongoDB is down or refuses credentials (+6 more)

### Community 53 - "TokenPayload"
Cohesion: 0.08
Nodes (16): delete_user(), get_user(), list_users(), _public(), set_user_status(), TokenPayload, UserRole, UserStatus (+8 more)

### Community 54 - "oidc.py"
Cohesion: 0.16
Nodes (5): _challenge(), OIDCClient, OIDCError, Upgrading, Sign in with Google, Microsoft, Okta or any OpenID Connect provider

### Community 55 - "Engineering standards"
Cohesion: 0.10
Nodes (18): Commands, Navigate with the code graph, not by reading everything, Rule zero: the standards are a gate, Rules that are checked in review, Skills, Tests, 10. Style, docs and commits, 11. Definition of done (+10 more)

### Community 57 - "MemoryCache"
Cohesion: 0.16
Nodes (3): MemoryCache, test_memory_cache_expiry_and_prefix_delete(), test_memory_cache_rate_limit_windows()

### Community 58 - "test_passkeys.py"
Cohesion: 0.19
Nodes (14): b64(), enrol(), sign_in(), signed_in(), SoftAuthenticator, test_a_cloned_authenticator_is_caught_by_its_signature_counter(), test_a_passkey_from_another_site_or_origin_is_refused(), test_api_tokens_cannot_manage_passkeys() (+6 more)

### Community 59 - "WebhookService"
Cohesion: 0.17
Nodes (5): create_webhook(), WebhookError, WebhookService, Background jobs, `webhooks` (`WebhookService`)

### Community 63 - ".__call__"
Cohesion: 0.10
Nodes (9): counting_receive(), tracking_send(), tracking_send(), capture_send(), tracking_send(), test_a_stalled_request_body_is_cut_off(), app(), receive() (+1 more)

### Community 64 - "IdempotencyMiddleware"
Cohesion: 0.19
Nodes (3): IdempotencyMiddleware, respond(), _problem()

### Community 66 - "OAuthService"
Cohesion: 0.13
Nodes (6): unlink_oauth_account(), OAuthAccount, OAuthUserInfo, OAuthService, test_oauth_sign_in_does_not_inherit_a_pre_registered_unverified_account(), test_unlinked_provider_identity_cannot_sign_in()

### Community 67 - "test_cache_contract.py"
Cohesion: 0.15
Nodes (3): test_concurrent_adds_have_exactly_one_winner(), test_concurrent_hits_never_exceed_the_limit(), test_value_expires_after_its_ttl()

### Community 69 - "routes/tokens.py"
Cohesion: 0.18
Nodes (7): create_api_token(), list_api_tokens(), revoke_api_token(), ApiToken, ApiTokenCreate, ApiTokenCreated, ApiTokenListResponse

### Community 70 - "services/auth/passkeys.py"
Cohesion: 0.18
Nodes (3): _b64url_decode(), PasskeyManager, public_view()

### Community 72 - "Configuration reference"
Cohesion: 0.15
Nodes (13): Access control and OAuth, Application, Authentication, Background jobs and audit, Cache, Configuration reference, Database, Email (+5 more)

### Community 73 - "contract/conftest.py"
Cohesion: 0.10
Nodes (9): load_backend_class(), create_database(), create_storage(), cache(), _config(), database(), _drop(), _selected() (+1 more)

### Community 74 - ".__init__"
Cohesion: 0.25
Nodes (3): _JsonFormatter, _one_line(), _RequestIdFilter

### Community 75 - "signed_in"
Cohesion: 0.10
Nodes (42): as_token(), create(), stored(), test_a_token_never_exceeds_its_owner(), test_invalid_requests_are_refused_with_a_reason(), test_last_used_is_updated(), test_other_users_cannot_revoke_your_token(), test_revoked_expired_and_unknown_tokens_are_refused() (+34 more)

### Community 76 - "FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter"
Cohesion: 0.22
Nodes (9): Contributing, Documentation, FAQ, FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter, License, Project structure, Quick start, Tech stack (+1 more)

### Community 79 - "test_mfa.py"
Cohesion: 0.35
Nodes (16): challenge(), code(), enrol(), finish(), test_a_code_works_only_once(), test_an_administrator_can_reset_a_lost_second_factor(), test_an_expired_challenge_is_refused(), test_challenge_tokens_are_not_access_tokens_and_vice_versa() (+8 more)

### Community 80 - "Configure common features"
Cohesion: 0.18
Nodes (11): Change roles, groups and limits, Configure common features, Let a browser front end call the API, Run behind a reverse proxy, Send password-reset email, Store files in S3 (or MinIO, R2, ...), Turn on observability, Turn on passkeys (+3 more)

### Community 81 - "Getting started"
Cohesion: 0.20
Nodes (10): 1. Set up, 2. Start the databases, 3. Create the first administrator, 4. Run the API, 5. Register and sign in, 6. Upload and list a file, 7. See access control at work, 8. Explore and test (+2 more)

### Community 82 - "services/auth/mfa.py"
Cohesion: 0.11
Nodes (12): _fernet(), _normalize_recovery_code(), code_at(), current_step(), generate_secret(), matching_step(), provisioning_uri(), _fernet() (+4 more)

### Community 83 - "webhook.py"
Cohesion: 0.47
Nodes (3): Webhook, WebhookCreate, WebhookCreated

### Community 84 - ".__setup_routes"
Cohesion: 0.25
Nodes (5): Where things go, 1. Model: `app/models/part.py`, 4. Routes: `app/api/routes/parts.py`, 6. Test it through the real app, Add a resource

### Community 88 - "For decision makers"
Cohesion: 0.25
Nodes (8): Decisions to make before building on it, For decision makers, How it helps the business, Scope: what it leaves to you, What it costs to run, What you can build with it, What you get on day one, Why it can be trusted

### Community 89 - "3. Recommendations"
Cohesion: 0.13
Nodes (15): openapi(), 3. Recommendations, P0-1. Pin `ruff` and add the hygiene CI jobs, P1-1. PostgreSQL backend (built in, optional), P1-2. Durable background jobs, with no new dependency, P1-3. MFA: TOTP plus recovery codes, P1-4. Personal access tokens / API keys, P1-5. Security audit log of changes (+7 more)

### Community 91 - "Endpoints"
Cohesion: 0.12
Nodes (13): link_oauth_account(), Access control (administrators), API tokens (your own), Authentication, Endpoints, Files (your own), Health (public), Passkeys (+5 more)

### Community 93 - "test_optional_packages.py"
Cohesion: 0.20
Nodes (4): set_user(), is_free(), test_enabling_a_feature_without_its_package_names_the_fix(), test_sentry_user_tagging_is_a_no_op_until_sentry_starts()

### Community 94 - "routes/rbac.py"
Cohesion: 0.24
Nodes (5): get_user_permissions(), list_groups(), list_permissions(), list_roles(), require_permission()

### Community 95 - "run-background-jobs.md"
Cohesion: 0.25
Nodes (5): 1. Register a handler, 2. Enqueue from a service, 3. Choose where the worker runs, 4. Watch it, Run background jobs

### Community 97 - "Code of Conduct"
Cohesion: 0.33
Nodes (5): Code of Conduct, Expected behaviour, Our pledge, Scope and enforcement, Unacceptable behaviour

### Community 98 - "Security model"
Cohesion: 0.20
Nodes (10): API tokens, Audit trail, Browser defences, Not covered, Passkeys, Security model, Sessions and tokens, Sign-in protection (+2 more)

### Community 99 - "Deploy"
Cohesion: 0.33
Nodes (6): Build the image, Deploy, Probes, Production checklist, Start-up sequence, Try the whole stack locally

### Community 100 - "json"
Cohesion: 0.24
Nodes (4): after(), decode(), encode(), newest_first()

### Community 102 - "manage.py"
Cohesion: 0.18
Nodes (3): get_file_versions(), list_files(), update_file()

### Community 103 - "assign_group"
Cohesion: 0.22
Nodes (5): assign_group(), assign_role(), _not_found(), remove_role(), revoke_temporary_permission()

### Community 104 - "Changed"
Cohesion: 0.25
Nodes (8): [1.0.0] - 2026-10-10, Added, Added, Changed, Changelog, Fixed, [Unreleased], Upgrading from 0.x

### Community 105 - "Any"
Cohesion: 0.08
Nodes (9): _convert_datetime_strings(), _default_cache_key(), _normalize_record(), Layers, Rules worth knowing, 2. Data: `app/services/data/parts_ops.py`, Data model, Migrations (+1 more)

### Community 106 - "For designers"
Cohesion: 0.18
Nodes (7): expand(), Copy rules from security, For designers, Patterns the API expects, Screens and the states they need, The account journey, Turning errors into states

### Community 107 - "test_oidc.py"
Cohesion: 0.23
Nodes (12): client(), finish(), idp(), start(), test_a_full_sign_in_creates_an_account_and_a_session(), test_a_token_signed_by_another_key_is_refused(), test_an_unverified_email_cannot_sign_in(), test_rotated_keys_are_fetched_again() (+4 more)

### Community 108 - "Contributing"
Cohesion: 0.20
Nodes (10): Code of Conduct, Commits, Contributing, Conventions, Documentation, Find your way with the code graph, Pull request checklist, Releases (+2 more)

### Community 109 - "test_middleware.py"
Cohesion: 0.24
Nodes (5): build(), stream(), test_escaping_exceptions_become_generic_problem_500s(), test_slow_requests_get_a_504(), test_streaming_responses_pass_through_intact()

### Community 110 - "ProblemDetail"
Cohesion: 0.22
Nodes (3): problem_responses(), ProblemDetail, Errors

### Community 113 - "AuditService"
Cohesion: 0.07
Nodes (6): AuditService, ApiTokenError, ApiTokenManager, public_view(), SessionManager, `audit_events` (`AuditService`)

### Community 116 - "Documentation"
Cohesion: 0.50
Nodes (4): Diagrams, Documentation, Every document, Start here, by role

### Community 117 - "pull_request_template.md"
Cohesion: 0.40
Nodes (4): AI assistance, Checklist, How it was tested, What and why

### Community 118 - "Collections"
Cohesion: 0.27
Nodes (12): `api_tokens` (`ApiTokenManager`), Collections, `files` (`FilesOps`), `jobs` (`JobService`), `login_attempts`, `mfa_totp` (`MFAService`), `oauth_accounts` (`OAuthOps`), `passkeys` (`PasskeyManager`) (+4 more)

### Community 119 - "Security policy"
Cohesion: 0.50
Nodes (4): Reporting a vulnerability, Scope, Security policy, Supported versions

### Community 126 - "ensure_bootstrap_admin"
Cohesion: 0.47
Nodes (5): ensure_bootstrap_admin(), make_auth_service(), test_bootstrap_admin_created_only_when_configured_and_empty(), test_bootstrap_admin_skipped_when_users_exist(), test_no_default_admin_without_explicit_config()

### Community 127 - "admin.py"
Cohesion: 0.11
Nodes (9): list_audit_events(), list_jobs(), list_webhooks(), _paged(), AuditEvent, AuditEventListResponse, Job, JobListResponse (+1 more)

### Community 135 - "generate-a-client.md"
Cohesion: 0.33
Nodes (5): Calling the API from a browser, Generate a typed client, Other languages, TypeScript (web and React Native), When you change the API

### Community 136 - "test_cache_degradation.py"
Cohesion: 0.17
Nodes (5): cache(), DownBackend, test_after_one_failure_the_backend_is_left_alone_until_the_cooldown_ends(), test_operations_without_a_fallback_say_so(), test_reads_become_misses_and_writes_are_skipped()

### Community 150 - "Send webhooks to other systems"
Cohesion: 0.40
Nodes (5): Safety, Send webhooks to other systems, Subscribe, Verify the signature, What the receiver gets

### Community 160 - "Competitive analysis and roadmap proposal (October 2026)"
Cohesion: 0.20
Nodes (9): 1. Who we compete with, 2. Gaps found in our own repository while checking, 4. What not to add, and why, 5. What to remove or reconsider, 6. Suggested order of work, 7. Decisions needed from the maintainer, Competitive analysis and roadmap proposal (October 2026), Progress (+1 more)

## Knowledge Gaps
- **155 isolated node(s):** `fastapi-boilerplate`, `Done when`, `What and why`, `How it was tested`, `Checklist` (+150 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1268 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Config` to `StorageInterface`, `user.py`, `typing`, `BaseMiddleware`, `.__init__`, `base.py`, `FileService`, `MFAService`, `SpreadsheetProcessor`, `DatabaseService`, `S3Storage`, `ChunkedUploadHandler`, `test_auth_flow.py`, `auth.py`, `DataService`, `AuthService`, `health.py`, `test_route_access.py`, `routes/oauth.py`, `build_services`, `JobService`, `Logger`, `build_test_app`, `TokenPayload`, `WebhookService`, `PasswordService`, `CacheService`, `Any`, `OAuthService`, `services/auth/passkeys.py`, `contract/conftest.py`, `.__init__`, `services/auth/mfa.py`, `RBACService`, `test_optional_packages.py`, `Any`, `test_middleware.py`, `tracing.py`, `AuditService`, `ensure_bootstrap_admin`?**
  _High betweenness centrality (0.203) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `Config` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Config` has 48 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fastapi-boilerplate`, `Done when`, `What and why` to the rest of the system?**
  _155 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `xlsx_package.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14855072463768115 - nodes in this community are weakly interconnected._
- **Why does `Logger` connect `Logger` to `StorageInterface`, `user.py`, `typing`, `Config`, `BaseMiddleware`, `run_migrations`, `.__init__`, `base.py`, `FileService`, `MFAService`, `SpreadsheetProcessor`, `DatabaseService`, `S3Storage`, `ChunkedUploadHandler`, `auth.py`, `DataService`, `AuthService`, `build_services`, `JobService`, `WebhookService`, `PasswordService`, `CacheService`, `Any`, `OAuthService`, `contract/conftest.py`, `.__init__`, `services/auth/mfa.py`, `RBACService`, `Any`, `tracing.py`, `AuditService`, `ensure_bootstrap_admin`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `Logger` (e.g. with `AppFactory` and `BaseMiddleware`) actually correct?**
  _`Logger` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Should `StorageInterface` be split into smaller, more focused modules?**
  _Cohesion score 0.04480874316939891 - nodes in this community are weakly interconnected._