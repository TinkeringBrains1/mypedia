"""Reflection Mode cadence and Learning Memory ai_desc writes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.schemas.learning_memory import LearningMemory
from app.services.educator import ReflectionSummary


REFLECTION_INTERVAL_CHECKS = 3


class ReflectionEducator(Protocol):
    def regenerate_ai_description(self, memory: LearningMemory) -> ReflectionSummary: ...


class ReflectionResult(BaseModel):
    """The copied canonical memory and whether this turn refreshed ai_desc."""

    model_config = ConfigDict(frozen=True)

    learning_memory: LearningMemory
    regenerated: bool


def is_reflection_due(memory: LearningMemory) -> bool:
    """Run every three recorded outcomes without a parallel turn-state model."""
    check_count = len(memory.knowledge_profile.mastery_history)
    last_reflection_count = memory.session_meta.last_reflection_mastery_count
    return check_count - last_reflection_count >= REFLECTION_INTERVAL_CHECKS


def refresh_ai_description_if_due(
    memory: LearningMemory, educator: ReflectionEducator
) -> ReflectionResult:
    """Regenerate ai_desc on the deterministic cadence and preserve all other state."""
    updated_memory = memory.model_copy(deep=True)
    if not is_reflection_due(updated_memory):
        return ReflectionResult(learning_memory=updated_memory, regenerated=False)

    reflection = educator.regenerate_ai_description(updated_memory)
    updated_memory.ai_desc.summary = reflection.summary
    updated_memory.session_meta.lesson_pulse.ai_conclusion = reflection.lesson_conclusion
    updated_memory.ai_desc.generated_at = datetime.now(timezone.utc)
    updated_memory.session_meta.last_reflection_mastery_count = len(
        updated_memory.knowledge_profile.mastery_history
    )
    return ReflectionResult(learning_memory=updated_memory, regenerated=True)
