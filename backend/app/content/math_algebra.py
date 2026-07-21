"""MyPedia's single MVP subject: introductory algebra."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


MATH_ALGEBRA_SUBJECT_ID = "math_algebra"


class DiagnosticOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    text: str


class DiagnosticQuestion(BaseModel):
    """A multiple-choice diagnostic at one point in the MVP concept graph."""

    model_config = ConfigDict(frozen=True)

    id: str
    concept_node: str
    prompt: str
    options: list[DiagnosticOption] = Field(min_length=3, max_length=3)
    correct_option_id: str


MATH_ALGEBRA_DIAGNOSTIC: tuple[DiagnosticQuestion, ...] = (
    DiagnosticQuestion(
        id="negative_numbers",
        concept_node="negative_numbers",
        prompt="What is -6 + 9?",
        options=[
            DiagnosticOption(id="a", text="3"),
            DiagnosticOption(id="b", text="-15"),
            DiagnosticOption(id="c", text="-3"),
        ],
        correct_option_id="a",
    ),
    DiagnosticQuestion(
        id="distributive_property",
        concept_node="distributive_property",
        prompt="Which expression is equivalent to 4(x + 3)?",
        options=[
            DiagnosticOption(id="a", text="4x + 12"),
            DiagnosticOption(id="b", text="4x + 3"),
            DiagnosticOption(id="c", text="x + 12"),
        ],
        correct_option_id="a",
    ),
    DiagnosticQuestion(
        id="combining_like_terms",
        concept_node="combining_like_terms",
        prompt="Simplify 3x + 5x - 2.",
        options=[
            DiagnosticOption(id="a", text="8x - 2"),
            DiagnosticOption(id="b", text="8x + 2"),
            DiagnosticOption(id="c", text="15x"),
        ],
        correct_option_id="a",
    ),
    DiagnosticQuestion(
        id="one_step_equations",
        concept_node="one_step_equations",
        prompt="Solve: x - 5 = 9.",
        options=[
            DiagnosticOption(id="a", text="x = 14"),
            DiagnosticOption(id="b", text="x = 4"),
            DiagnosticOption(id="c", text="x = -14"),
        ],
        correct_option_id="a",
    ),
    DiagnosticQuestion(
        id="two_step_equations",
        concept_node="two_step_equations",
        prompt="Solve: 3x + 4 = 19.",
        options=[
            DiagnosticOption(id="a", text="x = 5"),
            DiagnosticOption(id="b", text="x = 7"),
            DiagnosticOption(id="c", text="x = 23"),
        ],
        correct_option_id="a",
    ),
    DiagnosticQuestion(
        id="variables_both_sides",
        concept_node="variables_both_sides",
        prompt="Solve: 4x + 3 = 2x + 13.",
        options=[
            DiagnosticOption(id="a", text="x = 5"),
            DiagnosticOption(id="b", text="x = 8"),
            DiagnosticOption(id="c", text="x = -5"),
        ],
        correct_option_id="a",
    ),
    DiagnosticQuestion(
        id="fractions_in_equations",
        concept_node="fractions_in_equations",
        prompt="Solve: x/3 + 2 = 6.",
        options=[
            DiagnosticOption(id="a", text="x = 12"),
            DiagnosticOption(id="b", text="x = 4"),
            DiagnosticOption(id="c", text="x = 18"),
        ],
        correct_option_id="a",
    ),
)

MATH_ALGEBRA_NODES: tuple[str, ...] = tuple(
    question.concept_node for question in MATH_ALGEBRA_DIAGNOSTIC
)

MATH_ALGEBRA_PREREQUISITES: dict[str, str | None] = {
    "negative_numbers": None,
    "distributive_property": "negative_numbers",
    "combining_like_terms": "distributive_property",
    "one_step_equations": "combining_like_terms",
    "two_step_equations": "one_step_equations",
    "variables_both_sides": "two_step_equations",
    "fractions_in_equations": "variables_both_sides",
}


def next_math_algebra_node(node: str) -> str | None:
    """Return the next node in the one MVP graph, if one exists."""
    try:
        index = MATH_ALGEBRA_NODES.index(node)
    except ValueError as exc:
        raise ValueError(f"Unknown math_algebra concept node '{node}'.") from exc

    if index == len(MATH_ALGEBRA_NODES) - 1:
        return None
    return MATH_ALGEBRA_NODES[index + 1]


def is_math_algebra_complete(mastered_nodes: list[str]) -> bool:
    """Whether every concept in the MVP algebra graph is mastered."""
    return set(MATH_ALGEBRA_NODES).issubset(mastered_nodes)


def prerequisite_for_math_algebra_node(node: str) -> str | None:
    """Return the authored immediate prerequisite for an MVP algebra lesson."""
    try:
        return MATH_ALGEBRA_PREREQUISITES[node]
    except KeyError as exc:
        raise ValueError(f"Unknown math_algebra concept node '{node}'.") from exc
