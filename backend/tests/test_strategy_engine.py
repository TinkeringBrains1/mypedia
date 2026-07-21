import unittest

from app.schemas.learning_memory import LearningMemory
from app.services.strategy_engine import decide_next_move


def memory_for_strategy() -> LearningMemory:
    return LearningMemory.start_for_student(
        student_id="stu_0231",
        subject_id="math_algebra",
        first_concept_node="linear_equations_one_var",
    )


class StrategyEngineTest(unittest.TestCase):
    def test_high_stress_has_highest_priority(self) -> None:
        memory = memory_for_strategy()
        memory.affective_profile.inferred.stress_signal = 0.8
        memory.affective_profile.mismatch_flag = True

        instruction = decide_next_move(memory)

        self.assertEqual(instruction.action, "confidence_building_easy_win")
        self.assertEqual(instruction.rule_id, "high_stress_easy_win")
        self.assertEqual(instruction.chunk_size, "small")

    def test_mismatch_lowers_stakes_and_hides_score(self) -> None:
        memory = memory_for_strategy()
        memory.affective_profile.mismatch_flag = True

        instruction = decide_next_move(memory)

        self.assertEqual(instruction.rule_id, "affective_mismatch_lower_stakes")
        self.assertFalse(instruction.visible_score)

    def test_struggling_nodes_are_rechecked_only_once(self) -> None:
        memory = memory_for_strategy()
        position = memory.knowledge_profile.concept_graph_position
        position.struggling_nodes = ["fractions_in_equations", "negative_numbers"]

        first_instruction = decide_next_move(memory)
        memory.session_meta.last_orchestrator_action = first_instruction.action_key
        second_instruction = decide_next_move(memory)

        self.assertEqual(first_instruction.action, "reteach")
        self.assertEqual(first_instruction.node, "fractions_in_equations")
        self.assertTrue(first_instruction.requires_low_stakes_check)
        self.assertEqual(second_instruction.rule_id, "default_continue")

    def test_high_retry_reduces_chunk_size_and_adds_examples(self) -> None:
        memory = memory_for_strategy()
        memory.cognitive_pacing_profile.retry_rate = 0.41
        memory.cognitive_pacing_profile.preferred_chunk_size = "medium"

        instruction = decide_next_move(memory)

        self.assertEqual(instruction.chunk_size, "small")
        self.assertEqual(instruction.worked_example_density, "high")

    def test_high_mastery_and_low_stress_advances_with_a_stretch_problem(self) -> None:
        memory = memory_for_strategy()
        memory.knowledge_profile.mastery_history = [0.76, 0.9]
        memory.affective_profile.inferred.stress_signal = 0.1
        memory.knowledge_profile.concept_graph_position.current_node = "one_step_equations"

        instruction = decide_next_move(memory)

        self.assertEqual(instruction.rule_id, "mastery_stress_readiness_advance")
        self.assertEqual(instruction.node, "two_step_equations")
        self.assertTrue(instruction.offer_stretch_problem)

    def test_moderate_readiness_now_advances_through_the_mvp_graph(self) -> None:
        memory = memory_for_strategy()
        memory.knowledge_profile.concept_graph_position.current_node = "one_step_equations"
        memory.knowledge_profile.mastery_history = [0.65, 0.65]
        memory.affective_profile.inferred.stress_signal = 0.1

        self.assertEqual(decide_next_move(memory).rule_id, "mastery_stress_readiness_advance")

    def test_avoidant_low_engagement_shortens_session_and_uses_interests(self) -> None:
        memory = memory_for_strategy()
        memory.affective_profile.inferred.goal_orientation = "avoidant"
        memory.affective_profile.inferred.engagement_score = 0.34
        memory.interest_context.tags = ["cricket"]

        instruction = decide_next_move(memory)

        self.assertEqual(instruction.rule_id, "avoidant_low_engagement_shorten_session")
        self.assertEqual(instruction.session_length, "short")
        self.assertEqual(instruction.example_interest_tags, ["cricket"])

    def test_default_continues_the_current_concept(self) -> None:
        instruction = decide_next_move(memory_for_strategy())

        self.assertEqual(instruction.action, "continue")
        self.assertEqual(instruction.rule_id, "default_continue")
