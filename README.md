# Mypedia

Mypedia is a hackathon MVP for adaptive Maths learning. It combines a deterministic Strategy Engine with Gemini-generated teaching, checks, diagnostics, and student-support responses.

## What it does

- Starts a student on an adaptive, two-question diagnostic.
- Teaches a small Maths concept graph with prerequisite checks and low-stakes practice.
- Stores Learning Memory in PostgreSQL: mastery, pacing, affect, help-seeking, and session history.
- Supports voice doubts through short browser recordings; only the derived affect is retained.
- Provides resumable student sessions and a parent/teacher dashboard.

## Architecture

Learning Memory is the single persistent model. The deterministic Strategy Engine decides the next concept and teaching strategy. Gemini (`gemini-3.1-flash-lite`) generates and interprets educational content but never chooses curriculum progression.

## Local development

1. Create a PostgreSQL database and copy `.env.example` to `.env`.
2. Set `GEMINI_API_KEY` and `DATABASE_URL` in `.env`.
3. Apply the schema and run the backend:

   ```powershell
   .\.venv\Scripts\python.exe backend\setup_database.py
   cd backend
   ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

4. In another terminal, configure and run the frontend:

   ```powershell
   cd frontend
   Copy-Item .env.local.example .env.local
   npm install
   npm run dev
   ```

Open `http://localhost:3000`. Demo credentials are `user123` / `devpost12345`.

## Deployment

The backend is configured for Render using [render.yaml](render.yaml) and `backend/Dockerfile`; the image includes `ffmpeg` for voice recording conversion. Set `GEMINI_API_KEY`, `DATABASE_URL`, and `CORS_ORIGINS` as Render secrets. Deploy the frontend separately and set `NEXT_PUBLIC_API_BASE_URL` to the public API URL.

## Repository layout

- `frontend/` — Next.js student and parent-facing application.
- `backend/` — FastAPI API, deterministic strategy logic, and Gemini Educator integration.
- `docs/` — product, architecture, design, and implementation guidance.
