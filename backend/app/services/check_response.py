"""Deterministic Learning Memory writes from interpreted check responses."""

from __future__ import annotations

from statistics import fmean

from pydantic import BaseModel, ConfigDict, Field

from app.services.educator import CheckResponseInterpretation, CheckResponseSubmission
from app.services.strategy_engine import StrategyInstruction
from app.schemas.learning_memory import HelpSeekingEvent, LessonQuestionOutcome, LessonPulse, LearningMemory


class CheckResponseResult(BaseModel):
    """The updated canonical memory plus an inspectable turn-accuracy value."""

    model_config = ConfigDict(frozen=True)

    learning_memory: LearningMemory
    turn_accuracy: float = Field(ge=0.0, le=1.0)


def apply_check_response(
    memory: LearningMemory,
    instruction: StrategyInstruction,
    submission: CheckResponseSubmission,
    interpretation: CheckResponseInterpretation,
) -> CheckResponseResult:
    """Apply the approved deterministic response-update policy.

    Gemini supplies only correctness and a bounded affect cue. Every change to
    Learning Memory is calculated here, separately and reproducibly.
    """
    _validate_matching_response_counts(submission, interpretation)
    updated_memory = memory.model_copy(deep=True)
    turn_accuracy = sum(
        answer.is_correct for answer in interpretation.answers
    ) / len(interpretation.answers)

    _update_knowledge(updated_memory, instruction, turn_accuracy)
    _update_pacing(updated_memory, submission, turn_accuracy)
    _update_affect(updated_memory, interpretation.affect_signal, turn_accuracy)
    _record_recent_responses(updated_memory, submission)
    _record_question_outcomes(updated_memory, instruction.node, submission, interpretation)
    _refresh_lesson_pulse(updated_memory)
    if updated_memory.session_meta.pending_lesson_node == instruction.node:
        updated_memory.session_meta.pending_lesson_node = None
    updated_memory.session_meta.last_orchestrator_action = instruction.action_key
    updated_memory.session_meta.voice_learning_request = "none"

    return CheckResponseResult(
        learning_memory=updated_memory,
        turn_accuracy=turn_accuracy,
    )


def _update_knowledge(
    memory: LearningMemory, instruction: StrategyInstruction, turn_accuracy: float
) -> None:
    profile = memory.knowledge_profile
    position = profile.concept_graph_position
    taught_node = instruction.node

    profile.mastery_score = 0.70 * profile.mastery_score + 0.30 * turn_accuracy
    profile.mastery_history.append(turn_accuracy)
    position.current_node = taught_node
    position.not_yet_attempted = [
        node for node in position.not_yet_attempted if node != taught_node
    ]

    if turn_accuracy < 0.50:
        position.mastered_nodes = [node for node in position.mastered_nodes if node != taught_node]
        if taught_node not in position.struggling_nodes:
            position.struggling_nodes.append(taught_node)
    elif turn_accuracy >= 0.75:
        if taught_node not in position.mastered_nodes:
            position.mastered_nodes.append(taught_node)
        position.struggling_nodes = [
            node for node in position.struggling_nodes if node != taught_node
        ]


def _update_pacing(
    memory: LearningMemory,
    submission: CheckResponseSubmission,
    turn_accuracy: float,
) -> None:
    pacing = memory.cognitive_pacing_profile
    turn_latency = fmean(answer.response_latency_sec for answer in submission.answers)
    turn_hint_rate = sum(answer.used_hint for answer in submission.answers) / len(
        submission.answers
    )
    turn_retry_rate = sum(answer.attempt_count > 1 for answer in submission.answers) / len(
        submission.answers
    )

    pacing.avg_response_latency_sec = _blend_optional_average(
        pacing.avg_response_latency_sec, turn_latency
    )
    pacing.hint_usage_rate = (pacing.hint_usage_rate + turn_hint_rate) / 2
    pacing.retry_rate = (pacing.retry_rate + turn_retry_rate) / 2

    if (
        turn_hint_rate > 0.4
        or turn_retry_rate > 0.4
        or pacing.hint_usage_rate > 0.4
        or pacing.retry_rate > 0.4
    ):
        pacing.scaffold_level = "high"
        pacing.preferred_chunk_size = "small"
    elif turn_accuracy >= 0.75 and pacing.avg_response_latency_sec <= 20:
        pacing.scaffold_level = "low"
        pacing.preferred_chunk_size = "large"
    else:
        pacing.scaffold_level = "medium"
        pacing.preferred_chunk_size = "medium"


def _update_affect(
    memory: LearningMemory,
    affect_signal: str,
    turn_accuracy: float,
) -> None:
    inferred = memory.affective_profile.inferred
    stress_delta = 0.15 if affect_signal == "frustrated" else 0.0

    if turn_accuracy < 0.50:
        stress_delta += 0.10
        engagement_delta = -0.10
    elif turn_accuracy >= 0.75:
        stress_delta -= 0.10
        engagement_delta = 0.10
    else:
        engagement_delta = 0.0

    inferred.stress_signal = _clamp(inferred.stress_signal + stress_delta)
    inferred.stress_history.append(inferred.stress_signal)
    inferred.engagement_score = _clamp(inferred.engagement_score + engagement_delta)


def _record_recent_responses(
    memory: LearningMemory, submission: CheckResponseSubmission
) -> None:
    """Keep only a small, bounded window of the student's own recent wording."""
    additions = [answer.answer.strip().replace("\n", " ")[:360] for answer in submission.answers]
    memory.session_meta.recent_student_responses = (
        memory.session_meta.recent_student_responses + additions
    )[-4:]


def _record_question_outcomes(memory: LearningMemory, topic: str, submission: CheckResponseSubmission, interpretation: CheckResponseInterpretation) -> None:
    history = memory.session_meta.lesson_question_history
    start = history[-1].question_no + 1 if history else 1
    additions = [LessonQuestionOutcome(question_no=start + index, topic=topic, accuracy=float(result.is_correct), time_sec=answer.response_latency_sec) for index, (answer, result) in enumerate(zip(submission.answers, interpretation.answers))]
    memory.session_meta.lesson_question_history = (history + additions)[-30:]


def _refresh_lesson_pulse(memory: LearningMemory) -> None:
    history = memory.session_meta.lesson_question_history[-6:]
    if not history:
        return
    accuracy = sum(item.accuracy for item in history) / len(history)
    first, last = history[: max(1, len(history) // 2)], history[len(history) // 2 :]
    first_accuracy = sum(item.accuracy for item in first) / len(first)
    last_accuracy = sum(item.accuracy for item in last) / len(last)
    accuracy_trend = "declining" if last_accuracy + .2 < first_accuracy else "improving" if last_accuracy > first_accuracy + .2 else "steady"
    first_time = sum(item.time_sec for item in first) / len(first)
    last_time = sum(item.time_sec for item in last) / len(last)
    pace_trend = "slower" if last_time > first_time * 1.35 else "faster" if last_time < first_time * .7 else "steady"
    support_topic = next((item.topic for item in reversed(history) if item.accuracy == 0), None)
    memory.session_meta.lesson_pulse = LessonPulse(recent_accuracy=accuracy, accuracy_trend=accuracy_trend, pace_trend=pace_trend, help_seeking_count=len(memory.session_meta.help_seeking_events), support_topic=support_topic, ai_conclusion=memory.session_meta.lesson_pulse.ai_conclusion)


def _blend_optional_average(previous: float | None, current: float) -> float:
    return current if previous is None else (previous + current) / 2


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def apply_voice_affect(
    memory: LearningMemory, affect: str, learning_request: str = "none", topic: str | None = None
) -> LearningMemory:
    """Persist only the bounded affect derived from a transient voice doubt."""
    if affect not in {"anxious", "neutral", "confident"}:
        raise ValueError("Voice affect must be anxious, neutral, or confident.")
    if learning_request not in {"slower", "worked_example", "ready", "none"}:
        raise ValueError("Voice learning request is invalid.")

    updated = memory.model_copy(deep=True)
    profile = updated.affective_profile
    inferred = profile.inferred
    profile.voice_affect = affect  # type: ignore[assignment]
    profile.voice_affect_history.append(affect)  # type: ignore[arg-type]
    updated.session_meta.voice_learning_request = learning_request  # type: ignore[assignment]
    event_kind = learning_request if learning_request in {"slower", "worked_example"} else "voice_doubt"
    updated.session_meta.help_seeking_events = (updated.session_meta.help_seeking_events + [HelpSeekingEvent(kind=event_kind, topic=topic or updated.knowledge_profile.concept_graph_position.current_node)])[-30:]
    _refresh_lesson_pulse(updated)

    if affect == "anxious":
        inferred.stress_signal = _clamp(inferred.stress_signal + 0.15)
        inferred.engagement_score = _clamp(inferred.engagement_score - 0.05)
        inferred.self_efficacy_score = _clamp(inferred.self_efficacy_score - 0.10)
    elif affect == "confident":
        inferred.stress_signal = _clamp(inferred.stress_signal - 0.05)
        inferred.engagement_score = _clamp(inferred.engagement_score + 0.05)
        inferred.self_efficacy_score = _clamp(inferred.self_efficacy_score + 0.10)

    inferred.stress_history.append(inferred.stress_signal)
    return updated


def _validate_matching_response_counts(
    submission: CheckResponseSubmission,
    interpretation: CheckResponseInterpretation,
) -> None:
    if len(submission.answers) != len(interpretation.answers):
        raise ValueError("The interpretation must cover every submitted answer.")
