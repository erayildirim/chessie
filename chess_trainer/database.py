"""SQLite access layer.

All queries use parameter binding (``?`` placeholders); user input is never
formatted into SQL strings.
"""
import json
import os
import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    username         TEXT NOT NULL UNIQUE,
    password         TEXT NOT NULL,
    name             TEXT,
    surname          TEXT,
    elo              INTEGER DEFAULT 1500,
    eloHistory       TEXT DEFAULT '',
    studyElo         INTEGER DEFAULT 1500,
    studyEloHistory  TEXT DEFAULT '',
    completedStudies TEXT DEFAULT '',
    incorrectStudies TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS games (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    userId  INTEGER REFERENCES users(id),
    sonuc   INTEGER,
    eskiElo INTEGER,
    yeniElo INTEGER,
    pgn     TEXT
);
CREATE TABLE IF NOT EXISTS studies (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    type     TEXT,
    rating   INTEGER,
    fen      TEXT,
    solution TEXT
);
"""

_initialized = False


def connect():
    """Open a connection to the app database (creating/seeding it if needed)."""
    global _initialized
    if not _initialized:
        init_db()
        _initialized = True
    return sqlite3.connect(config.DB_PATH)


def init_db():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    try:
        conn.executescript(SCHEMA)
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        except sqlite3.IntegrityError:
            pass  # legacy database with duplicate usernames; UNIQUE check is still done in code
        _seed_or_update_puzzles(conn)
        conn.commit()
    finally:
        conn.close()


def _seed_or_update_puzzles(conn):
    """Load puzzles from data/puzzles.json (inserts new ones, fixes old solutions)."""
    if not os.path.isfile(config.PUZZLES_JSON):
        return
    with open(config.PUZZLES_JSON, encoding="utf-8") as f:
        puzzles = json.load(f)
    conn.executemany(
        """INSERT INTO studies (id, type, rating, fen, solution) VALUES (:id, :type, :rating, :fen, :solution)
           ON CONFLICT(id) DO UPDATE SET type=excluded.type, rating=excluded.rating,
                                         fen=excluded.fen, solution=excluded.solution""",
        puzzles,
    )


def split_ids(value):
    """Parse a comma separated id list stored in the users table."""
    return [v for v in (value or "").split(",") if v.strip()]


def parse_int_list(value):
    out = []
    for v in split_ids(value):
        try:
            out.append(int(v))
        except ValueError:
            pass
    return out
