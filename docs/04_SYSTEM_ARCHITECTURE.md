# MyPedia — System Architecture

## Components (2, not 4)

### 1. Learning Memory (data layer)
The single source of truth for a student's state. Global object per student, with a `subject_id` field so it can extend to true per-subject profiles post-hackathon without a schema rewrite.

```json
{
  "student_id": "stu_0231",
  "subject_id": "math_algebra",
  "knowledge_profile": {
    "concept_graph_position": {
      "current_node": "linear_equations_one_var",
      "mastered_nodes": [],
      "struggling_nodes": [],
      "not_yet_attempted": []
    },
    "mastery_score": 0.0,
    "mastery_history": []
  },
  "cognitive_pacing_profile": {
    "avg_response_latency_sec": null,
    "hint_usage_rate": 0.0,
    "retry_rate": 0.0,
    "scaffold_level": "medium",
    "preferred_chunk_size": "medium"
  },
  "affective_profile": {
    "self_reported": { "last_checkin": null, "checkin_history": [] },
    "inferred": {
      "engagement_score": 0.5,
      "stress_signal": 0.0,
      "self_efficacy_score": 0.5,
      "goal_orientation": "mastery",
      "mindset_signal": "growth"
    },
    "mismatch_flag": false
  },
  "interest_context": { "tags": [], "source": "onboarding_survey" },
  "ai_desc": { "summary": "", "generated_at": null },
  "session_meta": { "total_sessions": 0, "total_time_min": 0, "last_orchestrator_action": null }
}
```

Context assembly (formerly a separate "Context Engine") is just a function: `get_relevant_state(student_id, subject_id)` that reads Learning Memory. No separate agent.

### 2. Strategy Engine (deterministic, rule-based — NOT an LLM call)
Reads Learning Memory, decides the next teaching move. Small rule set, kept tight for demo reliability and explainability:

1. `stress_signal > 0.7` → insert confidence-building easy win before continuing
2. `mismatch_flag == true` → lower stakes framing, no visible score this turn
3. `struggling_nodes` non-empty on current path → re-teach prerequisite before advancing
4. `retry_rate > 0.4` → decrease `preferred_chunk_size`, increase worked-example density
5. `accuracy high + latency low` on last 2 checks → advance node, offer stretch problem
6. `goal_orientation == "avoidant"` + low engagement → shorten session, interest-tag next example
7. default → advance normally

Output of Strategy Engine = an instruction object (e.g. `{action: "reteach", node: "fractions_in_equations", chunk_size: "small", tone: "supportive"}`) passed to the Educator.

### 3. the Educator (GPT-5.6)
Receives: current concept node + Strategy Engine instruction + `ai_desc` (compact narrative summary of the student).
Produces:
- Teaching content for the turn (adapted per instruction)
- Check questions (2-3, low-stakes)
- End-of-turn interpretation of the student's response → feeds back into Learning Memory update
- Reflection Mode: regenerates `ai_desc` after N turns
- Parental/teacher advice text (on demand, not every turn)

GPT-5.6 never decides *what* to teach next (that's Strategy Engine) — only *how* to teach it and *how to interpret* what happened. This is the "genuinely hard to hard-code" test from the Rule Lock.

## Data flow (one turn)
```
Learning Memory (read)
      ↓
Strategy Engine (deterministic decision)
      ↓
the Educator (GPT-5.6: generate content + questions)
      ↓
Student responds
      ↓
the Educator (GPT-5.6: interpret response)
      ↓
Learning Memory (write: mastery, pacing, affective updates)
      ↓
[every N turns] the Educator: regenerate ai_desc (Reflection Mode)
```

## Stack
- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI (Python)
- DB: PostgreSQL (Supabase)
- LLM orchestration: Python, calling GPT-5.6 directly for Educator tasks only
