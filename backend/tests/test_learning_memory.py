import unittest

from app.schemas.learning_memory import LearningMemory


class LearningMemoryTest(unittest.TestCase):
    def test_new_memory_has_neutral_mvp_defaults(self) -> None:
        memory = LearningMemory.start_for_student(
            student_id="stu_0231",
            subject_id="math_algebra",
            first_concept_node="linear_equations_one_var",
        )

        self.assertEqual(memory.knowledge_profile.mastery_score, 0.0)
        self.assertEqual(memory.affective_profile.inferred.engagement_score, 0.5)
        self.assertEqual(memory.affective_profile.inferred.stress_signal, 0.0)
        self.assertEqual(memory.affective_profile.inferred.stress_history, [])
        self.assertEqual(memory.cognitive_pacing_profile.preferred_chunk_size, "medium")
        self.assertEqual(
            memory.knowledge_profile.concept_graph_position.not_yet_attempted,
            ["linear_equations_one_var"],
        )
