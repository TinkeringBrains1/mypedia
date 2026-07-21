import unittest

from app.schemas.learning_memory import LearningMemory
from app.services.educator import (
    GEMINI_MODEL,
    CheckResponseSubmission,
    GeminiEducator,
    ReflectionSummary,
    StudentCheckAnswer,
    TeachingTurn,
    PrerequisiteCheck,
    PrerequisiteMultipleChoice,
    PrerequisiteSubmission,
    VoiceDoubtResponse,
    build_educator_prompt,
)
from app.services.strategy_engine import decide_next_move


class FakeInteractions:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.request: dict[str, object] | None = None

    def create(self, **kwargs: object) -> object:
        self.request = kwargs
        return type("Interaction", (), {"output_text": self.output_text})()


class FakeGeminiClient:
    def __init__(self, output_text: str) -> None:
        self.interactions = FakeInteractions(output_text)


def memory_for_educator() -> LearningMemory:
    memory = LearningMemory.start_for_student(
        student_id="stu_0231",
        subject_id="math_algebra",
        first_concept_node="linear_equations_one_var",
    )
    memory.ai_desc.summary = "Learns best with calm, short explanations."
    return memory


class EducatorTest(unittest.TestCase):
    def test_prompt_keeps_strategy_in_charge_of_what_is_taught(self) -> None:
        memory = memory_for_educator()
        instruction = decide_next_move(memory)

        prompt = build_educator_prompt(memory, instruction)

        self.assertIn("linear_equations_one_var", prompt.user_input)
        self.assertIn(instruction.reason, prompt.user_input)
        self.assertIn(memory.ai_desc.summary, prompt.user_input)
        self.assertIn("do not change the concept node", prompt.system_instruction)

    def test_prompt_includes_recent_student_wording_for_a_natural_follow_up(self) -> None:
        memory = memory_for_educator()
        memory.session_meta.recent_student_responses = ["I subtracted 3, then I was not sure what to do."]
        prompt = build_educator_prompt(memory, decide_next_move(memory))
        self.assertIn(memory.session_meta.recent_student_responses[0], prompt.user_input)
        self.assertIn("thoughtful human tutor", prompt.system_instruction)

    def test_generate_teaching_turn_uses_structured_gemini_response(self) -> None:
        expected_turn = TeachingTurn(
            teaching_content="Solve 2x + 3 = 11 by undoing the +3 first.",
            check_questions=["What is 11 - 3?", "What is x if 2x = 8?"],
        )
        client = FakeGeminiClient(expected_turn.model_dump_json())
        educator = GeminiEducator(client)

        turn = educator.generate_teaching_turn(
            memory_for_educator(), decide_next_move(memory_for_educator())
        )

        self.assertEqual(turn, expected_turn)
        self.assertEqual(client.interactions.request["model"], GEMINI_MODEL)
        self.assertFalse(client.interactions.request["store"])
        self.assertEqual(
            client.interactions.request["response_format"]["mime_type"],
            "application/json",
        )

    def test_teaching_turn_requires_two_or_three_questions(self) -> None:
        with self.assertRaises(ValueError):
            TeachingTurn(teaching_content="A short explanation.", check_questions=["Only one?"])

    def test_interpretation_requires_ordered_result_for_each_answer(self) -> None:
        turn = TeachingTurn(
            teaching_content="Work one step at a time.",
            check_questions=["What is 2 + 2?", "What is 5 - 1?"],
        )
        submission = CheckResponseSubmission(
            answers=[
                StudentCheckAnswer(answer="4", response_latency_sec=5),
                StudentCheckAnswer(answer="4", response_latency_sec=4),
            ]
        )
        client = FakeGeminiClient(
            '{"answers":[{"question_index":0,"is_correct":true},'
            '{"question_index":1,"is_correct":true}],"affect_signal":"calm"}'
        )

        interpretation = GeminiEducator(client).interpret_check_responses(turn, submission)

        self.assertEqual([answer.is_correct for answer in interpretation.answers], [True, True])
        self.assertFalse(client.interactions.request["store"])

    def test_prerequisite_check_and_interpretation_use_structured_responses(self) -> None:
        check = PrerequisiteCheck(
            prerequisite_node="one_step_equations",
            multiple_choice=PrerequisiteMultipleChoice(
                prompt="Solve x + 2 = 5.", options=["3", "5", "7"]
            ),
            text_prompt="Explain the first step.",
        )
        client = FakeGeminiClient(check.model_dump_json())
        educator = GeminiEducator(client)
        self.assertEqual(
            educator.generate_prerequisite_check(
                memory_for_educator(), "two_step_equations", "one_step_equations"
            ),
            check,
        )
        self.assertFalse(client.interactions.request["store"])

        client.interactions.output_text = '{"multiple_choice_correct":true,"text_answer_demonstrates_understanding":true}'
        interpretation = educator.interpret_prerequisite_check(
            check, PrerequisiteSubmission(multiple_choice_answer="3", text_answer="Subtract 2.")
        )
        self.assertTrue(interpretation.demonstrates_understanding)
        self.assertFalse(client.interactions.request["store"])

    def test_voice_doubt_sends_audio_without_storing_it(self) -> None:
        client = FakeGeminiClient(
            VoiceDoubtResponse(reply_text="Let us try one step.", affect="anxious").model_dump_json()
        )
        response = GeminiEducator(client).respond_to_voice_doubt(
            b"short-audio", "audio/webm", "Solve x + 2 = 5."
        )
        self.assertEqual(response.affect, "anxious")
        self.assertFalse(client.interactions.request["store"])
        self.assertEqual(client.interactions.request["input"][1]["type"], "audio")

    def test_reflection_returns_a_structured_summary(self) -> None:
        client = FakeGeminiClient(
            '{"summary":"Shows steady effort and benefits from short algebra steps."}'
        )

        reflection = GeminiEducator(client).regenerate_ai_description(memory_for_educator())

        self.assertIsInstance(reflection, ReflectionSummary)
        self.assertFalse(client.interactions.request["store"])
        self.assertIn("Reflection Mode", client.interactions.request["system_instruction"])
