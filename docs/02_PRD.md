# MyPedia — Product Requirements Document

## Problem
India's education system optimizes for marks, not understanding, and has almost no infrastructure to notice *how* a specific student is struggling — cognitively or psychologically — until it becomes a crisis. Teachers can't personalize at scale; parents see grades, not the reasoning behind them.

## Users
- **Primary**: Students (any grade/subject, demoed on one topic) who want to actually learn a concept, not just pass a test.
- **Secondary**: Parents/teachers who want visibility into how a student is doing — academically and psychologically — without needing to ask.

## Vision
An adaptive learning system that assesses a student's knowledge, pacing, and psychological state *as it teaches* — not via a separate quiz — and adjusts what and how it teaches accordingly. "A personalized teacher who knows you fully."

## MVP Scope (build this)
1. One demo subject/topic with a small concept graph (5-8 nodes).
2. Adaptive diagnostic: branching pre-assessment that places the student on the concept graph and takes a first affective read.
3. Learning Memory: persistent student state (knowledge, pacing, affective, ai_desc) — global object with a `subject_id` field (not fully per-subject architecture yet).
4. Teaching loop: Educator (GPT-5.6) generates a teaching turn adapted to current state → short low-stakes check → Strategy Engine updates state deterministically → decides next move.
5. Two demo personas (e.g. fast-confident vs. slow-anxious) that visibly receive different teaching paths, chunk sizes, and tone.
6. Simple dashboard: student view (mastery + engagement only) and parent/teacher view (full meters + ai_desc + stress trend).

## Explicitly NOT building this week
- Multi-subject / full per-subject profile architecture (schema supports it later via `subject_id`, logic doesn't need it now)
- Long-term memory decay logic
- Real user auth / production security hardening
- Content library beyond the one demo topic
- Mobile app — web only

## Success Metrics (for demo)
- Two personas visibly get different teaching content/pacing/tone from the same starting question.
- Mastery score moves demonstrably (e.g. 30%→70%+) within a session.
- ai_desc / stress signal changes visibly in response to simulated struggle.
- Judges can see *why* the system did what it did (Strategy Engine rules are inspectable, not a black box).

## Guiding principle
"Would a great human teacher do this?" — if no, don't build it, however impressive it looks.
