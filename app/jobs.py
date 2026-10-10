"""Run the background job worker on its own: ``python -m app.jobs``.

Use it when jobs should not share CPU with requests: set ``jobs_run_in_api = false`` for the
API processes and run one or more of these (each claims jobs safely alongside the others).
Register handlers in ``register_job_handlers`` (``app/services/registry.py``) so the API and
this worker know the same jobs.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal

from app.services.registry import build_services
from config import Config


async def main() -> None:
    config = Config()
    services = build_services(config)
    await services.data_service.connect()
    worker = asyncio.create_task(services.job_service.run_forever())
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.cancel)
    try:
        with contextlib.suppress(asyncio.CancelledError):
            await worker
    finally:
        services.logger.info("Job worker stopped")
        await services.data_service.close()


if __name__ == "__main__":
    asyncio.run(main())
