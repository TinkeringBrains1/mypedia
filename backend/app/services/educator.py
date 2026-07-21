"""Gemini-backed Educator for teaching-turn generation.

The Educator adapts *how* a designated concept is taught. The deterministic
Strategy Engine remains solely responsible for choosing that concept and move.
"""

from __future__ import annotations

import os
import json
import base64
from typing import Any, Literal, Protocol

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.learning_memory import LearningMemory
from app.services.strategy_engine import StrategyInstruction
from app.content.math_algebra import DiagnosticQuestion


GEMINI_MODEL = "gemini-3.1-flash-lite"


class TeachingTurn(BaseModel):
    """Student-facing material returned by the Educator for one learning turn."""

    model_config = ConfigDict(extra="forbid")

    teaching_content: str = Field(min_length=1)
    check_questions: list[str] = Field(min_length=2, max_length=3)


class PrerequisiteMultipleChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    options: list[str] = Field(min_length=3, max_length=3)


class PrerequisiteCheck(BaseModel):
    """An AI-authored, low-stakes check for one deterministic prerequisite."""

    model_config = ConfigDict(extra="forbid")

    prerequisite_node: str = Field(min_length=1)
    multiple_choice: PrerequisiteMultipleChoice
    text_prompt: str = Field(min_length=1)


class PrerequisiteSubmission(BaseModel):
    multiple_choice_answer: str = Field(min_length=1)
    text_answer: str = Field(min_length=1)


class PrerequisiteInterpretation(BaseModel):
    multiple_choice_correct: bool
    text_answer_demonstrates_understanding: bool

    @property
    def demonstrates_understanding(self) -> bool:
        return self.multiple_choice_correct and self.text_answer_demonstrates_understanding


VoiceAffect = Literal["anxious", "neutral", "confident"]


class VoiceDoubtResponse(BaseModel):
    """The only retained output from a transient student voice recording."""

    model_config = ConfigDict(extra="forbid")

    reply_text: str = Field(min_length=1, max_length=1200)
    affect: VoiceAffect
    learning_request: Literal["slower", "worked_example", "ready", "none"] = "none"


class StudentCheckAnswer(BaseModel):
    """A student's answer and local interaction metadata for one check question."""

    answer: str = Field(min_length=1)
    response_latency_sec: float = Field(ge=0.0)
    used_hint: bool = False
    attempt_count: int = Field(default=1, ge=1)


class CheckResponseSubmission(BaseModel):
    """Answers submitted for the complete low-stakes check."""

    answers: list[StudentCheckAnswer] = Field(min_length=2, max_length=3)


class InterpretedCheckAnswer(BaseModel):
    question_index: int = Field(ge=0)
    is_correct: bool


class CheckResponseInterpretation(BaseModel):
    """The narrow Gemini interpretation passed to deterministic state updates."""

    answers: list[InterpretedCheckAnswer] = Field(min_length=2, max_length=3)
    affect_signal: Literal["calm", "uncertain", "frustrated"]


class ReflectionSummary(BaseModel):
    """The compact narrative written to Learning Memory's ``ai_desc`` field."""

    summary: str = Field(min_length=1, max_length=600)
    lesson_conclusion: str = Field(default="", max_length=320)


class PromptParts(BaseModel):
    """Separated prompt parts make the instructional policy easy to inspect."""

    system_instruction: str
    user_input: str


class InteractionsAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class GeminiClient(Protocol):
    interactions: InteractionsAPI


class EducatorGenerationError(RuntimeError):
    """Raised when Gemini does not produce the required teaching-turn contract."""


def build_educator_prompt(
    memory: LearningMemory,
    instruction: StrategyInstruction,
    alternate_from: str | None = None,
) -> PromptParts:
    """Build the minimal context the Educator needs for a teaching turn.

    The current node and deterministic instruction are deliberately explicit.
    The Educator must not select another topic, alter strategy, or write
    Learning Memory.
    """
    ai_summary = memory.ai_desc.summary or "No narrative summary is available yet."
    interest_tags = ", ".join(instruction.example_interest_tags) or "none"

    system_instruction = """You are Mypedia's Educator for one learning turn.
Teach the exact concept selected by the Strategy Engine. You decide how to
explain it, not what the learner studies next.

Follow every Strategy Engine instruction exactly:
- do not change the concept node or advance the curriculum;
- match the requested chunk size and tone;
- use the requested worked-example density and interest tags when supplied;
- if score visibility is false, frame the check as private practice and do not
  mention marks, grades, percentages, or scores;
- if a short session is requested, keep the teaching content concise;
- if a stretch problem is requested, include it as one of the check questions;
- always create exactly 2 or 3 short, low-stakes check questions.

Sound like a thoughtful human tutor: write naturally, vary sentence rhythm, and
give a clear reason for each step. When recent student responses are supplied,
use them to address the student's actual approach or misconception when useful.
Do not pretend to know anything they did not write, repeat their answer at
length, use generic praise, or say "Great question". Keep the tone calm,
specific, and conversational.

Return only JSON matching the supplied response schema. Do not assess the
student, update mastery, infer affect, write ai_desc, or choose a next lesson."""

    recent_responses = memory.session_meta.recent_student_responses
    response_context = "\n".join(f"- {response}" for response in recent_responses) or "No prior written responses in this session."
    user_input = f"""Learning Memory narrative summary:
{ai_summary}

Recent student responses (use only when relevant):
{response_context}

Current concept node to teach: {instruction.node}

Strategy Engine instruction:
- action: {instruction.action}
- chunk size: {instruction.chunk_size}
- tone: {instruction.tone}
- visible score: {instruction.visible_score}
- worked-example density: {instruction.worked_example_density}
- offer stretch problem: {instruction.offer_stretch_problem}
- session length: {instruction.session_length}
- interest tags for examples: {interest_tags}
- requires a low-stakes check: {instruction.requires_low_stakes_check}
- rationale: {instruction.reason}

Generate this one teaching turn now."""
    if alternate_from:
        user_input += f"""

The student requested another example. Use a genuinely different explanation
and worked example: do not reuse the previous turn's numbers, scenario, or
sentence structure. Keep the same concept and Strategy Engine instruction.

Previous turn:
{alternate_from[:6000]}"""

    return PromptParts(
        system_instruction=system_instruction,
        user_input=user_input,
    )


class GeminiEducator:
    """Calls Gemini only to produce teaching content and check questions."""

    def __init__(
        self, client: GeminiClient, model: str = GEMINI_MODEL
    ) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_environment(cls) -> "GeminiEducator":
        """Create an Educator from the local, untracked GEMINI_API_KEY."""
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY must be configured to use the Educator.")
        return cls(genai.Client(api_key=api_key))

    def generate_teaching_turn(
        self,
        memory: LearningMemory,
        instruction: StrategyInstruction,
        alternate_from: str | None = None,
    ) -> TeachingTurn:
        """Generate a structured teaching turn without changing application state."""
        prompt = build_educator_prompt(memory, instruction, alternate_from)
        interaction = self._client.interactions.create(
            model=self._model,
            input=prompt.user_input,
            system_instruction=prompt.system_instruction,
            store=False,
            generation_config={"temperature": 0.4},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": TeachingTurn.model_json_schema(),
            },
        )

        try:
            return TeachingTurn.model_validate_json(interaction.output_text)
        except (AttributeError, ValidationError) as exc:
            raise EducatorGenerationError(
                "Gemini returned an invalid teaching-turn response."
            ) from exc

    def generate_diagnostic_questions(
        self, concept_nodes: list[str], question_ids: list[str] | None = None, prior_response: str | None = None
    ) -> list[DiagnosticQuestion]:
        """Author two diagnostic questions for curriculum nodes chosen by code."""
        system_instruction = """You are MyPedia's diagnostic-question author.
Write exactly two short, accessible three-option multiple-choice Maths questions.
Each question must assess the corresponding supplied curriculum node, in the same
order. Use the supplied unique question id and corresponding `concept_node`; option ids must be
`a`, `b`, and `c`; and `correct_option_id` must identify the one correct option.
Do not choose other curriculum nodes, assess affect, teach a lesson, or add fields.
Return only JSON matching the supplied response schema."""
        interaction = self._client.interactions.create(
            model=self._model,
            input=(f"Curriculum nodes, in order: {json.dumps(concept_nodes)}\n"
                   f"Question ids, in order: {json.dumps(question_ids or concept_nodes)}\n"
                   f"Previous diagnostic response, if any: {prior_response or 'None'}"),
            system_instruction=system_instruction,
            store=False,
            generation_config={"temperature": 0.35},
            response_format={
                "type": "text", "mime_type": "application/json",
                # Gemini's Interactions API does not resolve nested Pydantic
                # `$ref`s inside a root array schema, so keep this small
                # student-facing contract fully inline.
                "schema": {
                    "type": "array",
                    "minItems": len(concept_nodes),
                    "maxItems": len(concept_nodes),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "concept_node", "prompt", "options", "correct_option_id"],
                        "properties": {
                            "id": {"type": "string"},
                            "concept_node": {"type": "string"},
                            "prompt": {"type": "string"},
                            "correct_option_id": {"type": "string", "enum": ["a", "b", "c"]},
                            "options": {
                                "type": "array",
                                "minItems": 3,
                                "maxItems": 3,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["id", "text"],
                                    "properties": {
                                        "id": {"type": "string", "enum": ["a", "b", "c"]},
                                        "text": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        )
        try:
            questions = [DiagnosticQuestion.model_validate(item) for item in json.loads(interaction.output_text)]
        except (AttributeError, TypeError, ValueError, ValidationError) as exc:
            raise EducatorGenerationError("Gemini returned invalid diagnostic questions.") from exc
        expected_ids = question_ids or concept_nodes
        if len(questions) != len(concept_nodes) or [question.concept_node for question in questions] != concept_nodes or [question.id for question in questions] != expected_ids:
            raise EducatorGenerationError("Gemini must preserve the selected diagnostic nodes and ids.")
        return questions

    def interpret_check_responses(
        self,
        teaching_turn: TeachingTurn,
        submission: CheckResponseSubmission,
    ) -> CheckResponseInterpretation:
        """Interpret answers; deterministic code, not Gemini, updates Memory."""
        if len(teaching_turn.check_questions) != len(submission.answers):
            raise ValueError("Every check question must have exactly one student answer.")

        numbered_answers = "\n".join(
            (
                f"Question {index}: {question}\n"
                f"Student answer {index}: {answer.answer}"
            )
            for index, (question, answer) in enumerate(
                zip(teaching_turn.check_questions, submission.answers)
            )
        )
        system_instruction = """You are MyPedia's response interpreter.
For each numbered low-stakes check question, determine whether the student's
answer is correct. Return one result for every question in the same zero-based
order. Select `frustrated` only when the student's wording clearly communicates
frustration, select `uncertain` only when it clearly communicates uncertainty,
and otherwise select `calm`.

Do not choose a lesson, change a teaching strategy, calculate mastery, update
Learning Memory, provide teaching content, or add any fields. Return only JSON
matching the supplied response schema."""

        interaction = self._client.interactions.create(
            model=self._model,
            input=numbered_answers,
            system_instruction=system_instruction,
            store=False,
            generation_config={"temperature": 0.0},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": CheckResponseInterpretation.model_json_schema(),
            },
        )
        try:
            interpretation = CheckResponseInterpretation.model_validate_json(
                interaction.output_text
            )
        except (AttributeError, ValidationError) as exc:
            raise EducatorGenerationError(
                "Gemini returned an invalid check-response interpretation."
            ) from exc

        expected_indices = list(range(len(submission.answers)))
        actual_indices = [answer.question_index for answer in interpretation.answers]
        if actual_indices != expected_indices:
            raise EducatorGenerationError(
                "Gemini must return one ordered interpretation for every answer."
            )
        return interpretation

    def generate_prerequisite_check(
        self,
        memory: LearningMemory,
        lesson_node: str,
        prerequisite_node: str,
    ) -> PrerequisiteCheck:
        """Generate wording for a prerequisite selected by deterministic code."""
        system_instruction = """You are MyPedia's prerequisite-check author.
The curriculum code selected the lesson and its prerequisite. Write exactly one
short, supportive three-option multiple-choice question and exactly one short
textual-answer question that assess only that prerequisite.

Do not teach, decide curriculum, update Learning Memory, reveal an answer key,
or add fields. Return only JSON matching the supplied response schema."""
        interaction = self._client.interactions.create(
            model=self._model,
            input=(
                f"Planned lesson node: {lesson_node}\n"
                f"Prerequisite node to assess: {prerequisite_node}\n"
                f"Learning Memory summary: {memory.ai_desc.summary or 'None yet.'}"
            ),
            system_instruction=system_instruction,
            store=False,
            generation_config={"temperature": 0.3},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": PrerequisiteCheck.model_json_schema(),
            },
        )
        try:
            check = PrerequisiteCheck.model_validate_json(interaction.output_text)
        except (AttributeError, ValidationError) as exc:
            raise EducatorGenerationError(
                "Gemini returned an invalid prerequisite-check response."
            ) from exc
        if check.prerequisite_node != prerequisite_node:
            raise EducatorGenerationError("Gemini must keep the selected prerequisite node.")
        return check

    def interpret_prerequisite_check(
        self,
        check: PrerequisiteCheck,
        submission: PrerequisiteSubmission,
    ) -> PrerequisiteInterpretation:
        """Interpret both prerequisite responses without changing state."""
        system_instruction = """You are MyPedia's prerequisite-check interpreter.
Determine whether the selected multiple-choice answer is correct and whether the
student's text answer demonstrates understanding of the exact prerequisite.
Do not teach, choose a lesson, update Learning Memory, infer wellbeing, or add
fields. Return only JSON matching the supplied response schema."""
        interaction = self._client.interactions.create(
            model=self._model,
            input=(
                f"Prerequisite: {check.prerequisite_node}\n"
                f"Multiple-choice question: {check.multiple_choice.prompt}\n"
                f"Options: {json.dumps(check.multiple_choice.options)}\n"
                f"Student selected: {submission.multiple_choice_answer}\n"
                f"Text question: {check.text_prompt}\n"
                f"Student text answer: {submission.text_answer}"
            ),
            system_instruction=system_instruction,
            store=False,
            generation_config={"temperature": 0.0},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": PrerequisiteInterpretation.model_json_schema(),
            },
        )
        try:
            return PrerequisiteInterpretation.model_validate_json(interaction.output_text)
        except (AttributeError, ValidationError) as exc:
            raise EducatorGenerationError(
                "Gemini returned an invalid prerequisite interpretation."
            ) from exc

    def respond_to_voice_doubt(
        self, audio_bytes: bytes, mime_type: str, active_context: str
    ) -> VoiceDoubtResponse:
        """Answer one short audio doubt and classify the student's affect."""
        system_instruction = """You are MyPedia's voice-doubt Educator.
Listen to the student's short question and answer the learning doubt in plain,
supportive text using the supplied active context. Classify affect as exactly:
anxious (dreading or worried), neutral (a straightforward doubt), or confident
(curious and genuinely engaged).

For anxious, validate feelings and offer one very small next step. For neutral,
give a direct clarification with one worked step. For confident, acknowledge
curiosity and explain precisely without over-scaffolding. Do not diagnose,
choose curriculum or update Learning Memory. Set learning_request to `slower`
when the student asks to slow down, `worked_example` when they ask for another
example, `ready` when they ask to move on, otherwise `none`. Return only JSON
matching the supplied response schema."""
        interaction = self._client.interactions.create(
            model=self._model,
            input=[
                {"type": "text", "text": f"Active learning context:\n{active_context}"},
                {
                    "type": "audio",
                    "data": base64.b64encode(audio_bytes).decode("ascii"),
                    "mime_type": mime_type,
                },
            ],
            system_instruction=system_instruction,
            store=False,
            generation_config={"temperature": 0.3},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": VoiceDoubtResponse.model_json_schema(),
            },
        )
        try:
            return VoiceDoubtResponse.model_validate_json(interaction.output_text)
        except (AttributeError, ValidationError) as exc:
            raise EducatorGenerationError(
                "Gemini returned an invalid voice-doubt response."
            ) from exc

    def regenerate_ai_description(self, memory: LearningMemory) -> ReflectionSummary:
        """Generate a compact narrative summary from existing Learning Memory."""
        position = memory.knowledge_profile.concept_graph_position
        context = {
            "subject_id": memory.subject_id,
            "current_node": position.current_node,
            "mastered_nodes": position.mastered_nodes,
            "struggling_nodes": position.struggling_nodes,
            "mastery_score": memory.knowledge_profile.mastery_score,
            "recent_mastery": memory.knowledge_profile.mastery_history[-3:],
            "pacing": memory.cognitive_pacing_profile.model_dump(),
            "affect": memory.affective_profile.model_dump(),
            "interest_tags": memory.interest_context.tags,
            "lesson_pulse": memory.session_meta.lesson_pulse.model_dump(),
            "recent_question_outcomes": [item.model_dump() for item in memory.session_meta.lesson_question_history[-6:]],
        }
        system_instruction = """You are MyPedia's Reflection Mode.
Write a factual, supportive two- or three-sentence narrative about the learner's
current understanding, pacing, and affect using only the supplied Learning
Memory facts. Mention an observed strength and, when present, a concrete area
that needs support. Do not diagnose, speculate, assign labels, choose the next
lesson, give parental advice, calculate scores, or change any state.

Also write `lesson_conclusion`: one short factual sentence about the current
accuracy/pace/help-seeking pattern and the next support needed. Return only JSON
matching the supplied response schema."""
        interaction = self._client.interactions.create(
            model=self._model,
            input=json.dumps(context),
            system_instruction=system_instruction,
            store=False,
            generation_config={"temperature": 0.2},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ReflectionSummary.model_json_schema(),
            },
        )
        try:
            return ReflectionSummary.model_validate_json(interaction.output_text)
        except (AttributeError, ValidationError) as exc:
            raise EducatorGenerationError(
                "Gemini returned an invalid Reflection Mode response."
            ) from exc
