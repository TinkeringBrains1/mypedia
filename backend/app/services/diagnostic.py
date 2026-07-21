"""Deterministic interpretation of a two-question, AI-authored diagnostic."""

from __future__ import annotations

from statistics import fmean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.content.math_algebra import MATH_ALGEBRA_NODES, MATH_ALGEBRA_SUBJECT_ID, DiagnosticQuestion
from app.schemas.learning_memory import LearningMemory

AffectiveCheckin = Literal["confident", "unsure", "anxious"]

class DiagnosticResponse(BaseModel):
    question_id: str
    selected_option_id: str
    response_latency_sec: float = Field(ge=0.0)
    used_hint: bool = False
    attempt_count: int = Field(default=1, ge=1)

class DiagnosticSubmission(BaseModel):
    responses: list[DiagnosticResponse] = Field(min_length=2, max_length=2)
    affective_checkin: AffectiveCheckin

class DiagnosticResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    learning_memory: LearningMemory
    completed_question_ids: list[str]

class DiagnosticFlowError(ValueError):
    pass

def seed_learning_memory(student_id: str, submission: DiagnosticSubmission, questions: list[DiagnosticQuestion]) -> DiagnosticResult:
    """Write initial state from answers; Gemini only authored the question wording."""
    _validate_responses(submission.responses, questions)
    correct = [response.selected_option_id == question.correct_option_id for response, question in zip(submission.responses, questions)]
    first_incorrect = next((index for index, value in enumerate(correct) if not value), None)
    current_question = questions[first_incorrect] if first_incorrect is not None else questions[-1]
    current_index = MATH_ALGEBRA_NODES.index(current_question.concept_node)
    mastered_nodes = [question.concept_node for response, question, is_correct in zip(submission.responses, questions, correct) if is_correct]
    struggling_nodes = [] if all(correct) else [current_question.concept_node]
    not_yet_attempted = [] if all(correct) else list(MATH_ALGEBRA_NODES[current_index + 1:])

    memory = LearningMemory.start_for_student(student_id, MATH_ALGEBRA_SUBJECT_ID, current_question.concept_node)
    position = memory.knowledge_profile.concept_graph_position
    position.mastered_nodes = list(dict.fromkeys(mastered_nodes))
    position.struggling_nodes = struggling_nodes
    position.not_yet_attempted = not_yet_attempted
    score = sum(correct) / len(correct)
    memory.knowledge_profile.mastery_score = score
    memory.knowledge_profile.mastery_history = [score]
    _seed_pacing(memory, submission.responses)
    _seed_affect(memory, submission.affective_checkin)
    return DiagnosticResult(learning_memory=memory, completed_question_ids=[response.question_id for response in submission.responses])

def _validate_responses(responses: list[DiagnosticResponse], questions: list[DiagnosticQuestion]) -> None:
    if len(questions) != 2 or len(responses) != 2:
        raise DiagnosticFlowError("The diagnostic requires exactly two questions and two answers.")
    for response, question in zip(responses, questions):
        if response.question_id != question.id:
            raise DiagnosticFlowError("Diagnostic answers do not match this diagnostic session.")
        if response.selected_option_id not in {option.id for option in question.options}:
            raise DiagnosticFlowError("A diagnostic answer is not one of the supplied options.")

def _seed_pacing(memory: LearningMemory, responses: list[DiagnosticResponse]) -> None:
    pacing = memory.cognitive_pacing_profile
    pacing.avg_response_latency_sec = fmean(response.response_latency_sec for response in responses)
    pacing.hint_usage_rate = sum(response.used_hint for response in responses) / len(responses)
    pacing.retry_rate = sum(response.attempt_count > 1 for response in responses) / len(responses)
    if pacing.hint_usage_rate > 0 or pacing.retry_rate > 0:
        pacing.scaffold_level, pacing.preferred_chunk_size = "high", "small"
    elif pacing.avg_response_latency_sec <= 20 and all(response.attempt_count == 1 for response in responses):
        pacing.scaffold_level, pacing.preferred_chunk_size = "low", "large"

def _seed_affect(memory: LearningMemory, checkin: AffectiveCheckin) -> None:
    profile = memory.affective_profile
    profile.self_reported.last_checkin, profile.self_reported.checkin_history = checkin, [checkin]
    profile.mismatch_flag = False
    inferred = profile.inferred
    if checkin == "confident": inferred.engagement_score, inferred.stress_signal, inferred.self_efficacy_score = .65, .15, .75
    elif checkin == "unsure": inferred.engagement_score, inferred.stress_signal, inferred.self_efficacy_score = .5, .4, .5
    else: inferred.engagement_score, inferred.stress_signal, inferred.self_efficacy_score = .4, .75, .3
    inferred.stress_history = [inferred.stress_signal]
