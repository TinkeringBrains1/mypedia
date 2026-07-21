"""Run the inspectable MyPedia two-persona MVP demonstration.

Default mode shows the deterministic Strategy decisions without calling Gemini.
Use ``--live`` to also generate the two real Educator teaching turns.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from app.demo.personas import get_demo_personas
from app.services.educator import GeminiEducator
from app.services.strategy_engine import decide_next_move


def build_demo_report(live: bool = False) -> list[dict[str, Any]]:
    """Build a comparison report for the two documented demo personas."""
    educator = GeminiEducator.from_environment() if live else None
    report: list[dict[str, Any]] = []

    for persona in get_demo_personas():
        memory = persona.learning_memory
        instruction = decide_next_move(memory)
        entry: dict[str, Any] = {
            "persona": persona.name,
            "scenario": persona.scenario,
            "shared_starting_node": memory.knowledge_profile.concept_graph_position.current_node,
            "learning_signals": {
                "mastery_history": memory.knowledge_profile.mastery_history,
                "stress_signal": memory.affective_profile.inferred.stress_signal,
                "preferred_chunk_size": memory.cognitive_pacing_profile.preferred_chunk_size,
            },
            "strategy_instruction": instruction.model_dump(),
        }
        if educator is not None:
            entry["teaching_turn"] = educator.generate_teaching_turn(
                memory, instruction
            ).model_dump()
        report.append(entry)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MyPedia MVP demo.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Generate teaching content with Gemini (uses GEMINI_API_KEY).",
    )
    args = parser.parse_args()
    print(json.dumps(build_demo_report(live=args.live), indent=2))


if __name__ == "__main__":
    main()
