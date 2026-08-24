from src.schemas import (
    ActionItem,
    Evidence,
    MeetingAnalysis,
    Priority,
)
from src.validation import validate_evidence_grounding


def test_evidence_passes_when_quote_exists() -> None:
    transcript = "Priya will send the API specification by Friday."

    analysis = MeetingAnalysis(
        title="Test meeting",
        executive_summary="Priya agreed to provide the API specification by Friday.",
        action_items=[
            ActionItem(
                task="Send the API specification",
                owner="Priya",
                due_date="Friday",
                priority=Priority.HIGH,
                confidence=0.95,
                evidence=Evidence(
                    excerpt="Priya will send the API specification by Friday."
                ),
            )
        ],
    )

    assert validate_evidence_grounding(analysis, transcript) == []


def test_evidence_fails_when_quote_is_not_present() -> None:
    transcript = "Priya will send the API specification by Friday."

    analysis = MeetingAnalysis(
        title="Test meeting",
        executive_summary="A task was identified during the meeting.",
        action_items=[
            ActionItem(
                task="Create a dashboard",
                owner="Priya",
                due_date=None,
                priority=Priority.MEDIUM,
                confidence=0.80,
                evidence=Evidence(
                    excerpt="Priya will create a dashboard tomorrow."
                ),
            )
        ],
    )

    errors = validate_evidence_grounding(analysis, transcript)

    assert len(errors) == 1
    assert "Unsupported action item" in errors[0]