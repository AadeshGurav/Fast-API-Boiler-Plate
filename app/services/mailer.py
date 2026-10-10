"""Minimal outbound email over SMTP (stdlib only).

Configure ``smtp_host`` (and optionally ``smtp_port``, ``smtp_username``,
``smtp_password``, ``smtp_from``, ``smtp_starttls``) in ``config.local.toml`` (or as ``FABP_SMTP_*`` environment variables).
Without ``smtp_host`` nothing is sent: the problem is logged loudly, and in debug mode
the message is logged in full so local development still works.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

SMTP_TIMEOUT_SECONDS = 10


def _send_blocking(config: Config, message: EmailMessage) -> None:
    host = config["smtp_host"]
    port = config["smtp_port"]
    with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS) as server:
        if config["smtp_starttls"]:
            server.starttls(context=ssl.create_default_context())  # verify cert and host
        username = config["smtp_username"]
        if username:
            server.login(username, config["smtp_password"])
        server.send_message(message)


async def send_email(config: Config, logger: Logger, to: str, subject: str, body: str) -> bool:
    """Send a plain-text email without blocking the event loop.

    Returns:
    -------
        True if the message was handed to the SMTP server.

    """
    if not config["smtp_host"]:
        if config["app_debug"]:
            logger.warning(f"SMTP not configured; email to {to} not sent:\n{subject}\n{body}")
        else:
            logger.error(
                "SMTP is not configured (set smtp_host in config.local.toml or FABP_SMTP_HOST); "
                f"email '{subject}' was not delivered."
            )
        return False

    message = EmailMessage()
    message["From"] = config["smtp_from"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        await asyncio.to_thread(_send_blocking, config, message)
    except (OSError, smtplib.SMTPException) as e:
        logger.error(f"Failed to send email '{subject}': {e}")
        return False
    return True


async def send_password_reset_email(config: Config, logger: Logger, to: str, token: str) -> bool:
    """Email a password-reset link (or the bare token if no URL template is set)."""
    template = config["password_reset_url_template"]
    target = template.format(token=token) if template else f"Reset token: {token}"
    body = (
        "A password reset was requested for your account.\n\n"
        f"{target}\n\n"
        "The link works once and expires soon. If you did not ask for this, "
        "you can ignore this message; your password has not changed."
    )
    return await send_email(config, logger, to, "Reset your password", body)
