FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Browser recordings are converted to Gemini-compatible WAV by the backend.
RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY db ./db
COPY setup_database.py ./

EXPOSE 8000

# The schema is idempotent, so this safely prepares a fresh managed Postgres
# database before the service starts. Render supplies PORT at runtime.
CMD ["sh", "-c", "python setup_database.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
