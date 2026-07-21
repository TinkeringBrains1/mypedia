import unittest

from app.content.math_algebra import DiagnosticOption, DiagnosticQuestion
from app.services.diagnostic import DiagnosticFlowError, DiagnosticResponse, DiagnosticSubmission, seed_learning_memory


QUESTIONS = [
    DiagnosticQuestion(id="negative_numbers", concept_node="negative_numbers", prompt="A", options=[DiagnosticOption(id="a", text="yes"), DiagnosticOption(id="b", text="no"), DiagnosticOption(id="c", text="maybe")], correct_option_id="a"),
    DiagnosticQuestion(id="one_step_equations", concept_node="one_step_equations", prompt="B", options=[DiagnosticOption(id="a", text="yes"), DiagnosticOption(id="b", text="no"), DiagnosticOption(id="c", text="maybe")], correct_option_id="b"),
]

def response(question: DiagnosticQuestion, option: str) -> DiagnosticResponse:
    return DiagnosticResponse(question_id=question.id, selected_option_id=option, response_latency_sec=12)

class DiagnosticFlowTest(unittest.TestCase):
    def test_two_answers_seed_learning_memory_deterministically(self) -> None:
        result = seed_learning_memory("stu_0231", DiagnosticSubmission(responses=[response(QUESTIONS[0], "a"), response(QUESTIONS[1], "a")], affective_checkin="anxious"), QUESTIONS)
        memory = result.learning_memory
        self.assertEqual(memory.knowledge_profile.concept_graph_position.mastered_nodes, ["negative_numbers"])
        self.assertEqual(memory.knowledge_profile.concept_graph_position.struggling_nodes, ["one_step_equations"])
        self.assertEqual(memory.knowledge_profile.mastery_score, .5)
        self.assertEqual(memory.cognitive_pacing_profile.preferred_chunk_size, "large")

    def test_rejects_anything_other_than_the_two_session_questions(self) -> None:
        with self.assertRaises(DiagnosticFlowError):
            seed_learning_memory("stu", DiagnosticSubmission(responses=[response(QUESTIONS[0], "a"), response(QUESTIONS[0], "a")], affective_checkin="confident"), QUESTIONS)
