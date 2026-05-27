from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from core.config import Settings
from core.logging import get_logger
from models.pipeline import OutputBundle, TimelineMilestone
from models.user import UserPublic
from services import email_service, reminder_store, user_store

log = get_logger(__name__)


def _project_name(bundle: OutputBundle) -> str:
    name = bundle.rfp.filename or "Untitled project"
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


def timeline_rows_for_email(timeline: list[TimelineMilestone], project_name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in timeline:
        rows.append(
            {
                "project_name": item.project_name or project_name,
                "milestone": item.milestone,
                "end_deadline": item.end_deadline,
                "required_deliverables": item.required_deliverables or item.dependency,
                "status": item.status,
                "priority": item.priority,
            }
        )
    return rows


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _reminder_payloads(
    settings: Settings,
    timeline: list[TimelineMilestone],
    submission_date: str,
) -> list[dict[str, str]]:
    payloads: list[dict[str, str]] = []
    for item in timeline:
        deadline = _parse_iso_date(item.end_deadline)
        if deadline is None:
            continue
        reminder_day = deadline - timedelta(days=settings.reminder_days_before)
        payloads.append(
            {
                "milestone": item.milestone,
                "milestone_name": item.milestone,
                "end_deadline": item.end_deadline,
                "deadline_date": item.end_deadline,
                "reminder_date": reminder_day.isoformat(),
                "required_deliverables": item.required_deliverables or item.dependency,
                "pending_tasks": item.required_deliverables or item.dependency,
                "priority": item.priority,
                "status": item.status,
                "submission_date": submission_date,
            }
        )
    return payloads


def schedule_project_reminders(settings: Settings, user: UserPublic, bundle: OutputBundle) -> int:
    """Schedule 3-day-before deadline reminders (idempotent per run + milestone)."""
    project = _project_name(bundle)
    scheduled = reminder_store.schedule_reminders(
        settings,
        user_id=user.id,
        user_email=user.email,
        run_id=bundle.run_id,
        project_name=project,
        submission_date=bundle.submission_date or "",
        milestones=_reminder_payloads(settings, bundle.timeline, bundle.submission_date or ""),
    )
    log.info(
        "notifications.reminders_scheduled",
        run_id=bundle.run_id,
        user_id=user.id,
        reminders_scheduled=scheduled,
    )
    return scheduled


def notify_draft_complete(settings: Settings, user: UserPublic, bundle: OutputBundle) -> dict[str, object]:
    """Send the full project timeline email when the final draft is generated."""
    project = _project_name(bundle)
    rows = timeline_rows_for_email(bundle.timeline, project)
    draft_sections = len(bundle.draft_response.sections) if bundle.draft_response else 0
    sent = email_service.send_draft_ready_timeline_email(
        settings,
        to_email=user.email,
        user_name=user.full_name,
        project_name=project,
        submission_date=bundle.submission_date or "",
        expected_completion_date=bundle.expected_completion_date or "",
        draft_sections=draft_sections,
        timeline_rows=rows,
    )
    scheduled = schedule_project_reminders(settings, user, bundle)
    log.info(
        "notifications.draft_complete",
        run_id=bundle.run_id,
        user_id=user.id,
        email_sent=sent,
        reminders_scheduled=scheduled,
    )
    return {"email_sent": sent, "reminders_scheduled": scheduled}


def process_due_reminders(settings: Settings) -> int:
    today = datetime.now(UTC).date().isoformat()
    due = reminder_store.list_due_reminders(settings, today)
    sent_count = 0
    for row in due:
        user = user_store.get_user_by_id(settings, row["user_id"])
        user_name = user.full_name if user else "User"
        ok = email_service.send_deadline_reminder_email(
            settings,
            to_email=row["user_email"],
            user_name=user_name,
            project_name=row["project_name"],
            milestone_name=row["milestone_name"],
            deadline_date=row["deadline_date"],
            submission_date=row["submission_date"],
            pending_tasks=row["pending_tasks"] or row["required_deliverables"],
            priority=row["priority"],
            status=row["status"],
            days_before=settings.reminder_days_before,
        )
        if ok:
            reminder_store.mark_reminder_sent(settings, row["id"])
            sent_count += 1
    return sent_count
