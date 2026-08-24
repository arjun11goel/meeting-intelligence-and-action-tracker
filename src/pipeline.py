"""MeetingMind workflow orchestration."""

from src.extraction import extract_meeting_analysis
from src.schemas import MeetingAnalysis


def analyze_meeting(transcript: str) -> MeetingAnalysis:
    """Run the complete transcript-to-intelligence workflow."""
    return extract_meeting_analysis(transcript)