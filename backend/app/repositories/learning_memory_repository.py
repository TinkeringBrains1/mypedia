"""PostgreSQL access for the single Learning Memory record per student."""

from __future__ import annotations

from typing import Protocol

from psycopg import Connection
from psycopg.types.json import Jsonb

from app.schemas.learning_memory import LearningMemory


class LearningMemoryReader(Protocol):
    def get_relevant_state(self, student_id: str, subject_id: str) -> LearningMemory:
        """Return the canonical state used to assemble an Educator context."""


class LearningMemoryStore(LearningMemoryReader, Protocol):
    def save(self, memory: LearningMemory) -> None:
        """Persist the canonical Learning Memory object."""


class PostgresLearningMemoryRepository:
    """A thin adapter; strategy and context assembly do not live here."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_relevant_state(self, student_id: str, subject_id: str) -> LearningMemory:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT memory
                FROM learning_memories
                WHERE student_id = %s AND subject_id = %s
                """,
                (student_id, subject_id),
            )
            row = cursor.fetchone()

        if row is None:
            raise KeyError(f"No Learning Memory exists for student '{student_id}'.")

        return LearningMemory.model_validate(row[0])

    def save(self, memory: LearningMemory) -> None:
        """Create or replace the student's one canonical memory object."""
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO learning_memories (student_id, subject_id, memory)
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id) DO UPDATE
                SET subject_id = EXCLUDED.subject_id,
                    memory = EXCLUDED.memory,
                    updated_at = NOW()
                """,
                (
                    memory.student_id,
                    memory.subject_id,
                    Jsonb(memory.model_dump(mode="json")),
                ),
            )
        self._connection.commit()
