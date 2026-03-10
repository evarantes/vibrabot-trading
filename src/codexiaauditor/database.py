from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import psycopg
from psycopg.rows import dict_row

DB_PATH = Path("codexiaauditor.db")  # fallback para testes locais


def get_db_engine() -> str:
    engine = os.getenv("CODEXIAAUDITOR_DB_ENGINE", "postgres").strip().lower()
    if engine in {"postgres", "postgresql"}:
        return "postgres"
    if engine == "sqlite":
        return "sqlite"
    raise ValueError("CODEXIAAUDITOR_DB_ENGINE deve ser 'postgres' ou 'sqlite'.")


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/codexiaauditor",
    )


def get_sqlite_path() -> Path:
    return Path(os.getenv("CODEXIAAUDITOR_SQLITE_PATH", str(DB_PATH)))


def adapt_query(query: str) -> str:
    if get_db_engine() == "postgres":
        return query.replace("?", "%s")
    return query


def _adapt_params(params: Sequence[Any] | None) -> Sequence[Any]:
    return tuple(params or ())


def execute(conn: Any, query: str, params: Sequence[Any] | None = None) -> Any:
    return conn.execute(adapt_query(query), _adapt_params(params))


@contextmanager
def get_connection() -> Iterator[Any]:
    engine = get_db_engine()
    if engine == "postgres":
        conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    else:
        conn = sqlite3.connect(get_sqlite_path())
        conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    if get_db_engine() == "postgres":
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres() -> None:
    with get_connection() as conn:
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS items (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                par_level INTEGER NOT NULL DEFAULT 0,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
        )
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS movements (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                item_id BIGINT NOT NULL REFERENCES items(id),
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                movement_date DATE NOT NULL,
                source_ref TEXT,
                note TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
        )
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS inventory_counts (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                item_id BIGINT NOT NULL REFERENCES items(id),
                count_date DATE NOT NULL,
                counted_stock INTEGER NOT NULL DEFAULT 0 CHECK(counted_stock >= 0),
                counted_laundry INTEGER NOT NULL DEFAULT 0 CHECK(counted_laundry >= 0),
                counted_in_use INTEGER NOT NULL DEFAULT 0 CHECK(counted_in_use >= 0),
                note TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_id, count_date)
            );
            """,
        )


def _init_sqlite() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                par_level INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                movement_date TEXT NOT NULL,
                source_ref TEXT,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items(id)
            );

            CREATE TABLE IF NOT EXISTS inventory_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                count_date TEXT NOT NULL,
                counted_stock INTEGER NOT NULL DEFAULT 0 CHECK(counted_stock >= 0),
                counted_laundry INTEGER NOT NULL DEFAULT 0 CHECK(counted_laundry >= 0),
                counted_in_use INTEGER NOT NULL DEFAULT 0 CHECK(counted_in_use >= 0),
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_id, count_date),
                FOREIGN KEY (item_id) REFERENCES items(id)
            );
            """
        )

