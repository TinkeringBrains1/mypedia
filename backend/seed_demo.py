"""Persist the two documented MyPedia demo personas to DATABASE_URL."""

from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv

from app.demo.personas import get_demo_personas
from app.repositories.learning_memory_repository import PostgresLearningMemoryRepository


def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required. Add it to the local .env file.")

    with psycopg.connect(database_url) as connection:
        repository = PostgresLearningMemoryRepository(connection)
        for persona in get_demo_personas():
            repository.save(persona.learning_memory)
    print("Seeded fast-confident and slow-anxious demo Learning Memories.")


if __name__ == "__main__":
    main()
