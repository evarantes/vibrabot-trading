from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("codexiaauditor.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
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

