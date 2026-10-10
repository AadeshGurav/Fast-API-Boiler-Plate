"""Background jobs: claiming, retries, the dead-letter state, leases, idempotency and admin."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.services.data.schema import collection_indexes
from app.services.jobs import JobService
from tests.conftest import run
from tests.test_features import admin_client, signed_in


@pytest.fixture
def jobs(env):
    services = env.services
    run(services.database_service.ensure_indexes(collection_indexes(services.config)))
    service = services.job_service
    service.backoff_base = 0.001
    return service


def records(env):
    return env.services.database_service.backend.collections.get("jobs", [])


def job(env, job_id):
    return next(j for j in records(env) if j["id"] == job_id)


def make_due(env, job_id):
    job(env, job_id)["run_at"] = datetime.now(UTC) - timedelta(seconds=1)


def test_a_queued_job_runs_once_and_is_marked_done(env, jobs):
    seen = []

    @jobs.handler("test.record")
    async def record(payload):
        seen.append(payload)

    job_id = run(jobs.enqueue("test.record", {"n": 1}))

    assert run(jobs.run_once()) == 1
    assert run(jobs.run_once()) == 0
    assert seen == [{"n": 1}]
    assert job(env, job_id)["status"] == "done" and job(env, job_id)["finished_at"] is not None


def test_failures_retry_with_backoff_then_go_dead(env, jobs):
    @jobs.handler("test.flaky")
    async def flaky(payload):
        raise ConnectionError("downstream unavailable")

    job_id = run(jobs.enqueue("test.flaky"))
    run(jobs.run_once())

    first = job(env, job_id)
    assert first["status"] == "queued" and first["attempts"] == 1
    assert "ConnectionError: downstream unavailable" in first["last_error"]

    for _ in range(jobs.max_attempts - 1):
        make_due(env, job_id)
        run(jobs.run_once())

    assert job(env, job_id)["status"] == "dead"
    assert job(env, job_id)["attempts"] == jobs.max_attempts


def test_a_job_without_a_handler_goes_dead_at_once(env, jobs):
    job_id = run(jobs.enqueue("test.nobody-handles-this"))

    run(jobs.run_once())

    assert job(env, job_id)["status"] == "dead"
    assert "No handler registered" in job(env, job_id)["last_error"]


def test_future_jobs_wait_for_their_time(env, jobs):
    @jobs.handler("test.later")
    async def later(payload):
        pass

    run(jobs.enqueue("test.later", run_at=datetime.now(UTC) + timedelta(hours=1)))

    assert run(jobs.run_once()) == 0


def test_the_same_idempotency_key_queues_one_job(env, jobs):
    first = run(jobs.enqueue("test.once", {"a": 1}, idempotency_key="order-42"))
    again = run(jobs.enqueue("test.once", {"a": 2}, idempotency_key="order-42"))

    assert first == again and len(records(env)) == 1


def test_two_workers_never_run_the_same_job(env, jobs):
    calls = []

    async def slow(payload):
        calls.append(payload["n"])
        await asyncio.sleep(0.01)

    other = JobService(env.services.config, env.services.logger, env.services.data_service)
    for worker in (jobs, other):
        worker.handlers["test.slow"] = slow
    for n in range(6):
        run(jobs.enqueue("test.slow", {"n": n}))

    async def both():
        await asyncio.gather(jobs.run_once(), other.run_once())

    run(both())

    assert sorted(calls) == list(range(6))


def test_an_expired_lease_runs_the_job_again_and_drops_the_stale_result(env, jobs):
    @jobs.handler("test.retry-after-crash")
    async def handler(payload):
        pass

    job_id = run(jobs.enqueue("test.retry-after-crash"))
    stuck = job(env, job_id)
    stuck.update(
        status="running",
        attempts=1,
        worker="crashed-worker",
        lease_until=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert run(jobs.run_once()) == 1
    assert job(env, job_id)["status"] == "done" and job(env, job_id)["attempts"] == 2

    crashed = JobService(env.services.config, env.services.logger, env.services.data_service)
    crashed.worker_id = "crashed-worker"
    run(crashed._finish(job(env, job_id), {"status": "dead"}))
    assert job(env, job_id)["status"] == "done"


def test_a_job_that_keeps_killing_its_worker_goes_dead(env, jobs):
    job_id = run(jobs.enqueue("test.poison"))
    job(env, job_id).update(
        status="running",
        attempts=jobs.max_attempts,
        lease_until=datetime.now(UTC) - timedelta(seconds=1),
    )

    run(jobs.run_once())

    assert job(env, job_id)["status"] == "dead"
    assert "lease expired" in job(env, job_id)["last_error"]


def test_attempts_are_cut_off_at_the_timeout(env, jobs):
    jobs.timeout = 0.05

    @jobs.handler("test.hangs")
    async def hangs(payload):
        await asyncio.sleep(5)

    job_id = run(jobs.enqueue("test.hangs"))
    run(jobs.run_once())

    assert job(env, job_id)["status"] == "queued"
    assert "TimeoutError" in job(env, job_id)["last_error"]


def test_a_handler_name_is_registered_once(jobs):
    with pytest.raises(ValueError, match="already registered"):
        jobs.handler("email.send")(lambda payload: None)


def test_email_job_retries_while_smtp_is_not_configured(env, jobs):
    job_id = run(jobs.enqueue("email.send", {"to": "a@b.io", "subject": "Hi", "body": "Hello"}))

    run(jobs.run_once())

    assert job(env, job_id)["status"] == "queued"
    assert "SMTP delivery failed" in job(env, job_id)["last_error"]


def test_administrators_see_dead_jobs_and_can_retry_them(env, jobs):
    job_id = run(jobs.enqueue("test.nobody-handles-this"))
    run(jobs.run_once())
    admin = admin_client(env)

    dead = admin.get("/api/v1/admin/jobs", params={"status": "dead"}).json()
    assert dead["total"] == 1 and dead["jobs"][0]["id"] == job_id

    assert admin.post(f"/api/v1/admin/jobs/{job_id}/retry").status_code == 200
    assert job(env, job_id)["status"] == "queued" and job(env, job_id)["attempts"] == 0
    assert admin.post(f"/api/v1/admin/jobs/{job_id}/retry").status_code == 404
    assert admin.get("/api/v1/admin/jobs", params={"status": "nonsense"}).status_code == 422
    assert signed_in(env).get("/api/v1/admin/jobs").status_code == 403


def test_the_api_process_runs_the_worker_unless_told_not_to(tmp_path):
    import time

    from fastapi.testclient import TestClient

    from tests.conftest import build_test_app

    for enabled in (True, False):
        app, services = build_test_app(tmp_path, jobs_run_in_api=enabled, jobs_poll_seconds=0.01)
        services.job_service.poll_seconds = 0.01
        ran = []

        @services.job_service.handler("test.in-api")
        async def in_api(payload, ran=ran):
            ran.append(True)

        with TestClient(app):
            run(services.job_service.enqueue("test.in-api"))
            deadline = time.monotonic() + 2
            while enabled and not ran and time.monotonic() < deadline:
                time.sleep(0.01)

        assert bool(ran) is enabled
