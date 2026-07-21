"""Deterministic teaching-move selection for the MyPedia MVP.

The Strategy Engine reads Learning Memory and emits an instruction for the
Educator. It never calls an LLM, reads the database, or mutates student state.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.content.math_algebra import next_math_algebra_node
from app.schemas.learning_memory import LearningMemory


LOW_ENGAGEMENT = 0.35
# Readiness still combines demonstrated accuracy (60%) and low stress (40%),
# but this lower threshold keeps the small MVP graph moving in one session.
READINESS_TO_ADVANCE = 0.60

StrategyAction = Literal[
    "confidence_building_easy_win", "reteach", "continue", "advance"
]
ChunkSize = Literal["small", "medium", "large"]
Tone = Literal["supportive", "reassuring", "patient", "challenging", "encouraging", "neutral"]
WorkedExampleDensity = Literal["standard", "high"]
SessionLength = Literal["standard", "short"]


class StrategyInstruction(BaseModel):
    """An inspectable, deterministic direction passed to the Educator."""

    model_config = ConfigDict(frozen=True)

    action: StrategyAction
    node: str
    chunk_size: ChunkSize
    tone: Tone
    visible_score: bool = True
    worked_example_density: WorkedExampleDensity = "standard"
    offer_stretch_problem: bool = False
    session_length: SessionLength = "standard"
    example_interest_tags: list[str] = Field(default_factory=list)
    requires_low_stakes_check: bool = False
    rule_id: str
    reason: str

    @property
    def action_key(self) -> str:
        """Value the orchestrator records in ``session_meta.last_orchestrator_action``."""
        return f"{self.action}:{self.node}"


def decide_next_move(memory: LearningMemory) -> StrategyInstruction:
    """Return the first applicable documented Strategy Engine rule.

    Rule order is intentional: learner wellbeing and remediation take
    precedence over acceleration. The function is pure, making each decision
    reproducible from one Learning Memory snapshot.
    """
    position = memory.knowledge_profile.concept_graph_position
    pacing = memory.cognitive_pacing_profile
    affective = memory.affective_profile
    inferred = affective.inferred

    if inferred.stress_signal > 0.7:
        return _instruction(
            action="confidence_building_easy_win",
            node=position.current_node,
            chunk_size="small",
            tone="supportive",
            rule_id="high_stress_easy_win",
            reason="Stress is above 0.7, so build confidence before continuing.",
        )

    if affective.mismatch_flag:
        return _instruction(
            action="continue",
            node=position.current_node,
            chunk_size=pacing.preferred_chunk_size,
            tone="reassuring",
            visible_score=False,
            rule_id="affective_mismatch_lower_stakes",
            reason="Reported and inferred affect differ, so keep this turn low-stakes.",
        )

    if memory.session_meta.voice_learning_request in {"slower", "worked_example"}:
        request = memory.session_meta.voice_learning_request
        return _instruction(
            action="continue", node=position.current_node, chunk_size="small", tone="patient",
            worked_example_density="high", rule_id="voice_requested_support",
            reason="The student asked by voice for a slower explanation or another worked example.",
        )

    if memory.session_meta.lesson_pulse.accuracy_trend == "declining":
        return _instruction(
            action="continue", node=memory.session_meta.lesson_pulse.support_topic or position.current_node,
            chunk_size="small", tone="patient", worked_example_density="high",
            rule_id="declining_accuracy_extra_support",
            reason="Recent accuracy declined, so revisit this topic with extra care and a worked example.",
        )

    struggling_node = _unrechecked_struggling_node(memory)
    if struggling_node is not None:
        return _instruction(
            action="reteach",
            node=struggling_node,
            chunk_size="small",
            tone="supportive",
            requires_low_stakes_check=True,
            rule_id="struggling_prerequisite_recheck",
            reason="Re-teach and check the struggling prerequisite once before advancing.",
        )

    if memory.session_meta.pending_lesson_node is not None:
        return _instruction(
            action="advance",
            node=memory.session_meta.pending_lesson_node,
            chunk_size="small",
            tone="supportive",
            worked_example_density="high",
            rule_id="resume_after_prerequisite_support",
            reason="Resume the planned lesson slowly after prerequisite support.",
        )

    if pacing.retry_rate > 0.4:
        return _instruction(
            action="continue",
            node=position.current_node,
            chunk_size=_smaller_chunk_size(pacing.preferred_chunk_size),
            tone="patient",
            worked_example_density="high",
            rule_id="high_retry_more_scaffolding",
            reason="Retry rate is above 0.4, so reduce chunk size and add worked examples.",
        )

    readiness_score = _readiness_score(memory)
    if readiness_score is not None and readiness_score >= READINESS_TO_ADVANCE:
        next_node = _next_node(memory)
        return _instruction(
            action="advance",
            node=next_node,
            chunk_size=pacing.preferred_chunk_size,
            tone="challenging",
            offer_stretch_problem=True,
            rule_id="mastery_stress_readiness_advance",
            reason=(
                "Readiness from recent mastery (60%) and low stress (40%) is at "
                f"least {READINESS_TO_ADVANCE:.2f}."
            ),
        )

    if (
        inferred.goal_orientation == "avoidant"
        and inferred.engagement_score < LOW_ENGAGEMENT
    ):
        return _instruction(
            action="continue",
            node=position.current_node,
            chunk_size=pacing.preferred_chunk_size,
            tone="encouraging",
            session_length="short",
            example_interest_tags=memory.interest_context.tags,
            rule_id="avoidant_low_engagement_shorten_session",
            reason="Avoidant goal orientation and low engagement call for a shorter, relevant turn.",
        )

    return _instruction(
        action="continue",
        node=position.current_node,
        chunk_size=pacing.preferred_chunk_size,
        tone="neutral",
        rule_id="default_continue",
        reason="No higher-priority support or readiness rule applies, so continue this concept.",
    )


def _unrechecked_struggling_node(memory: LearningMemory) -> str | None:
    """Return one prerequisite for a single re-teach/check iteration.

    A non-empty struggling set gets one re-check turn, using its first node as
    the focus. The existing ``last_orchestrator_action`` field then prevents a
    loop through the remaining nodes; the next decision advances. The
    orchestration layer records ``action_key`` after dispatching an instruction;
    this function itself has no side effects.
    """
    struggling_nodes = memory.knowledge_profile.concept_graph_position.struggling_nodes
    if not struggling_nodes:
        return None

    last_action = memory.session_meta.last_orchestrator_action
    if last_action is not None and last_action.startswith("reteach:"):
        return None

    return struggling_nodes[0]


def _smaller_chunk_size(chunk_size: ChunkSize) -> ChunkSize:
    return {"large": "medium", "medium": "small", "small": "small"}[chunk_size]


def _readiness_score(memory: LearningMemory) -> float | None:
    """Return the approved 60% mastery / 40% inverse-stress readiness score."""
    recent_history = memory.knowledge_profile.mastery_history[-2:]
    if len(recent_history) < 2:
        return None

    recent_mastery = sum(recent_history) / len(recent_history)
    stress = memory.affective_profile.inferred.stress_signal
    return 0.60 * recent_mastery + 0.40 * (1 - stress)


def _next_node(memory: LearningMemory) -> str:
    """Keep the final node active for a stretch turn when no later node exists."""
    current_node = memory.knowledge_profile.concept_graph_position.current_node
    return next_math_algebra_node(current_node) or current_node


def _instruction(
    *,
    action: StrategyAction,
    node: str,
    chunk_size: ChunkSize,
    tone: Tone,
    rule_id: str,
    reason: str,
    visible_score: bool = True,
    worked_example_density: WorkedExampleDensity = "standard",
    offer_stretch_problem: bool = False,
    session_length: SessionLength = "standard",
    example_interest_tags: list[str] | None = None,
    requires_low_stakes_check: bool = False,
) -> StrategyInstruction:
    return StrategyInstruction(
        action=action,
        node=node,
        chunk_size=chunk_size,
        tone=tone,
        visible_score=visible_score,
        worked_example_density=worked_example_density,
        offer_stretch_problem=offer_stretch_problem,
        session_length=session_length,
        example_interest_tags=example_interest_tags or [],
        requires_low_stakes_check=requires_low_stakes_check,
        rule_id=rule_id,
        reason=reason,
    )
