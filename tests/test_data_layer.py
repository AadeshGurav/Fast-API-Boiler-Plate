"""Regression tests for the database / cache / data-service layering."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.mongodb import MongoDB
from app.services.auth.bootstrap import ensure_bootstrap_admin
from app.services.data.policies import CachePolicy
from app.services.data.users_ops import normalize_user

USER = {"username": "ada", "email": "ada@example.com", "roles": ["user"], "status": "active"}


async def make_user(data_service, **overrides) -> str:
    return await data_service.users.create_user({**USER, **overrides})


async def warm_all_lookups(data_service, user_id: str, user: dict = USER) -> None:
    await data_service.users.get_user_by_id(user_id)
    await data_service.users.get_user_by_username(user["username"])
    await data_service.users.get_user_by_email(user["email"])


# --- DataService write semantics -------------------------------------------------


async def test_update_unknown_record_creates_nothing(data_service):
    assert await data_service.update("users", {"id": "ghost"}, {"status": "x"}) is False
    assert await data_service.database_service.find_many("users", {}) == []


async def test_update_user_unknown_id_returns_false_and_stores_nothing(data_service):
    assert await data_service.users.update_user("missing", {"status": "locked"}) is False
    assert await data_service.database_service.find_many("users", {}) == []


async def test_partial_set_does_not_replace_cached_record_with_the_fragment(data_service):
    await data_service.set("things", {"id": "1"}, {"id": "1", "name": "full", "qty": 3})
    await data_service.get("things", {"id": "1"})  # warm the cache

    await data_service.set("things", {"id": "1"}, {"qty": 4})

    record = await data_service.get("things", {"id": "1"})
    assert record["name"] == "full"
    assert record["qty"] == 4


async def test_find_many_does_not_write_list_results_to_cache(data_service):
    await data_service.set("things", {"id": "1"}, {"id": "1"}, policy=CachePolicy.DB_ONLY)
    await data_service.find_many("things", {}, policy=CachePolicy.AUTO)
    assert data_service.cache_service.backend._items == {}


async def test_datetimes_survive_the_cache_round_trip(data_service):
    created = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    await data_service.set("things", {"id": "1"}, {"id": "1", "created_at": created})

    from_db = await data_service.get("things", {"id": "1"})
    from_cache = await data_service.get("things", {"id": "1"})

    assert from_db["created_at"] == from_cache["created_at"] == created


# --- User cache invalidation -----------------------------------------------------


async def test_update_user_refreshes_every_cached_lookup_key(data_service):
    user_id = await make_user(data_service)
    await warm_all_lookups(data_service, user_id)

    await data_service.users.update_user(user_id, {"roles": ["admin"]})

    assert (await data_service.users.get_user_by_id(user_id))["roles"] == ["admin"]
    assert (await data_service.users.get_user_by_username("ada"))["roles"] == ["admin"]
    assert (await data_service.users.get_user_by_email("ada@example.com"))["roles"] == ["admin"]


async def test_changing_email_drops_the_old_email_lookup(data_service):
    user_id = await make_user(data_service)
    await warm_all_lookups(data_service, user_id)

    await data_service.users.update_user(user_id, {"email": "new@example.com"})

    assert await data_service.users.get_user_by_email("ada@example.com") is None
    assert (await data_service.users.get_user_by_email("new@example.com"))["username"] == "ada"


async def test_deleted_user_is_not_served_from_cache(data_service):
    user_id = await make_user(data_service)
    await warm_all_lookups(data_service, user_id)

    assert await data_service.users.delete_user(user_id) is True

    assert await data_service.users.get_user_by_id(user_id) is None
    assert await data_service.users.get_user_by_username("ada") is None


async def test_create_user_keeps_its_own_id(data_service):
    user_id = await make_user(data_service)
    assert (await data_service.users.get_user_by_username("ada"))["id"] == user_id


# --- Normalisation is per-collection, not global ---------------------------------


def test_legacy_user_fields_are_normalised():
    user = normalize_user({"password": "hash", "profile": {"email": "a@b.c"}, "login_attempts": 3})
    assert user["password_hash"] == "hash"
    assert user["email"] == "a@b.c"
    assert user["login_attempts"] == []
    assert user["sessions"] == []


async def test_non_user_collections_do_not_gain_user_fields(data_service):
    await data_service.set("roles", {"id": "admin"}, {"id": "admin", "name": "Admin"})
    role = await data_service.get("roles", {"id": "admin"})
    assert "sessions" not in role and "login_attempts" not in role


def test_mongo_normalisation_keeps_the_business_id(config):
    backend = MongoDB(config, MagicMock())

    assert backend._normalize_record({"_id": "oid1", "id": "admin"}) == {"id": "admin"}
    assert backend._normalize_record({"_id": "oid1", "name": "x"}) == {"id": "oid1", "name": "x"}


# --- Cache service ----------------------------------------------------------------


async def test_clear_pattern_matches_keys_under_the_cache_prefix(data_service):
    cache = data_service.cache_service
    await cache.set("user_permissions:1", ["a"])
    await cache.set("user_permissions:2", ["b"])
    await cache.set("other:1", ["c"])

    assert await cache.clear_pattern("user_permissions:*") == 2

    assert await cache.get("user_permissions:1") is None
    assert await cache.get("other:1") == ["c"]


# --- Sessions / RBAC / OAuth write paths -----------------------------------------


async def test_update_missing_session_does_not_create_one(data_service):
    assert await data_service.sessions.update_session("nope", {"ip": "1.1.1.1"}) is False
    assert await data_service.database_service.find_many("sessions", {}) == []


async def test_revoking_unknown_temporary_permission_fails_cleanly(data_service):
    assert await data_service.temp_permissions.revoke("nope") is False
    assert await data_service.database_service.find_many("temporary_permissions", {}) == []


# --- Bootstrap admin --------------------------------------------------------------


def make_auth_service(existing_users: list):
    auth = MagicMock()
    auth.data_service.count = AsyncMock(return_value=len(existing_users))
    auth.register_user = AsyncMock()
    return auth


async def test_no_default_admin_without_explicit_config(config):
    auth = make_auth_service([])

    assert await ensure_bootstrap_admin(auth, config, MagicMock()) is False
    auth.register_user.assert_not_called()


async def test_bootstrap_admin_created_only_when_configured_and_empty(config):
    config.data.update(
        bootstrap_admin_username="root",
        bootstrap_admin_email="root@example.com",
        bootstrap_admin_password="a-long-password",
    )
    auth = make_auth_service([])

    assert await ensure_bootstrap_admin(auth, config, MagicMock()) is True
    created = auth.register_user.await_args.args[0]
    assert created.username == "root" and created.roles == ["admin"]


async def test_bootstrap_admin_skipped_when_users_exist(config):
    config.data.update(
        bootstrap_admin_username="root",
        bootstrap_admin_email="root@example.com",
        bootstrap_admin_password="a-long-password",
    )
    auth = make_auth_service([{"id": "1"}])

    assert await ensure_bootstrap_admin(auth, config, MagicMock()) is False
    auth.register_user.assert_not_called()


# --- Bring-your-own backends ------------------------------------------------------


async def test_memory_cache_rate_limit_windows(config):
    from app.cache.memory import MemoryCache

    cache = MemoryCache(config, MagicMock())
    await cache.connect()

    decisions = [await cache.hit("k", 2, 60) for _ in range(3)]

    assert [d.allowed for d in decisions] == [True, True, False]
    assert decisions[2].retry_after >= 1
    assert (await cache.hit("other", 2, 60)).allowed  # keys are independent


async def test_memory_cache_expiry_and_prefix_delete(config):
    from app.cache.memory import MemoryCache

    cache = MemoryCache(config, MagicMock())
    await cache.set("a:1", {"x": 1}, ttl=60)
    await cache.set("a:2", 2)
    await cache.set("b:1", 3, ttl=-1)  # already expired

    assert await cache.get("a:1") == {"x": 1}
    assert await cache.get("b:1") is None
    assert await cache.delete_prefix("a:") == 2


def test_providers_resolve_builtin_names_and_dotted_paths(config):
    from app.cache import BUILTIN_CACHES
    from app.core.plugins import load_backend_class

    assert load_backend_class("memory", BUILTIN_CACHES, "cache").__name__ == "MemoryCache"
    assert load_backend_class("app.cache.memory:MemoryCache", BUILTIN_CACHES, "cache")
    with pytest.raises(ValueError, match="Unknown cache provider"):
        load_backend_class("memcached", BUILTIN_CACHES, "cache")
    with pytest.raises(ValueError, match="Cannot load"):
        load_backend_class("nope.module:Thing", BUILTIN_CACHES, "cache")


# --- RBAC --------------------------------------------------------------------------


@pytest.fixture
def rbac(data_service, config):
    from app.services.audit import AuditService
    from app.services.rbac import RBACService

    config.data["rbac_roles"] = {
        "admin": {"permissions": ["*"], "inherits": []},
        "manager": {"permissions": ["users:read"], "inherits": ["user"]},
        "user": {"permissions": ["profile:read"], "inherits": ["base"]},
        "editor": {"permissions": ["files:*"], "inherits": ["base"]},
        "base": {"permissions": ["public:read"], "inherits": []},
        "loop_a": {"permissions": ["a"], "inherits": ["loop_b"]},
        "loop_b": {"permissions": ["b"], "inherits": ["loop_a"]},
    }
    config.data["rbac_groups"] = {"staff": {"roles": ["manager"]}}
    audit = AuditService(config, MagicMock(), data_service)
    return RBACService(config, MagicMock(), data_service, data_service.cache_service, audit)


async def test_inheritance_diamonds_work_and_cycles_terminate(rbac):
    assert rbac.resolve_role_inheritance("manager") == {"users:read", "profile:read", "public:read"}
    assert rbac.resolve_role_inheritance("loop_a") == {"a", "b"}


async def test_permissions_come_from_roles_groups_and_temporary_grants(rbac, data_service):
    user_id = await make_user(data_service, roles=["user"], groups=["staff"])

    held = await rbac.resolve_user_permissions(user_id)
    assert {"profile:read", "users:read"} <= set(held)
    assert not await rbac.check_permission(user_id, "files:read")

    await rbac.create_temporary_permission(
        {"entity_type": "user", "entity_id": user_id, "permission_id": "files:read"}
    )
    assert await rbac.check_permission(user_id, "files:read")  # cache was invalidated


async def test_wildcards_and_revoked_or_expired_grants(rbac, data_service):
    from datetime import UTC, datetime, timedelta

    editor = await make_user(data_service, username="ed", email="ed@x.io", roles=["editor"])
    admin = await make_user(data_service, username="ad", email="ad@x.io", roles=["admin"])
    assert await rbac.check_permission(editor, "files:delete")  # resource wildcard
    assert not await rbac.check_permission(editor, "users:read")
    assert await rbac.check_permission(admin, "anything:at_all")

    plain = await make_user(data_service, username="pl", email="pl@x.io", roles=[])
    grant = await rbac.create_temporary_permission(
        {"entity_type": "user", "entity_id": plain, "permission_id": "x:y"}
    )
    await rbac.create_temporary_permission(
        {
            "entity_type": "user",
            "entity_id": plain,
            "permission_id": "old:perm",
            "end_time": datetime.now(UTC) - timedelta(seconds=1),
        }
    )
    assert await rbac.check_permission(plain, "x:y") and not await rbac.check_permission(
        plain, "old:perm"
    )
    assert await rbac.revoke_temporary_permission(grant)
    assert not await rbac.check_permission(plain, "x:y")


async def test_assignments_validate_against_definitions_and_take_effect_at_once(rbac, data_service):
    user_id = await make_user(data_service, roles=[])

    assert not await rbac.assign_role(user_id, "no_such_role")
    assert not await rbac.assign_role("missing-user", "user")
    assert await rbac.assign_role(user_id, "admin")
    assert await rbac.check_permission(user_id, "whatever")
    assert await rbac.remove_role(user_id, "admin")
    assert not await rbac.check_permission(user_id, "whatever")


async def test_group_grants_reach_members(rbac, data_service):
    member = await make_user(data_service, groups=["staff"])
    other = await make_user(data_service, username="o2", email="o2@x.io")
    assert not await rbac.check_permission(member, "z:z")

    await rbac.create_temporary_permission(
        {"entity_type": "group", "entity_id": "staff", "permission_id": "z:z"}
    )

    assert await rbac.check_permission(member, "z:z")
    assert not await rbac.check_permission(other, "z:z")


# --- Migrations -----------------------------------------------------------------------


async def test_migrations_run_once_and_connect_applies_indexes(data_service):
    await data_service.connect()
    await data_service.connect()  # a second worker starting up

    recorded = await data_service.database_service.find_many("schema_migrations", {})
    assert [m["version"] for m in recorded] == [1, 2]
    assert len(data_service.database_service.backend.dropped) == 2
    assert "users" in data_service.database_service.backend.indexes


# --- file listing: paging happens in the database ---------------------------------


def file_record(file_id: str, version: int, created: int, user_id: str = "u1", **extra) -> dict:
    return {
        "file_id": file_id,
        "user_id": user_id,
        "version": version,
        "filename": f"{file_id}.txt",
        "created_at": datetime(2026, 1, created, tzinfo=UTC),
        **extra,
    }


async def test_listing_returns_newest_version_of_each_file_paged_in_the_database(data_service):
    files = data_service.files
    await files.create_file_metadata(file_record("a", 1, 1))
    await files.create_file_metadata(file_record("a", 2, 2))
    await files.create_file_metadata(file_record("b", 1, 3))
    await files.create_file_metadata(file_record("other", 1, 4, user_id="u2"))

    page, total = await files.get_user_files("u1", limit=10)
    assert total == 2
    assert {(f["file_id"], f["version"]) for f in page} == {("a", 2), ("b", 1)}

    first, _ = await files.get_user_files("u1", limit=1)
    second, _ = await files.get_user_files("u1", limit=1, offset=1)
    assert [first[0]["file_id"], second[0]["file_id"]] != [None, None]
    assert first[0]["file_id"] != second[0]["file_id"]


async def test_deleted_file_leaves_the_listing_and_all_versions_are_flagged(data_service):
    files = data_service.files
    await files.create_file_metadata(file_record("a", 1, 1))
    await files.create_file_metadata(file_record("a", 2, 2))

    assert await files.delete_file_metadata("a") is True
    assert await files.get_user_files("u1") == ([], 0)
    assert await files.get_file_by_id("a") is None
    assert len(await files.get_file_versions("a", include_deleted=True)) == 2
    assert await files.delete_file_metadata("a") is False


async def test_migration_flags_the_newest_version_of_existing_files(data_service):
    from app.services.data.migrations import MIGRATIONS

    db = data_service.database_service
    for record in (file_record("a", 1, 1), file_record("a", 3, 3), file_record("a", 2, 2)):
        await db.insert_record("files", record)  # pre-migration: no is_latest field
    migrate = next(m for m in MIGRATIONS if m.version == 2)

    await migrate.apply(db)
    await migrate.apply(db)  # idempotent

    flags = {r["version"]: r["is_latest"] for r in await db.find_many("files", {})}
    assert flags == {1: False, 2: False, 3: True}
