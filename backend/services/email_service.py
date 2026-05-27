from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from core.config import Settings
from core.logging import get_logger

log = get_logger(__name__)


def _timeline_table_html(rows: list[dict[str, str]], title: str = "Project timeline") -> str:
    headers = [
        ("project_name", "Project"),
        ("milestone", "Milestone / Task"),
        ("end_deadline", "Deadline"),
        ("required_deliverables", "Required deliverables"),
        ("status", "Status"),
        ("priority", "Priority"),
    ]
    head = "".join(
        f"<th style='padding:8px;border:1px solid #ccc;text-align:left'>{label}</th>" for _, label in headers
    )
    body_rows = []
    for row in rows:
        cells = "".join(
            f"<td style='padding:8px;border:1px solid #eee;vertical-align:top'>{row.get(key, '—')}</td>"
            for key, _ in headers
        )
        body_rows.append(f"<tr>{cells}</tr>")
    return f"""
    <h2 style="font-family:Segoe UI,Arial,sans-serif;color:#1e293b">{title}</h2>
    <table style="border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif;font-size:14px">
      <thead><tr style="background:#f1f5f9">{head}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
    """


def _write_outbox(settings: Settings, to_email: str, subject: str, html_body: str) -> None:
    outbox = Path(settings.data_dir).parent / "email_outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    safe = to_email.replace("@", "_at_").replace(".", "_")
    stamp = __import__("datetime").datetime.now(__import__("datetime").UTC).strftime("%Y%m%dT%H%M%S")
    path = outbox / f"{stamp}_{safe}.html"
    path.write_text(f"<h1>{subject}</h1>\n{html_body}", encoding="utf-8")
    log.info("email.outbox_written", path=str(path), to=to_email)


def send_email(settings: Settings, to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    if not settings.email_enabled or not settings.smtp_host:
        _write_outbox(settings, to_email, subject, html_body)
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp_password = settings.smtp_password.replace(" ", "")
                server.login(settings.smtp_user, smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        log.info("email.sent", to=to_email, subject=subject)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("email.send_failed", to=to_email, error=str(exc))
        _write_outbox(settings, to_email, subject, html_body)
        return False


def send_draft_ready_timeline_email(
    settings: Settings,
    *,
    to_email: str,
    user_name: str,
    project_name: str,
    submission_date: str,
    expected_completion_date: str,
    draft_sections: int,
    timeline_rows: list[dict[str, str]],
) -> bool:
    table = _timeline_table_html(timeline_rows, "Complete project timeline")
    reminder_days = settings.reminder_days_before
    html = f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;color:#0f172a;line-height:1.6;max-width:720px">
      <p>Hello {user_name},</p>
      <p>Your final proposal draft for <strong>{project_name}</strong> has been generated successfully.
      Below is your complete project timeline with all major milestones, deadlines, and deliverables.</p>
      <table style="border-collapse:collapse;font-size:14px;margin:16px 0;background:#f8fafc">
        <tr><td style="padding:8px 12px;font-weight:600">Project</td><td style="padding:8px 12px">{project_name}</td></tr>
        <tr><td style="padding:8px 12px;font-weight:600">Proposal draft</td><td style="padding:8px 12px">{draft_sections} section(s) ready</td></tr>
        <tr><td style="padding:8px 12px;font-weight:600">Submission date</td><td style="padding:8px 12px">{submission_date or '—'}</td></tr>
        <tr><td style="padding:8px 12px;font-weight:600">Expected completion</td><td style="padding:8px 12px">{expected_completion_date or '—'}</td></tr>
      </table>
      {table}
      <p style="margin-top:20px"><strong>What happens next</strong></p>
      <ul style="padding-left:20px">
        <li>Review each milestone and confirm required deliverables are on track.</li>
        <li>Complete pending tasks before each deadline to avoid last-minute delays.</li>
        <li>You will receive an automatic reminder email <strong>{reminder_days} days before</strong> every major deadline listed above.</li>
      </ul>
      <p style="color:#64748b;font-size:13px;margin-top:24px">
        This email is your permanent project timeline record. Keep it for reference throughout the engagement.
      </p>
    </div>
    """
    text = (
        f"Draft ready for {project_name}. "
        f"Submission: {submission_date or '—'}. "
        f"{len(timeline_rows)} milestone(s). "
        f"Reminders will be sent {reminder_days} days before each deadline."
    )
    return send_email(
        settings,
        to_email,
        subject=f"Draft ready — project timeline for {project_name}",
        html_body=html,
        text_body=text,
    )


def send_deadline_reminder_email(
    settings: Settings,
    *,
    to_email: str,
    user_name: str,
    project_name: str,
    milestone_name: str,
    deadline_date: str,
    submission_date: str,
    pending_tasks: str,
    priority: str,
    status: str,
    days_before: int | None = None,
) -> bool:
    lead_days = days_before if days_before is not None else settings.reminder_days_before
    pending = pending_tasks or "Review deliverables and confirm all requirements are complete before the deadline."
    html = f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;color:#0f172a;line-height:1.6;max-width:720px">
      <p>Hello {user_name},</p>
      <p style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px 16px;border-radius:4px">
        <strong>Action required:</strong> A major project deadline is approaching in <strong>{lead_days} days</strong>.
        Please complete the pending work below on time to stay on schedule.
      </p>
      <table style="border-collapse:collapse;font-size:14px;margin:16px 0;width:100%">
        <tr style="background:#f8fafc">
          <td style="padding:8px 12px;font-weight:600;width:40%">Project</td>
          <td style="padding:8px 12px">{project_name}</td>
        </tr>
        <tr>
          <td style="padding:8px 12px;font-weight:600">Upcoming milestone</td>
          <td style="padding:8px 12px">{milestone_name}</td>
        </tr>
        <tr style="background:#f8fafc">
          <td style="padding:8px 12px;font-weight:600">Deadline date</td>
          <td style="padding:8px 12px"><strong>{deadline_date}</strong></td>
        </tr>
        <tr>
          <td style="padding:8px 12px;font-weight:600">Submission date</td>
          <td style="padding:8px 12px">{submission_date or '—'}</td>
        </tr>
        <tr style="background:#f8fafc">
          <td style="padding:8px 12px;font-weight:600">Priority</td>
          <td style="padding:8px 12px">{priority}</td>
        </tr>
        <tr>
          <td style="padding:8px 12px;font-weight:600">Current status</td>
          <td style="padding:8px 12px">{status}</td>
        </tr>
      </table>
      <p><strong>Pending requirements / tasks to complete:</strong></p>
      <p style="background:#f1f5f9;padding:12px 16px;border-radius:4px">{pending}</p>
      <p style="margin-top:20px">Please allocate time now to finish these deliverables before <strong>{deadline_date}</strong>.
      Completing this milestone on schedule helps keep the overall project on track.</p>
      <p style="color:#64748b;font-size:13px;margin-top:24px">
        This is an automated reminder sent {lead_days} days before the deadline.
      </p>
    </div>
    """
    text = (
        f"Reminder ({lead_days} days): complete pending work for '{milestone_name}' "
        f"in project '{project_name}' before {deadline_date}. Tasks: {pending}"
    )
    return send_email(
        settings,
        to_email,
        subject=f"Deadline in {lead_days} days — {project_name}: {milestone_name}",
        html_body=html,
        text_body=text,
    )
