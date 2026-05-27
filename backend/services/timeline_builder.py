from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

from models.pipeline import OutputBundle, TimelineMilestone
from models.rfp import RFPDocument, Requirement


def _project_name(rfp: RFPDocument) -> str:
    raw = rfp.filename or "Untitled project"
    stem = Path(raw).stem if raw else "Untitled project"
    org = str(rfp.metadata.get("org_hint") or "").strip()
    if org and org.lower() not in stem.lower():
        return f"{org} — {stem}"
    return stem


def _priority_for_milestone(name: str) -> str:
    lowered = name.lower()
    if any(k in lowered for k in ("submission", "go-live", "uat", "deadline")):
        return "High"
    if any(k in lowered for k in ("design", "build", "integration")):
        return "Medium"
    return "Low"


def build_strict_timeline(
    rfp: RFPDocument, requirements: list[Requirement]
) -> tuple[list[TimelineMilestone], str, str]:
    submission = _resolve_submission_date(rfp, requirements)
    project = _project_name(rfp)
    milestone_defs = [
        (
            "RFP submission baseline confirmed",
            submission,
            submission,
            "Submission package, mandatory annexures, and compliance attestations",
        ),
        (
            "Discovery and mobilization",
            submission + timedelta(days=1),
            submission + timedelta(days=14),
            "Kick-off deck, RACI matrix, and mobilization plan",
        ),
        (
            "Detailed solution design and sign-off",
            submission + timedelta(days=15),
            submission + timedelta(days=28),
            "Solution design document and stakeholder sign-off pack",
        ),
        (
            "Build and integration sprints",
            submission + timedelta(days=29),
            submission + timedelta(days=84),
            "Working increments, integration test evidence, and release notes",
        ),
        (
            "UAT and security validation",
            submission + timedelta(days=85),
            submission + timedelta(days=98),
            "UAT scripts, defect closure report, and security validation pack",
        ),
        (
            "Go-live and hypercare closeout",
            submission + timedelta(days=99),
            submission + timedelta(days=112),
            "Cutover checklist, hypercare runbook, and final acceptance sign-off",
        ),
    ]

    today = datetime.now(__import__("datetime").UTC).date()
    milestones: list[TimelineMilestone] = []
    for name, start, end, deliverables in milestone_defs:
        if end < today:
            status = "Completed"
        elif start <= today <= end:
            status = "In Progress"
        else:
            status = "Pending"
        milestones.append(
            TimelineMilestone(
                project_name=project,
                milestone=name,
                start_date=start.isoformat(),
                end_deadline=end.isoformat(),
                required_deliverables=deliverables,
                dependency=deliverables,
                status=status,
                priority=_priority_for_milestone(name),
            )
        )

    completion = milestones[-1].end_deadline
    return milestones, submission.isoformat(), completion


def ensure_bundle_timeline(bundle: OutputBundle) -> tuple[OutputBundle, bool]:
    """Rebuild strict timeline rows when missing from a stored or legacy bundle."""
    if bundle.timeline and bundle.submission_date:
        return bundle, False
    if not bundle.rfp:
        return bundle, False
    timeline, submission_date, expected_completion_date = build_strict_timeline(
        bundle.rfp, bundle.requirements or []
    )
    return (
        bundle.model_copy(
            update={
                "timeline": timeline,
                "submission_date": submission_date,
                "expected_completion_date": expected_completion_date,
            }
        ),
        True,
    )


def _resolve_submission_date(rfp: RFPDocument, requirements: list[Requirement]) -> date:
    candidates = [
        str(rfp.metadata.get("submission_date_hint", "")).strip(),
        str(rfp.metadata.get("deadline_hint", "")).strip(),
    ]
    for req in requirements:
        if str(req.type).lower() != "deadline":
            continue
        candidates.append(req.text)
    candidates.append(rfp.raw_text[:2500])

    for candidate in candidates:
        parsed = _parse_date(candidate)
        if parsed is not None:
            return parsed
    return rfp.upload_timestamp.date()


def _parse_date(text: str) -> date | None:
    if not text:
        return None

    raw = text.strip().replace(".", "/")
    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\s+\d{4}\b",
        r"\b(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\s+\d{1,2},\s+\d{4}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.I)
        if not match:
            continue
        nested = _parse_date(match.group(0))
        if nested is not None:
            return nested
    return None
