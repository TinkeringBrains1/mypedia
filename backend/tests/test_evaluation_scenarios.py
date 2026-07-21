"""Scripted MVP journeys that guard the visible adaptive behaviours."""

import unittest

from app.schemas.learning_memory import LearningMemory
from app.services.strategy_engine import decide_next_move


class EvaluationScenariosTest(unittest.TestCase):
    def test_confident_ready_learner_advances(self) -> None:
        memory = LearningMemory.start_for_student("confident", "math_algebra", "one_step_equations")
        memory.knowledge_profile.mastery_history = [.9, .9]
        memory.affective_profile.inferred.stress_signal = .1
        self.assertEqual(decide_next_move(memory).action, "advance")

    def test_struggling_learner_gets_one_small_reteach(self) -> None:
        memory = LearningMemory.start_for_student("struggling", "math_algebra", "two_step_equations")
        memory.knowledge_profile.concept_graph_position.struggling_nodes = ["one_step_equations"]
        instruction = decide_next_move(memory)
        self.assertEqual((instruction.action, instruction.chunk_size), ("reteach", "small"))

    def test_voice_request_adds_worked_example_support(self) -> None:
        memory = LearningMemory.start_for_student("voice", "math_algebra", "one_step_equations")
        memory.session_meta.voice_learning_request = "worked_example"
        instruction = decide_next_move(memory)
        self.assertEqual((instruction.chunk_size, instruction.worked_example_density), ("small", "high"))

    def test_declining_accuracy_gets_extra_topic_support(self) -> None:
        memory = LearningMemory.start_for_student("declining", "math_algebra", "one_step_equations")
        memory.session_meta.lesson_pulse.accuracy_trend = "declining"
        memory.session_meta.lesson_pulse.support_topic = "one_step_equations"
        instruction = decide_next_move(memory)
        self.assertEqual((instruction.rule_id, instruction.chunk_size), ("declining_accuracy_extra_support", "small"))
