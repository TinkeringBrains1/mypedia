# MyPedia — Design System

## Direction
The Educator is an AI, so the core interaction should feel like a chat interface (ChatGPT/Claude-style) — not a quiz app, not a dashboard-first product. The chat *is* the lesson. Mastery/affective visualization lives alongside the conversation, not instead of it.

## Color
| Token | Hex | Use |
|---|---|---|
| `bg-primary` | `#1C2B3A` | App background, sidebar |
| `surface` | `#F5EFE4` | Chat message bubbles, cards, main content area |
| `accent-mastery` | `#C77D3C` | Progress, mastered concepts, primary CTA |
| `accent-growth` | `#5B8C7B` | Positive affective states, growth signals |
| `accent-attention` | `#B85450` | Stress/struggle signals — muted, never alarm-red |
| `text-primary` | `#241C15` | Body text on light surfaces |
| `text-inverse` | `#F5EFE4` | Text on dark surfaces |

## Typography
- **Display / headings**: Fraunces (or Lora) — humanist serif, gives warmth, reads like a real tutor rather than software.
- **Body / UI / chat text**: Inter — clean, highly legible at small sizes, standard for chat interfaces.
- **Data / labels**: Inter, smaller weight, used sparingly for meters and timestamps only.

## Theme feel
Warm, steady, human — like a good tutor's study, not a gamified app and not a cold admin dashboard. No childish iconography, no harsh red error states (this is about a kid's psychological state, not a form validation error).

## Structure — Chat-first layout

```
┌─────────────┬───────────────────────────────────┬──────────────┐
│             │                                     │              │
│  Sidebar    │         Chat with Educator          │  Profile     │
│             │                                     │  Panel       │
│ - Subjects  │  [Educator]: Let's look at...       │              │
│   applied   │  [Student]: okay...                 │ Concept      │
│ - New       │  [Educator]: adapts based on        │ graph (dots  │
│   subject   │   Strategy Engine decision           │ fill in as   │
│ - Session   │                                     │ mastered)    │
│   history   │  [input box: type or select answer] │              │
│             │                                     │ Mastery: 62% │
│             │                                     │ Engagement:  │
│             │                                     │ steady       │
└─────────────┴───────────────────────────────────┴──────────────┘
```

- **Left sidebar** (dark, `bg-primary`): subjects the student has "applied" to, session history — same pattern as ChatGPT/Claude's conversation list, but listing subjects/topics instead of past chats.
- **Center panel** (light, `surface`): the actual chat — Educator messages and student responses, styled as message bubbles. This is where all teaching content, check questions, and interpretation happens conversationally.
- **Right panel** (light, narrower): live concept-graph visualization (the signature element — nodes fill in `accent-mastery` as mastered) plus mastery/engagement meters only, per PRD student-view scope. No stress/confidence meters here — those are parent/teacher-view only.

## Parent/Teacher view (separate route, not a panel toggle)
Same color/type system, denser layout: full meter set (mastery, confidence, engagement, stress trend over time) plus the current `ai_desc` narrative summary in plain text. No chat interface here — this is a read-only report view, calmer and more clinical in tone.

## Signature element
The concept-graph visualization in the right panel is the one thing to spend design effort on — it's a direct visualization of the Learning Memory schema (mastered / struggling / not-yet-attempted nodes), not decorative. Small radial or tree layout, nodes as dots: filled = mastered, half-filled/dimmed = struggling, outline-only = not yet attempted.

## Copy voice
- Active voice, plain verbs, no filler.
- Educator speaks like a calm tutor, not a corporate assistant — no "Great question!" filler, no exclamation-point enthusiasm.
- Errors/struggle moments are framed neutrally and constructively, never as failure ("Let's look at this differently" not "That's wrong").
