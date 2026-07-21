"""Apply the MyPedia Learning Memory schema to DATABASE_URL."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required. Add it to the local .env file.")

    schema_path = Path(__file__).parent / "db" / "schema.sql"
    statements = [statement.strip() for statement in schema_path.read_text().split(";")]
    with psycopg.connect(database_url) as connection:
        for statement in statements:
            if statement:
                connection.execute(statement)
        connection.commit()
    print("Learning Memory schema applied.")


if __name__ == "__main__":
    main()
