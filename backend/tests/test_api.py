import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, get_educator, get_repository
from app.schemas.learning_memory import LearningMemory
from app.services.educator import (
    CheckResponseInterpretation,
    CheckResponseSubmission,
    InterpretedCheckAnswer,
    ReflectionSummary,
    TeachingTurn,
    PrerequisiteCheck,
    PrerequisiteInterpretation,
    PrerequisiteMultipleChoice,
    PrerequisiteSubmission,
    VoiceDoubtResponse,
)
from app.content.math_algebra import DiagnosticOption, DiagnosticQuestion


class InMemoryRepository:
    def __init__(self) -> None:
        self.memories: dict[str, LearningMemory] = {}

    def get_relevant_state(self, student_id: str, subject_id: str) -> LearningMemory:
        memory = self.memories[student_id]
        if memory.subject_id != subject_id:
            raise KeyError(student_id)
        return memory

    def save(self, memory: LearningMemory) -> None:
        self.memories[memory.student_id] = memory


class FakeEducator:
    prerequisite_understanding = True
    def generate_diagnostic_questions(self, nodes: list[str], question_ids: list[str] | None = None, _prior_response: str | None = None) -> list[DiagnosticQuestion]:
        return [
            DiagnosticQuestion(id=(question_ids or nodes)[index], concept_node=node, prompt=f"Question for {node}", options=[DiagnosticOption(id="a", text="Correct"), DiagnosticOption(id="b", text="Not correct"), DiagnosticOption(id="c", text="Also not correct")], correct_option_id="a")
            for index, node in enumerate(nodes)
        ]
    def generate_teaching_turn(self, memory: LearningMemory, _instruction: object, alternate_from: str | None = None) -> TeachingTurn:
        return TeachingTurn(
            teaching_content="Undo the addition before dividing.",
            check_questions=["What is 10 - 4?", "What is 6 divided by 2?"],
        )

    def interpret_check_responses(
        self, _turn: TeachingTurn, submission: CheckResponseSubmission
    ) -> CheckResponseInterpretation:
        return CheckResponseInterpretation(
            answers=[
                InterpretedCheckAnswer(question_index=index, is_correct=True)
                for index in range(len(submission.answers))
            ],
            affect_signal="calm",
        )

    def regenerate_ai_description(self, _memory: LearningMemory) -> ReflectionSummary:
        return ReflectionSummary(summary="A concise current learning picture.")

    def generate_prerequisite_check(
        self, _memory: LearningMemory, _lesson_node: str, prerequisite_node: str
    ) -> PrerequisiteCheck:
        return PrerequisiteCheck(
            prerequisite_node=prerequisite_node,
            multiple_choice=PrerequisiteMultipleChoice(
                prompt="What does x = 4 mean?", options=["x is 4", "x is 0", "x is 8"]
            ),
            text_prompt="Explain what you would do first.",
        )

    def interpret_prerequisite_check(
        self, _check: PrerequisiteCheck, _submission: PrerequisiteSubmission
    ) -> PrerequisiteInterpretation:
        return PrerequisiteInterpretation(
            multiple_choice_correct=self.prerequisite_understanding,
            text_answer_demonstrates_understanding=self.prerequisite_understanding,
        )

    def respond_to_voice_doubt(
        self, _audio: bytes, _mime_type: str, _context: str
    ) -> VoiceDoubtResponse:
        return VoiceDoubtResponse(reply_text="Let us take one small step.", affect="anxious")


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRepository()
        self.educator = FakeEducator()
        app.dependency_overrides[get_repository] = lambda: self.repository
        app.dependency_overrides[get_educator] = lambda: self.educator
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_diagnostic_then_learning_memory_read(self) -> None:
        start = self.client.post("/subjects/math_algebra/diagnostic/start")
        session_id = start.json()["diagnostic_session_id"]
        first = start.json()["question"]
        next_response = self.client.post("/subjects/math_algebra/diagnostic/next", json={"diagnostic_session_id": session_id, "response": {"question_id": first["id"], "selected_option_id": "a", "response_latency_sec": 12}})
        second = next_response.json()["question"]
        response = self.client.post(
            "/diagnostic",
            json={
                "student_id": "stu_api",
                "diagnostic_session_id": session_id,
                "submission": {
                    "responses": [
                        {
                            "question_id": first["id"],
                            "selected_option_id": "a",
                            "response_latency_sec": 12,
                        },
                        {
                            "question_id": second["id"],
                            "selected_option_id": "a",
                            "response_latency_sec": 12,
                        },
                    ],
                    "affective_checkin": "confident",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        memory_response = self.client.get(
            "/students/stu_api/learning-memory?subject_id=math_algebra"
        )
        self.assertEqual(memory_response.status_code, 200)
        self.assertEqual(memory_response.json()["student_id"], "stu_api")

    def test_diagnostic_endpoint_returns_two_ai_questions_without_answer_keys(self) -> None:
        response = self.client.post("/subjects/math_algebra/diagnostic/start")
        self.assertEqual(response.status_code, 200)
        self.assertIn("question", response.json())
        self.assertNotIn("correct_option_id", response.json()["question"])

    def test_teaching_turn_uses_server_selected_strategy(self) -> None:
        self.repository.save(
            LearningMemory.start_for_student("stu_turn", "math_algebra", "two_step_equations")
        )

        response = self.client.post(
            "/students/stu_turn/teaching-turn?subject_id=math_algebra"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["instruction"]["node"], "two_step_equations")
        self.assertEqual(len(response.json()["teaching_turn"]["check_questions"]), 2)

    def test_pause_creates_a_resumable_session_checkpoint(self) -> None:
        self.repository.save(
            LearningMemory.start_for_student("stu_pause", "math_algebra", "one_step_equations")
        )
        response = self.client.post(
            "/students/stu_pause/pause-session?subject_id=math_algebra"
        )

        self.assertEqual(response.status_code, 200)
        checkpoint = response.json()["session_meta"]["paused_sessions"][0]
        self.assertEqual(checkpoint["topic"], "one_step_equations")
        self.assertIn("paused_at", checkpoint)
        self.assertEqual(response.json()["session_meta"]["inactivity_events"], 1)

    def test_prerequisite_gap_queues_a_slow_prerequisite_reteach(self) -> None:
        self.repository.save(
            LearningMemory.start_for_student("stu_pre", "math_algebra", "two_step_equations")
        )
        check_response = self.client.post(
            "/students/stu_pre/prerequisite-check?subject_id=math_algebra"
        )
        self.assertTrue(check_response.json()["required"])
        self.assertEqual(check_response.json()["prerequisite_node"], "one_step_equations")

        self.educator.prerequisite_understanding = False
        result = self.client.post(
            "/students/stu_pre/prerequisite-check-response?subject_id=math_algebra",
            json={
                "lesson_node": "two_step_equations",
                "check": check_response.json()["check"],
                "submission": {"multiple_choice_answer": "x is 0", "text_answer": "I am unsure."},
            },
        )
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()["lesson_ready"])
        memory = result.json()["learning_memory"]
        self.assertEqual(memory["knowledge_profile"]["concept_graph_position"]["current_node"], "one_step_equations")
        self.assertEqual(memory["session_meta"]["pending_lesson_node"], "two_step_equations")
        self.assertEqual(memory["knowledge_profile"]["mastery_history"], [])

    @patch("app.main.convert_for_gemini", return_value=(b"wav-audio", "audio/wav"))
    def test_voice_doubt_updates_only_derived_affect(self, _conversion) -> None:
        self.repository.save(
            LearningMemory.start_for_student("stu_voice", "math_algebra", "negative_numbers")
        )
        response = self.client.post(
            "/students/stu_voice/voice-doubt",
            data={"subject_id": "math_algebra", "active_context": "What is -6 + 9?"},
            files={"audio": ("doubt.webm", b"short-audio", "audio/webm")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["affect"], "anxious")
        profile = response.json()["learning_memory"]["affective_profile"]
        self.assertEqual(profile["voice_affect"], "anxious")
        self.assertNotIn("audio", response.json())

    def test_voice_doubt_rejects_unsupported_audio(self) -> None:
        self.repository.save(
            LearningMemory.start_for_student("stu_bad_audio", "math_algebra", "negative_numbers")
        )
        response = self.client.post(
            "/students/stu_bad_audio/voice-doubt",
            data={"subject_id": "math_algebra", "active_context": "A question"},
            files={"audio": ("doubt.wav", b"short-audio", "audio/wav")},
        )
        self.assertEqual(response.status_code, 415)
