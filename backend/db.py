"""The SQLite database, seeded from the business data in data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    kind TEXT NOT NULL,
    id TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (kind, id)
);
CREATE TABLE IF NOT EXISTS work (
    claim_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    decision TEXT,
    payout REAL,
    explanation TEXT,
    policy_section TEXT,
    decided_at TEXT,
    signed_off_by TEXT,
    signed_off_at TEXT,
    paid_amount REAL,
    paid_at TEXT
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    at TEXT NOT NULL,
    text TEXT NOT NULL
);
"""

# (kind, file, id field) for the files that are plain lists
SEEDS = [
    ("claims", "claims.json", "claim_id"),
    ("policies", "policies.json", "policy_id"),
    ("customers", "customers.json", "customer_id"),
    ("handlers", "handlers.json", "handler_id"),
]


def db_path() -> str:
    """Return the database file, from UNDERCOVER_DB or next to this module."""
    return os.environ.get("UNDERCOVER_DB", str(Path(__file__).parent / "undercover.db"))


def seed_rows() -> Iterator[tuple[str, str, str]]:
    """Yield every (kind, id, json) row the database starts from."""
    for kind, file, id_field in SEEDS:
        for item in json.loads((DATA / file).read_text(encoding="utf-8")):
            yield kind, item[id_field], json.dumps(item)
    plans = json.loads((DATA / "plans.json").read_text(encoding="utf-8"))
    for plan in plans["plans"]:
        yield "plans", plan["plan"], json.dumps(plan)
    company = json.loads((DATA / "company.json").read_text(encoding="utf-8"))
    yield "company", "company", json.dumps(company)


def connect() -> sqlite3.Connection:
    """Open the database, creating and seeding it when it is empty."""
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    if conn.execute("SELECT 1 FROM records LIMIT 1").fetchone() is None:
        conn.executemany("INSERT INTO records VALUES (?, ?, ?)", seed_rows())
        conn.commit()
    return conn
