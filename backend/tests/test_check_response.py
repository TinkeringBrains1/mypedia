import unittest

from app.schemas.learning_memory import LearningMemory
from app.services.check_response import apply_check_response
from app.services.educator import (
    CheckResponseInterpretation,
    CheckResponseSubmission,
    InterpretedCheckAnswer,
    StudentCheckAnswer,
)
from app.services.strategy_engine import StrategyInstruction


def instruction() -> StrategyInstruction:
    return StrategyInstruction(
        action="continue",
        node="two_step_equations",
        chunk_size="medium",
        tone="neutral",
        rule_id="default_continue",
        reason="Continue the current concept.",
    )


def memory() -> LearningMemory:
    memory = LearningMemory.start_for_student(
        student_id="stu_0231",
        subject_id="math_algebra",
        first_concept_node="two_step_equations",
    )
    memory.knowledge_profile.mastery_score = 0.3
    memory.knowledge_profile.mastery_history = [0.2]
    memory.affective_profile.inferred.stress_signal = 0.4
    return memory


class CheckResponseUpdateTest(unittest.TestCase):
    def test_high_accuracy_updates_memory_deterministically(self) -> None:
        submission = CheckResponseSubmission(
            answers=[
                StudentCheckAnswer(answer="x = 5", response_latency_sec=12),
                StudentCheckAnswer(answer="x = 3", response_latency_sec=8),
            ]
        )
        interpretation = CheckResponseInterpretation(
            answers=[
                InterpretedCheckAnswer(question_index=0, is_correct=True),
                InterpretedCheckAnswer(question_index=1, is_correct=True),
            ],
            affect_signal="calm",
        )

        result = apply_check_response(memory(), instruction(), submission, interpretation)
        updated = result.learning_memory

        self.assertEqual(result.turn_accuracy, 1.0)
        self.assertAlmostEqual(updated.knowledge_profile.mastery_score, 0.51)
        self.assertEqual(updated.knowledge_profile.mastery_history, [0.2, 1.0])
        self.assertIn("two_step_equations", updated.knowledge_profile.concept_graph_position.mastered_nodes)
        self.assertAlmostEqual(updated.affective_profile.inferred.stress_signal, 0.3)
        self.assertAlmostEqual(updated.affective_profile.inferred.stress_history[0], 0.3)
        self.assertAlmostEqual(updated.affective_profile.inferred.engagement_score, 0.6)
        self.assertEqual(updated.cognitive_pacing_profile.preferred_chunk_size, "large")
        self.assertEqual(updated.session_meta.last_orchestrator_action, "continue:two_step_equations")
        self.assertEqual(updated.session_meta.recent_student_responses, ["x = 5", "x = 3"])
        self.assertEqual([(item.question_no, item.topic, item.accuracy, item.time_sec) for item in updated.session_meta.lesson_question_history], [(1, "two_step_equations", 1.0, 12.0), (2, "two_step_equations", 1.0, 8.0)])
        self.assertEqual(updated.session_meta.lesson_pulse.recent_accuracy, 1.0)

    def test_low_accuracy_and_frustration_adds_stress_and_marks_struggle(self) -> None:
        submission = CheckResponseSubmission(
            answers=[
                StudentCheckAnswer(answer="I do not know", response_latency_sec=30, used_hint=True),
                StudentCheckAnswer(
                    answer="I am stuck", response_latency_sec=40, attempt_count=2
                ),
            ]
        )
        interpretation = CheckResponseInterpretation(
            answers=[
                InterpretedCheckAnswer(question_index=0, is_correct=False),
                InterpretedCheckAnswer(question_index=1, is_correct=False),
            ],
            affect_signal="frustrated",
        )

        updated = apply_check_response(memory(), instruction(), submission, interpretation).learning_memory

        self.assertIn("two_step_equations", updated.knowledge_profile.concept_graph_position.struggling_nodes)
        self.assertAlmostEqual(updated.affective_profile.inferred.stress_signal, 0.65)
        self.assertEqual(updated.affective_profile.inferred.stress_history, [0.65])
        self.assertAlmostEqual(updated.affective_profile.inferred.engagement_score, 0.4)
        self.assertEqual(updated.cognitive_pacing_profile.preferred_chunk_size, "small")
