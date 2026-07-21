# Welcome to MyPedia

You are joining the MyPedia engineering team for OpenAI Build Week.

Before writing any code, read in order:
1. `02_PRD.md` — what we're building and NOT building this week
2. `04_SYSTEM_ARCHITECTURE.md` — the two-component architecture and data flow

## Implementation Rules
- Learning Memory is the single central data model. Don't invent parallel state.
- Strategy Engine is deterministic. Never implement it as an LLM call — it's plain rule logic (if/else or a small rules table) operating on Learning Memory fields.
- GPT-5.6 ("the Educator") is only used for: generating teaching content, generating check questions, interpreting student responses, and regenerating `ai_desc`. It never decides *what* concept to teach next — that's Strategy Engine's job.
- There is no separate "Context Engine" component — context assembly is a plain function that reads Learning Memory, not an agent.
- Do not introduce features outside the MVP scope in `02_PRD.md`, however easy or impressive they seem.
- Learning Memory is global-with-a-`subject_id` for this build — do not build a full per-subject profile system now.
- Litmus test for any new feature or code path: "Would a great human teacher do this?" If no, don't build it.

When uncertain, follow the documentation instead of making assumptions. Ask before deviating from the architecture.

## Build order (suggested)
1. Learning Memory schema + DB setup
2. Strategy Engine rule logic (pure functions, testable without any LLM)
3. Educator prompt + GPT-5.6 integration (teaching content generation)
4. Diagnostic flow (adaptive pre-assessment → seeds Learning Memory)
5. Check-question flow + response interpretation → Learning Memory writes
6. Reflection Mode (ai_desc regeneration)
7. Student dashboard (mastery + engagement only)
8. Parent/teacher dashboard (full meters + ai_desc + trends)
9. Two-persona demo data + demo script
