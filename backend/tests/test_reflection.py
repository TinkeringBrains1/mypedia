import unittest

from app.schemas.learning_memory import LearningMemory
from app.services.educator import ReflectionSummary
from app.services.reflection import (
    REFLECTION_INTERVAL_CHECKS,
    is_reflection_due,
    refresh_ai_description_if_due,
)


class FakeReflectionEducator:
    def __init__(self) -> None:
        self.calls = 0

    def regenerate_ai_description(self, memory: LearningMemory) -> ReflectionSummary:
        self.calls += 1
        return ReflectionSummary(
            summary="Working steadily and ready for a supported next step."
        )


def memory_with_history(history: list[float]) -> LearningMemory:
    memory = LearningMemory.start_for_student(
        student_id="stu_0231",
        subject_id="math_algebra",
        first_concept_node="two_step_equations",
    )
    memory.knowledge_profile.mastery_history = history
    return memory


class ReflectionModeTest(unittest.TestCase):
    def test_reflection_is_due_every_three_check_outcomes(self) -> None:
        self.assertTrue(is_reflection_due(memory_with_history([0.3] * REFLECTION_INTERVAL_CHECKS)))
        self.assertFalse(is_reflection_due(memory_with_history([0.3, 0.6])))

    def test_due_reflection_writes_only_ai_description(self) -> None:
        memory = memory_with_history([0.3, 0.6, 1.0])
        educator = FakeReflectionEducator()

        result = refresh_ai_description_if_due(memory, educator)

        self.assertTrue(result.regenerated)
        self.assertEqual(educator.calls, 1)
        self.assertEqual(
            result.learning_memory.ai_desc.summary,
            "Working steadily and ready for a supported next step.",
        )
        self.assertIsNotNone(result.learning_memory.ai_desc.generated_at)
        self.assertEqual(
            result.learning_memory.session_meta.last_reflection_mastery_count,
            3,
        )
        self.assertEqual(memory.ai_desc.summary, "")

        repeated_result = refresh_ai_description_if_due(
            result.learning_memory, educator
        )
        self.assertFalse(repeated_result.regenerated)
        self.assertEqual(educator.calls, 1)

    def test_not_due_reflection_does_not_call_gemini(self) -> None:
        educator = FakeReflectionEducator()

        result = refresh_ai_description_if_due(memory_with_history([0.3, 0.6]), educator)

        self.assertFalse(result.regenerated)
        self.assertEqual(educator.calls, 0)
