"""Validation utilities for evidence-grounded meeting intelligence."""

import re

from src.schemas import MeetingAnalysis


def _normalize_text(text: str) -> str:
    """Normalize whitespace and casing for tolerant evidence matching."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_evidence_grounding(
    analysis: MeetingAnalysis,
    transcript: str,
) -> list[str]:
    """
    Return validation errors for facts whose evidence is absent from a transcript.

    An empty list means every extracted action, decision, and question
    is supported by a source quote in the input meeting transcript.
    """
    normalized_transcript = _normalize_text(transcript)
    errors: list[str] = []

    evidence_items = [
        ("action item", item.task, item.evidence.excerpt)
        for item in analysis.action_items
    ]
    evidence_items.extend(
        ("decision", item.decision, item.evidence.excerpt)
        for item in analysis.decisions
    )
    evidence_items.extend(
        ("open question", item.question, item.evidence.excerpt)
        for item in analysis.open_questions
    )

    for item_type, label, excerpt in evidence_items:
        if _normalize_text(excerpt) not in normalized_transcript:
            errors.append(
                f"Unsupported {item_type}: '{label}'. "
                "Its evidence quote was not found in the transcript."
            )

    return errors