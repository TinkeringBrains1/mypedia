"""The canonical persistent state for a MyPedia student.

Learning Memory deliberately contains the complete student model. Other
components read and update this object rather than maintaining their own state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConceptGraphPosition(BaseModel):
    current_node: str
    mastered_nodes: list[str] = Field(default_factory=list)
    struggling_nodes: list[str] = Field(default_factory=list)
    not_yet_attempted: list[str] = Field(default_factory=list)


class KnowledgeProfile(BaseModel):
    concept_graph_position: ConceptGraphPosition
    mastery_score: float = Field(ge=0.0, le=1.0)
    mastery_history: list[float] = Field(default_factory=list)


class CognitivePacingProfile(BaseModel):
    avg_response_latency_sec: float | None = Field(default=None, ge=0.0)
    hint_usage_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    retry_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    scaffold_level: Literal["low", "medium", "high"] = "medium"
    preferred_chunk_size: Literal["small", "medium", "large"] = "medium"


class SelfReportedAffect(BaseModel):
    last_checkin: str | None = None
    checkin_history: list[str] = Field(default_factory=list)


class InferredAffect(BaseModel):
    engagement_score: float = Field(default=0.5, ge=0.0, le=1.0)
    stress_signal: float = Field(default=0.0, ge=0.0, le=1.0)
    stress_history: list[float] = Field(default_factory=list)
    self_efficacy_score: float = Field(default=0.5, ge=0.0, le=1.0)
    goal_orientation: Literal["mastery", "avoidant"] = "mastery"
    mindset_signal: Literal["growth", "fixed"] = "growth"


class AffectiveProfile(BaseModel):
    self_reported: SelfReportedAffect = Field(default_factory=SelfReportedAffect)
    inferred: InferredAffect = Field(default_factory=InferredAffect)
    mismatch_flag: bool = False
    voice_affect: Literal["anxious", "neutral", "confident"] | None = None
    voice_affect_history: list[Literal["anxious", "neutral", "confident"]] = Field(
        default_factory=list
    )


class InterestContext(BaseModel):
    tags: list[str] = Field(default_factory=list)
    source: str = "onboarding_survey"


class AIDescription(BaseModel):
    summary: str = ""
    generated_at: datetime | None = None


class LessonQuestionOutcome(BaseModel):
    question_no: int = Field(ge=1)
    topic: str
    accuracy: float = Field(ge=0.0, le=1.0)
    time_sec: float = Field(ge=0.0)


class HelpSeekingEvent(BaseModel):
    kind: Literal["voice_doubt", "slower", "worked_example", "replay"]
    topic: str


class LessonPulse(BaseModel):
    recent_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    accuracy_trend: Literal["improving", "steady", "declining"] = "steady"
    pace_trend: Literal["faster", "steady", "slower"] = "steady"
    help_seeking_count: int = Field(default=0, ge=0)
    support_topic: str | None = None
    ai_conclusion: str = ""


class StudentSignal(BaseModel):
    kind: Literal["inactivity", "struggling", "challenge"]
    topic: str


class PausedSession(BaseModel):
    """A compact, resumable checkpoint shown on the student dashboard."""

    paused_at: datetime
    topic: str
    mastery_score: float = Field(ge=0.0, le=1.0)
    engagement_score: float = Field(ge=0.0, le=1.0)
    progress_summary: str


class SessionMeta(BaseModel):
    total_sessions: int = Field(default=0, ge=0)
    total_time_min: int = Field(default=0, ge=0)
    last_orchestrator_action: str | None = None
    last_reflection_mastery_count: int = Field(default=0, ge=0)
    pending_lesson_node: str | None = None
    prerequisite_checked_for_node: str | None = None
    # Compact, session-scoped context for the next Educator turn. This remains
    # part of canonical Learning Memory rather than becoming a chat store.
    recent_student_responses: list[str] = Field(default_factory=list, max_length=4)
    voice_learning_request: Literal["slower", "worked_example", "ready", "none"] = "none"
    lesson_question_history: list[LessonQuestionOutcome] = Field(default_factory=list, max_length=30)
    help_seeking_events: list[HelpSeekingEvent] = Field(default_factory=list, max_length=30)
    inactivity_events: int = Field(default=0, ge=0)
    lesson_pulse: LessonPulse = Field(default_factory=LessonPulse)
    student_signals: list[StudentSignal] = Field(default_factory=list, max_length=30)
    paused_sessions: list[PausedSession] = Field(default_factory=list, max_length=12)


class LearningMemory(BaseModel):
    """Single source of truth for a student's learning state.

    This MVP intentionally uses one global memory per student. ``subject_id``
    is retained on that object to make a future per-subject migration possible
    without changing the memory shape.
    """

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    knowledge_profile: KnowledgeProfile
    cognitive_pacing_profile: CognitivePacingProfile = Field(
        default_factory=CognitivePacingProfile
    )
    affective_profile: AffectiveProfile = Field(default_factory=AffectiveProfile)
    interest_context: InterestContext = Field(default_factory=InterestContext)
    ai_desc: AIDescription = Field(default_factory=AIDescription)
    session_meta: SessionMeta = Field(default_factory=SessionMeta)

    @classmethod
    def start_for_student(
        cls, student_id: str, subject_id: str, first_concept_node: str
    ) -> "LearningMemory":
        """Create the neutral state used before diagnostic assessment."""
        return cls(
            student_id=student_id,
            subject_id=subject_id,
            knowledge_profile=KnowledgeProfile(
                concept_graph_position=ConceptGraphPosition(
                    current_node=first_concept_node,
                    not_yet_attempted=[first_concept_node],
                ),
                mastery_score=0.0,
            ),
        )
