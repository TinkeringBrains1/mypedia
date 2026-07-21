"""Two contrasting Learning Memory snapshots for the MyPedia demo."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.learning_memory import LearningMemory


class DemoPersona(BaseModel):
    """A named demonstration learner backed by canonical Learning Memory."""

    model_config = ConfigDict(frozen=True)

    name: str
    scenario: str
    learning_memory: LearningMemory


def _fast_confident() -> DemoPersona:
    memory = LearningMemory.start_for_student(
        student_id="demo_fast_confident",
        subject_id="math_algebra",
        first_concept_node="two_step_equations",
    )
    memory.knowledge_profile.mastery_score = 0.86
    memory.knowledge_profile.mastery_history = [0.84, 0.92]
    memory.knowledge_profile.concept_graph_position.mastered_nodes = [
        "negative_numbers",
        "distributive_property",
        "combining_like_terms",
        "one_step_equations",
    ]
    memory.cognitive_pacing_profile.avg_response_latency_sec = 9.0
    memory.cognitive_pacing_profile.preferred_chunk_size = "large"
    memory.cognitive_pacing_profile.scaffold_level = "low"
    memory.affective_profile.inferred.engagement_score = 0.86
    memory.affective_profile.inferred.stress_signal = 0.10
    memory.affective_profile.inferred.stress_history = [0.16, 0.12, 0.10]
    memory.affective_profile.inferred.self_efficacy_score = 0.88
    memory.interest_context.tags = ["cricket"]
    memory.ai_desc.summary = (
        "Moves quickly through algebra steps and enjoys an extra challenge. "
        "Benefits from concise prompts that invite explanation."
    )
    return DemoPersona(
        name="Aarav — fast & confident",
        scenario="Strong recent checks and low stress at the same starting concept.",
        learning_memory=memory,
    )


def _slow_anxious() -> DemoPersona:
    memory = LearningMemory.start_for_student(
        student_id="demo_slow_anxious",
        subject_id="math_algebra",
        first_concept_node="two_step_equations",
    )
    memory.knowledge_profile.mastery_score = 0.38
    memory.knowledge_profile.mastery_history = [0.35, 0.40]
    memory.cognitive_pacing_profile.avg_response_latency_sec = 34.0
    memory.cognitive_pacing_profile.hint_usage_rate = 0.50
    memory.cognitive_pacing_profile.retry_rate = 0.50
    memory.cognitive_pacing_profile.preferred_chunk_size = "small"
    memory.cognitive_pacing_profile.scaffold_level = "high"
    memory.affective_profile.self_reported.last_checkin = "anxious"
    memory.affective_profile.self_reported.checkin_history = ["anxious"]
    memory.affective_profile.inferred.engagement_score = 0.32
    memory.affective_profile.inferred.stress_signal = 0.80
    memory.affective_profile.inferred.stress_history = [0.64, 0.72, 0.80]
    memory.affective_profile.inferred.self_efficacy_score = 0.30
    memory.interest_context.tags = ["drawing"]
    memory.ai_desc.summary = (
        "Needs reassurance before taking on multi-step equations. "
        "Short, worked examples reduce pressure and help rebuild confidence."
    )
    return DemoPersona(
        name="Meera — slow & anxious",
        scenario="High stress and slower pacing at the same starting concept.",
        learning_memory=memory,
    )


def get_demo_personas() -> tuple[DemoPersona, DemoPersona]:
    """Return fresh canonical Memory snapshots for a reliable repeatable demo."""
    return (_fast_confident(), _slow_anxious())
