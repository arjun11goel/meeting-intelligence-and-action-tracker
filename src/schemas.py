"""Validated data models for MeetingMind's AI workflow."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    """Priority assigned to an action item."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSPECIFIED = "unspecified"


class ActionStatus(str, Enum):
    """Lifecycle status for an action item."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Evidence(BaseModel):
    """Transcript evidence supporting an extracted fact."""

    model_config = ConfigDict(extra="forbid")

    excerpt: str = Field(
        min_length=5,
        description="Exact supporting quote from the transcript.",
    )
    timestamp_seconds: int | None = Field(
        default=None,
        ge=0,
        description="Start time of the evidence in seconds, if available.",
    )


class ActionItem(BaseModel):
    """A task extracted from a meeting transcript."""

    model_config = ConfigDict(extra="forbid")

    task: str = Field(
        min_length=3,
        description="Clear, actionable task written as a verb phrase.",
    )
    owner: str | None = Field(
        default=None,
        description="Person responsible for the task, if explicitly stated.",
    )
    due_date: str | None = Field(
        default=None,
        description="Deadline exactly as stated or normalized to YYYY-MM-DD.",
    )
    priority: Priority = Priority.UNSPECIFIED
    status: ActionStatus = ActionStatus.OPEN
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Evidence


class Decision(BaseModel):
    """A decision made during a meeting."""

    model_config = ConfigDict(extra="forbid")

    decision: str = Field(min_length=3)
    owner: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Evidence


class OpenQuestion(BaseModel):
    """An unresolved question or follow-up required after a meeting."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3)
    owner: str | None = None
    evidence: Evidence


class MeetingAnalysis(BaseModel):
    """Complete structured intelligence extracted from one meeting."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3)
    executive_summary: str = Field(min_length=20)
    key_topics: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)