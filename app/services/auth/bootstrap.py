"""First-run administrator creation, driven by explicit configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.user import UserCreate

if TYPE_CHECKING:
    from app.services.auth import AuthService
    from app.services.logger import Logger
    from config import Config


async def ensure_bootstrap_admin(auth_service: AuthService, config: Config, logger: Logger) -> bool:
    """Create the first admin from config when the user collection is empty.

    There is intentionally no default account: a built-in ``admin/admin`` login is a
    backdoor on every fresh deployment. Provide ``bootstrap_admin_username``,
    ``bootstrap_admin_email`` and ``bootstrap_admin_password`` (e.g. in the gitignored
    ``config.local.toml``) to seed one; remove them afterwards.

    Args:
    ----
        auth_service: Auth service used to register the user.
        config: Application configuration.
        logger: Logger instance.

    Returns:
    -------
        True if an admin was created.

    """
    username = config["bootstrap_admin_username"]
    email = config["bootstrap_admin_email"]
    password = config["bootstrap_admin_password"]

    if await auth_service.data_service.count("users", {}):
        return False

    if not (username and email and password):
        logger.warning(
            "No users exist and no bootstrap admin is configured; set "
            "bootstrap_admin_username/_email/_password in config.local.toml "
            "(or FABP_BOOTSTRAP_ADMIN_* env vars) to create the first administrator."
        )
        return False

    await auth_service.register_user(
        UserCreate(username=username, email=email, password=password, roles=["admin"])
    )
    logger.info(f"Bootstrap admin '{username}' created; remove its credentials from config.")
    return True
