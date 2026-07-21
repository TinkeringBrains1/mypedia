import unittest

from app.content.math_algebra import prerequisite_for_math_algebra_node
from app.schemas.learning_memory import LearningMemory
from app.services.check_response import apply_voice_affect
from app.services.educator import PrerequisiteInterpretation, PrerequisiteSubmission
from app.services.prerequisite import apply_prerequisite_result
from app.services.strategy_engine import decide_next_move


class PrerequisiteFlowTest(unittest.TestCase):
    def test_first_node_has_no_prerequisite(self) -> None:
        self.assertIsNone(prerequisite_for_math_algebra_node("negative_numbers"))

    def test_gap_resumes_the_original_lesson_slowly_after_one_recheck(self) -> None:
        memory = LearningMemory.start_for_student("stu_pre", "math_algebra", "two_step_equations")
        updated = apply_prerequisite_result(
            memory,
            "two_step_equations",
            "one_step_equations",
            PrerequisiteInterpretation(
                multiple_choice_correct=False,
                text_answer_demonstrates_understanding=False,
            ),
            PrerequisiteSubmission(
                multiple_choice_answer="I am unsure.", text_answer="I would try to subtract first."
            ),
        )
        self.assertEqual(decide_next_move(updated).node, "one_step_equations")
        updated.session_meta.last_orchestrator_action = "reteach:one_step_equations"
        resumed = decide_next_move(updated)
        self.assertEqual(resumed.node, "two_step_equations")
        self.assertEqual(resumed.chunk_size, "small")
        self.assertEqual(resumed.worked_example_density, "high")
        self.assertEqual(updated.session_meta.recent_student_responses[-1], "I would try to subtract first.")

    def test_voice_affect_is_bounded_and_keeps_no_transcript(self) -> None:
        memory = LearningMemory.start_for_student("stu_voice", "math_algebra", "negative_numbers")
        updated = apply_voice_affect(memory, "confident")
        self.assertEqual(updated.affective_profile.voice_affect, "confident")
        self.assertEqual(updated.affective_profile.voice_affect_history, ["confident"])
        self.assertEqual(updated.affective_profile.inferred.stress_history, [0.0])
