import unittest

from app.demo.personas import get_demo_personas
from app.services.strategy_engine import decide_next_move


class DemoPersonaTest(unittest.TestCase):
    def test_personas_share_a_starting_node_but_receive_distinct_paths(self) -> None:
        fast_confident, slow_anxious = get_demo_personas()

        fast_instruction = decide_next_move(fast_confident.learning_memory)
        slow_instruction = decide_next_move(slow_anxious.learning_memory)

        self.assertEqual(
            fast_confident.learning_memory.knowledge_profile.concept_graph_position.current_node,
            slow_anxious.learning_memory.knowledge_profile.concept_graph_position.current_node,
        )
        self.assertEqual(fast_instruction.action, "advance")
        self.assertEqual(fast_instruction.tone, "challenging")
        self.assertEqual(fast_instruction.chunk_size, "large")
        self.assertEqual(slow_instruction.action, "confidence_building_easy_win")
        self.assertEqual(slow_instruction.tone, "supportive")
        self.assertEqual(slow_instruction.chunk_size, "small")
