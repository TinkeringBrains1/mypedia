-- MyPedia MVP: Learning Memory is the only persistent student-state record.
-- One record per student is intentional for this build. subject_id is retained
-- for the future migration to true per-subject profiles.

CREATE TABLE IF NOT EXISTS learning_memories (
    student_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    memory JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS learning_memories_subject_id_idx
    ON learning_memories (subject_id);
