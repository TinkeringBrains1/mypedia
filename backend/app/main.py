"""FastAPI transport for the MyPedia MVP learning loop."""

from __future__ import annotations

import os
from uuid import uuid4
from collections.abc import Generator
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.content.math_algebra import (
    MATH_ALGEBRA_SUBJECT_ID,
    DiagnosticQuestion,
    MATH_ALGEBRA_NODES,
    is_math_algebra_complete,
    prerequisite_for_math_algebra_node,
)

from app.repositories.learning_memory_repository import (
    LearningMemoryStore,
    PostgresLearningMemoryRepository,
)
from app.schemas.learning_memory import LearningMemory, PausedSession, StudentSignal
from app.services.check_response import apply_check_response, apply_voice_affect
from app.services.audio import AudioConversionError, convert_for_gemini
from app.services.diagnostic import (
    DiagnosticFlowError,
    DiagnosticResponse,
    DiagnosticResult,
    DiagnosticSubmission,
    seed_learning_memory,
)
from app.services.educator import (
    CheckResponseInterpretation,
    CheckResponseSubmission,
    GeminiEducator,
    PrerequisiteCheck,
    PrerequisiteInterpretation,
    PrerequisiteSubmission,
    TeachingTurn,
    VoiceDoubtResponse,
)
from app.services.prerequisite import apply_prerequisite_result
from app.services.reflection import refresh_ai_description_if_due
from app.services.strategy_engine import StrategyInstruction, decide_next_move


app = FastAPI(title="MyPedia MVP API", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Lightweight Render health check that does not call Gemini or Postgres."""
    return {"status": "ok"}


cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DiagnosticRequest(BaseModel):
    student_id: str = Field(min_length=1)
    diagnostic_session_id: str = Field(min_length=1)
    submission: DiagnosticSubmission


class SubjectResponse(BaseModel):
    id: str
    label: str


class PublicDiagnosticQuestion(BaseModel):
    """Diagnostic content safe to return to a student browser."""

    id: str
    concept_node: str
    prompt: str
    options: list[dict[str, str]]


class DiagnosticStartResponse(BaseModel):
    diagnostic_session_id: str
    question: PublicDiagnosticQuestion


class DiagnosticNextRequest(BaseModel):
    diagnostic_session_id: str = Field(min_length=1)
    response: DiagnosticResponse


class DiagnosticNextResponse(BaseModel):
    question: PublicDiagnosticQuestion


class TeachingTurnResponse(BaseModel):
    instruction: StrategyInstruction
    teaching_turn: TeachingTurn


class PrerequisiteCheckResponse(BaseModel):
    required: bool
    lesson_node: str
    prerequisite_node: str | None = None
    check: PrerequisiteCheck | None = None


class PrerequisiteCheckRequest(BaseModel):
    lesson_node: str = Field(min_length=1)
    check: PrerequisiteCheck
    submission: PrerequisiteSubmission


class PrerequisiteCheckResultResponse(BaseModel):
    lesson_ready: bool
    learning_memory: LearningMemory
    interpretation: PrerequisiteInterpretation


class VoiceDoubtResultResponse(VoiceDoubtResponse):
    learning_memory: LearningMemory


class CheckResponseRequest(BaseModel):
    subject_id: str = Field(min_length=1)
    teaching_turn: TeachingTurn
    submission: CheckResponseSubmission


class CheckResponseResultResponse(BaseModel):
    learning_memory: LearningMemory
    instruction: StrategyInstruction
    interpretation: CheckResponseInterpretation
    reflection_regenerated: bool
    lesson_complete: bool


class StudentSignalRequest(BaseModel):
    kind: str


class TeachingTurnRequest(BaseModel):
    """Prior content is used only to avoid repeating a requested example."""

    previous_teaching_content: str | None = Field(default=None, max_length=6000)


def get_repository() -> Generator[LearningMemoryStore, None, None]:
    """Yield a PostgreSQL repository from the local, untracked DATABASE_URL."""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured to use the MyPedia API.")

    with psycopg.connect(database_url) as connection:
        yield PostgresLearningMemoryRepository(connection)


def get_educator() -> GeminiEducator:
    return GeminiEducator.from_environment()


def _read_memory(
    repository: LearningMemoryStore, student_id: str, subject_id: str
) -> LearningMemory:
    try:
        return repository.get_relevant_state(student_id, subject_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _require_mvp_subject(subject_id: str) -> None:
    if subject_id != MATH_ALGEBRA_SUBJECT_ID:
        raise HTTPException(status_code=404, detail="This MVP currently offers Maths only.")


def _public_question(question: DiagnosticQuestion) -> PublicDiagnosticQuestion:
    return PublicDiagnosticQuestion(
        id=question.id,
        concept_node=question.concept_node,
        prompt=question.prompt,
        options=[option.model_dump() for option in question.options],
    )


# Diagnostic question keys are deliberately transient and never sent to the browser.
# Learning Memory remains the only persistent learner state.
_diagnostic_sessions: dict[str, tuple[list[DiagnosticQuestion], list[DiagnosticResponse]]] = {}


ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4"}
MAX_VOICE_DOUBT_BYTES = 5 * 1024 * 1024


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/subjects", response_model=list[SubjectResponse])
def list_subjects() -> list[SubjectResponse]:
    return [SubjectResponse(id=MATH_ALGEBRA_SUBJECT_ID, label="Maths")]


@app.post("/subjects/{subject_id}/diagnostic/start", response_model=DiagnosticStartResponse)
def start_diagnostic(subject_id: str, educator: GeminiEducator = Depends(get_educator)) -> DiagnosticStartResponse:
    _require_mvp_subject(subject_id)
    questions = educator.generate_diagnostic_questions([MATH_ALGEBRA_NODES[0]], ["diagnostic_1"])
    session_id = str(uuid4())
    _diagnostic_sessions[session_id] = (questions, [])
    return DiagnosticStartResponse(diagnostic_session_id=session_id, question=_public_question(questions[0]))


@app.post("/subjects/{subject_id}/diagnostic/next", response_model=DiagnosticNextResponse)
def next_diagnostic_question(subject_id: str, request: DiagnosticNextRequest, educator: GeminiEducator = Depends(get_educator)) -> DiagnosticNextResponse:
    _require_mvp_subject(subject_id)
    session = _diagnostic_sessions.get(request.diagnostic_session_id)
    if session is None or len(session[0]) != 1:
        raise HTTPException(status_code=409, detail="This diagnostic session is no longer active.")
    first_question = session[0][0]
    if request.response.question_id != first_question.id or request.response.selected_option_id not in {option.id for option in first_question.options}:
        raise HTTPException(status_code=422, detail="The diagnostic answer does not match the current question.")
    correct = request.response.selected_option_id == first_question.correct_option_id
    second_node = "two_step_equations" if correct else "negative_numbers"
    selected = next(option.text for option in first_question.options if option.id == request.response.selected_option_id)
    second = educator.generate_diagnostic_questions([second_node], ["diagnostic_2"], f"Student selected: {selected}")[0]
    _diagnostic_sessions[request.diagnostic_session_id] = ([first_question, second], [request.response])
    return DiagnosticNextResponse(question=_public_question(second))


@app.post("/diagnostic", response_model=DiagnosticResult)
def submit_diagnostic(
    request: DiagnosticRequest,
    repository: LearningMemoryStore = Depends(get_repository),
) -> DiagnosticResult:
    _require_mvp_subject(MATH_ALGEBRA_SUBJECT_ID)
    session = _diagnostic_sessions.pop(request.diagnostic_session_id, None)
    if session is None:
        raise HTTPException(status_code=409, detail="This diagnostic session has expired. Start again.")
    questions, prior_responses = session
    if len(questions) != 2 or prior_responses != request.submission.responses[:1]:
        raise HTTPException(status_code=422, detail="Complete the diagnostic in its presented order.")
    try:
        result = seed_learning_memory(request.student_id, request.submission, questions)
    except DiagnosticFlowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    repository.save(result.learning_memory)
    return result


@app.get("/students/{student_id}/learning-memory", response_model=LearningMemory)
def get_learning_memory(
    student_id: str,
    subject_id: str = Query(min_length=1),
    repository: LearningMemoryStore = Depends(get_repository),
) -> LearningMemory:
    _require_mvp_subject(subject_id)
    return _read_memory(repository, student_id, subject_id)


@app.post("/students/{student_id}/student-signal", response_model=LearningMemory)
def record_student_signal(student_id: str, request: StudentSignalRequest, subject_id: str = Query(min_length=1), repository: LearningMemoryStore = Depends(get_repository)) -> LearningMemory:
    _require_mvp_subject(subject_id)
    if request.kind not in {"inactivity", "struggling", "challenge"}:
        raise HTTPException(status_code=422, detail="Unknown student signal.")
    memory = _read_memory(repository, student_id, subject_id).model_copy(deep=True)
    topic = memory.knowledge_profile.concept_graph_position.current_node
    memory.session_meta.student_signals = (memory.session_meta.student_signals + [StudentSignal(kind=request.kind, topic=topic)])[-30:]
    if request.kind == "inactivity":
        memory.session_meta.inactivity_events += 1
    elif request.kind == "struggling":
        memory.cognitive_pacing_profile.scaffold_level = "high"
        memory.cognitive_pacing_profile.preferred_chunk_size = "small"
    repository.save(memory)
    return memory


@app.post("/students/{student_id}/teaching-turn", response_model=TeachingTurnResponse)
def generate_teaching_turn(
    student_id: str,
    request: TeachingTurnRequest | None = None,
    subject_id: str = Query(min_length=1),
    repository: LearningMemoryStore = Depends(get_repository),
    educator: GeminiEducator = Depends(get_educator),
) -> TeachingTurnResponse:
    _require_mvp_subject(subject_id)
    memory = _read_memory(repository, student_id, subject_id)
    instruction = decide_next_move(memory)
    if request is not None and request.previous_teaching_content:
        teaching_turn = educator.generate_teaching_turn(
            memory, instruction, alternate_from=request.previous_teaching_content
        )
    else:
        teaching_turn = educator.generate_teaching_turn(memory, instruction)
    return TeachingTurnResponse(
        instruction=instruction,
        teaching_turn=teaching_turn,
    )


@app.post("/students/{student_id}/pause-session", response_model=LearningMemory)
def pause_session(
    student_id: str,
    subject_id: str = Query(min_length=1),
    repository: LearningMemoryStore = Depends(get_repository),
) -> LearningMemory:
    """Save a compact dashboard checkpoint without duplicating learning state."""
    _require_mvp_subject(subject_id)
    memory = _read_memory(repository, student_id, subject_id).model_copy(deep=True)
    topic = memory.knowledge_profile.concept_graph_position.current_node
    memory.session_meta.student_signals = (
        memory.session_meta.student_signals + [StudentSignal(kind="inactivity", topic=topic)]
    )[-30:]
    memory.session_meta.inactivity_events += 1
    memory.session_meta.paused_sessions = (
        memory.session_meta.paused_sessions
        + [
            PausedSession(
                paused_at=datetime.now(timezone.utc),
                topic=topic,
                mastery_score=memory.knowledge_profile.mastery_score,
                engagement_score=memory.affective_profile.inferred.engagement_score,
                progress_summary=(
                    memory.session_meta.lesson_pulse.ai_conclusion
                    or "Ready to continue this lesson."
                ),
            )
        ]
    )[-12:]
    repository.save(memory)
    return memory


@app.post(
    "/students/{student_id}/prerequisite-check",
    response_model=PrerequisiteCheckResponse,
)
def generate_prerequisite_check(
    student_id: str,
    subject_id: str = Query(min_length=1),
    repository: LearningMemoryStore = Depends(get_repository),
    educator: GeminiEducator = Depends(get_educator),
) -> PrerequisiteCheckResponse:
    _require_mvp_subject(subject_id)
    memory = _read_memory(repository, student_id, subject_id)
    lesson_node = decide_next_move(memory).node
    prerequisite_node = prerequisite_for_math_algebra_node(lesson_node)
    if (
        prerequisite_node is None
        or memory.session_meta.prerequisite_checked_for_node == lesson_node
    ):
        return PrerequisiteCheckResponse(required=False, lesson_node=lesson_node)

    return PrerequisiteCheckResponse(
        required=True,
        lesson_node=lesson_node,
        prerequisite_node=prerequisite_node,
        check=educator.generate_prerequisite_check(
            memory, lesson_node, prerequisite_node
        ),
    )


@app.post(
    "/students/{student_id}/prerequisite-check-response",
    response_model=PrerequisiteCheckResultResponse,
)
def submit_prerequisite_check(
    student_id: str,
    request: PrerequisiteCheckRequest,
    subject_id: str = Query(min_length=1),
    repository: LearningMemoryStore = Depends(get_repository),
    educator: GeminiEducator = Depends(get_educator),
) -> PrerequisiteCheckResultResponse:
    _require_mvp_subject(subject_id)
    memory = _read_memory(repository, student_id, subject_id)
    expected_lesson = decide_next_move(memory).node
    if request.lesson_node != expected_lesson:
        raise HTTPException(status_code=409, detail="The learning state changed; request a new prerequisite check.")
    prerequisite_node = prerequisite_for_math_algebra_node(request.lesson_node)
    if prerequisite_node is None or request.check.prerequisite_node != prerequisite_node:
        raise HTTPException(status_code=422, detail="This lesson does not have the supplied prerequisite check.")

    interpretation = educator.interpret_prerequisite_check(
        request.check, request.submission
    )
    updated = apply_prerequisite_result(
        memory, request.lesson_node, prerequisite_node, interpretation, request.submission
    )
    repository.save(updated)
    return PrerequisiteCheckResultResponse(
        lesson_ready=interpretation.demonstrates_understanding,
        learning_memory=updated,
        interpretation=interpretation,
    )


@app.post(
    "/students/{student_id}/voice-doubt",
    response_model=VoiceDoubtResultResponse,
)
async def submit_voice_doubt(
    student_id: str,
    subject_id: str = Form(min_length=1),
    active_context: str = Form(min_length=1, max_length=6000),
    audio: UploadFile = File(),
    repository: LearningMemoryStore = Depends(get_repository),
    educator: GeminiEducator = Depends(get_educator),
) -> VoiceDoubtResultResponse:
    _require_mvp_subject(subject_id)
    mime_type = (audio.content_type or "").split(";", maxsplit=1)[0]
    if mime_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Use a WebM, OGG, or MP4 audio recording.")
    audio_bytes = await audio.read(MAX_VOICE_DOUBT_BYTES + 1)
    if not audio_bytes or len(audio_bytes) > MAX_VOICE_DOUBT_BYTES:
        raise HTTPException(status_code=413, detail="Voice recordings must be no larger than 5 MiB.")

    memory = _read_memory(repository, student_id, subject_id)
    try:
        gemini_audio, gemini_mime_type = convert_for_gemini(audio_bytes, mime_type)
    except AudioConversionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = educator.respond_to_voice_doubt(
        gemini_audio, gemini_mime_type, active_context
    )
    updated = apply_voice_affect(memory, response.affect, response.learning_request, memory.knowledge_profile.concept_graph_position.current_node)
    repository.save(updated)
    return VoiceDoubtResultResponse(
        reply_text=response.reply_text,
        affect=response.affect,
        learning_memory=updated,
    )


@app.post(
    "/students/{student_id}/check-response", response_model=CheckResponseResultResponse
)
def submit_check_response(
    student_id: str,
    request: CheckResponseRequest,
    repository: LearningMemoryStore = Depends(get_repository),
    educator: GeminiEducator = Depends(get_educator),
) -> CheckResponseResultResponse:
    _require_mvp_subject(request.subject_id)
    memory = _read_memory(repository, student_id, request.subject_id)
    instruction = decide_next_move(memory)
    interpretation = educator.interpret_check_responses(
        request.teaching_turn, request.submission
    )
    updated = apply_check_response(
        memory, instruction, request.submission, interpretation
    ).learning_memory
    reflection = refresh_ai_description_if_due(updated, educator)
    repository.save(reflection.learning_memory)
    return CheckResponseResultResponse(
        learning_memory=reflection.learning_memory,
        instruction=instruction,
        interpretation=interpretation,
        reflection_regenerated=reflection.regenerated,
        lesson_complete=is_math_algebra_complete(
            reflection.learning_memory.knowledge_profile.concept_graph_position.mastered_nodes
        ),
    )
