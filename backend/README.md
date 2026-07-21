# Mypedia backend

FastAPI backend for the Mypedia adaptive learning MVP.

## Responsibilities

- Persists the canonical Learning Memory record in PostgreSQL.
- Runs the deterministic Strategy Engine.
- Calls Gemini only for diagnostics, teaching content, answer interpretation, reflection, prerequisite interpretation, and voice-doubt responses.
- Converts browser audio to WAV with `ffmpeg` before sending it to Gemini.

## Setup

From the repository root, create `.env` with:

```env
GEMINI_API_KEY=your_key
DATABASE_URL=postgresql://...
```

Apply the idempotent database schema:

```powershell
..\.venv\Scripts\python.exe setup_database.py
```

Start the API from this directory:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs` and deployment health checks use `/health`.

## Tests

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

## Back4App Containers deployment

`Dockerfile` installs `ffmpeg`, installs Python dependencies, applies `db/schema.sql` through `setup_database.py`, then starts Uvicorn on the platform-provided `PORT` (defaulting to `8000`).

In Back4App Containers:

1. Connect the GitHub repository and select `backend` as the **Root** directory.
2. Keep the Dockerfile at that root (`backend/Dockerfile`) and configure container port `8000`.
3. Set `/health` as the HTTP health-check endpoint when prompted.
4. Add these environment variables in the deployment settings:

```env
GEMINI_API_KEY=...
DATABASE_URL=...
CORS_ORIGINS=https://your-frontend-domain
```

Do not expose `GEMINI_API_KEY` to the frontend.
