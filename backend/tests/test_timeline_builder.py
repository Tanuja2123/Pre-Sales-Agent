from __future__ import annotations

from datetime import UTC, datetime

from models.pipeline import OutputBundle
from models.rfp import MAFLevel, Requirement, RequirementType, RFPDocument
from services.timeline_builder import build_strict_timeline, ensure_bundle_timeline


def _sample_rfp() -> RFPDocument:
    return RFPDocument(
        document_id="doc-1",
        filename="client-rfp.txt",
        upload_timestamp=datetime(2026, 5, 1, tzinfo=UTC),
        raw_text="Submission deadline: 15 June 2026",
        chunks=[],
        sections={},
        metadata={"submission_date_hint": "15/06/2026"},
    )


def test_build_strict_timeline_returns_six_milestones() -> None:
    rfp = _sample_rfp()
    reqs = [
        Requirement(
            requirement_id="REQ-1",
            type=RequirementType.DEADLINE,
            priority="mandatory",
            maf_classification=MAFLevel.MINIMUM,
            source_section="s1",
            text="Proposals due 15 June 2026",
        )
    ]
    timeline, submission, completion = build_strict_timeline(rfp, reqs)
    assert len(timeline) == 6
    assert submission == "2026-06-15"
    assert completion == timeline[-1].end_deadline
    assert timeline[0].milestone == "RFP submission baseline confirmed"


def test_ensure_bundle_timeline_backfills_missing_rows() -> None:
    rfp = _sample_rfp()
    bundle = OutputBundle(
        run_id="run-1",
        rfp=rfp,
        requirements=[],
        timeline=[],
        submission_date=None,
        expected_completion_date=None,
    )
    updated, changed = ensure_bundle_timeline(bundle)
    assert changed is True
    assert len(updated.timeline) == 6
    assert updated.submission_date == "2026-06-15"
    assert updated.expected_completion_date


def test_ensure_bundle_timeline_noop_when_present() -> None:
    rfp = _sample_rfp()
    timeline, submission, completion = build_strict_timeline(rfp, [])
    bundle = OutputBundle(
        run_id="run-2",
        rfp=rfp,
        timeline=timeline,
        submission_date=submission,
        expected_completion_date=completion,
    )
    same, changed = ensure_bundle_timeline(bundle)
    assert changed is False
    assert same.timeline == timeline
