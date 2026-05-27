from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import get_settings
from core.logging import get_logger
from services.notification_service import process_due_reminders

log = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler  # noqa: PLW0603
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    _scheduler = AsyncIOScheduler()

    async def _run_reminders() -> None:
        try:
            count = process_due_reminders(get_settings())
            if count:
                log.info("scheduler.reminders_sent", count=count)
        except Exception as exc:  # noqa: BLE001
            log.error("scheduler.reminder_job_failed", error=str(exc))

    _scheduler.add_job(
        _run_reminders,
        trigger="interval",
        seconds=max(300, settings.scheduler_interval_seconds),
        id="deadline_reminders",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("scheduler.started", interval_seconds=settings.scheduler_interval_seconds)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler  # noqa: PLW0603
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler.stopped")
