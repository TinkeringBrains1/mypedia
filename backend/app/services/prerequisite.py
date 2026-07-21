"""Deterministic Learning Memory writes for pre-lesson prerequisite checks."""

from __future__ import annotations

from app.schemas.learning_memory import LearningMemory
from app.services.educator import PrerequisiteInterpretation
from app.services.educator import PrerequisiteSubmission


def apply_prerequisite_result(
    memory: LearningMemory,
    lesson_node: str,
    prerequisite_node: str,
    interpretation: PrerequisiteInterpretation,
    submission: PrerequisiteSubmission,
) -> LearningMemory:
    """Record a pre-lesson check without changing mastery or history."""
    updated = memory.model_copy(deep=True)
    session = updated.session_meta
    session.prerequisite_checked_for_node = lesson_node
    session.recent_student_responses = (
        session.recent_student_responses
        + [submission.multiple_choice_answer.strip()[:180], submission.text_answer.strip().replace("\n", " ")[:360]]
    )[-4:]

    if interpretation.demonstrates_understanding:
        return updated

    position = updated.knowledge_profile.concept_graph_position
    position.current_node = prerequisite_node
    if prerequisite_node not in position.struggling_nodes:
        position.struggling_nodes.append(prerequisite_node)
    session.pending_lesson_node = lesson_node
    session.last_orchestrator_action = None
    updated.cognitive_pacing_profile.scaffold_level = "high"
    updated.cognitive_pacing_profile.preferred_chunk_size = "small"
    return updated
