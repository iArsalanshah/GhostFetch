import asyncio

from src.core.job_manager import JobManager
from src.utils.config import settings


class _FakeScraper:
    async def fetch(self, url, context_id=None, auth_storage_state_path=None):
        return {"metadata": {"title": "ok"}, "markdown": "body"}


class _AuthRequiredScraper:
    async def fetch(self, url, context_id=None, auth_storage_state_path=None):
        from src.core.scraper import ScraperError
        raise ScraperError("Authentication required", "auth_required", retryable=False)


def test_job_manager_completes_and_triggers_callback(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path}/jobs.db")
    monkeypatch.setattr(settings, "MAX_CONCURRENT_BROWSERS", 1)

    callback_called = {"value": False}

    async def _fake_callback(job):
        callback_called["value"] = True

    async def _run():
        manager = JobManager(_FakeScraper())
        manager._send_callback_async = _fake_callback
        await manager.start()
        job_id = await manager.submit_job("https://example.com", callback_url="https://hooks.example.com")
        await asyncio.wait_for(manager.queue.join(), timeout=2)
        await asyncio.sleep(0.05)
        job = manager.get_job(job_id)
        await manager.stop()
        return job

    job = asyncio.run(_run())
    assert callback_called["value"] is True
    assert job is not None
    assert job.status == "completed"


def test_job_manager_records_auth_required_as_structured_result(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path}/jobs.db")
    monkeypatch.setattr(settings, "MAX_CONCURRENT_BROWSERS", 1)

    async def _run():
        manager = JobManager(_AuthRequiredScraper())
        await manager.start()
        job_id = await manager.submit_job("https://example.com")
        await asyncio.wait_for(manager.queue.join(), timeout=2)
        job = manager.get_job(job_id)
        await manager.stop()
        return job

    job = asyncio.run(_run())
    assert job is not None
    assert job.status == "completed"
    assert isinstance(job.result, dict)
    assert job.result["status"] == "auth_required"
