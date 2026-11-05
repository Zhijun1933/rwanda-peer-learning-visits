"""Local SQLite store for discovered articles, extractions and qualitative coding.

The database lives at data/tracker.db and is excluded from git: it holds
article texts, which are not redistributed.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from . import DATA_DIR

DB_PATH = DATA_DIR / "tracker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY,
    url             TEXT UNIQUE NOT NULL,
    domain          TEXT NOT NULL,
    discovered_via  TEXT NOT NULL,          -- sitemap | gdelt | gkg | manual
    discovered_at   TEXT NOT NULL,
    hint_title      TEXT,                   -- title seen at discovery time
    status          TEXT NOT NULL DEFAULT 'new',
        -- new | fetched | skipped_robots | skipped_policy | error | irrelevant | candidate
    fetched_at      TEXT,
    http_status     INTEGER,
    title           TEXT,
    pub_date        TEXT,
    language        TEXT,
    text            TEXT,
    relevance       REAL,
    error           TEXT
);

CREATE TABLE IF NOT EXISTS extractions (
    id          INTEGER PRIMARY KEY,
    article_id  INTEGER NOT NULL REFERENCES articles(id),
    method      TEXT NOT NULL,              -- rules | llm
    created_at  TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    UNIQUE (article_id, method)
);

CREATE TABLE IF NOT EXISTS article_visit (
    article_id  INTEGER NOT NULL REFERENCES articles(id),
    visit_id    TEXT NOT NULL,              -- matches data/visits.csv
    PRIMARY KEY (article_id, visit_id)
);

-- Qualitative coding
CREATE TABLE IF NOT EXISTS codes (
    code        TEXT PRIMARY KEY,           -- e.g. "A1"
    name        TEXT NOT NULL,
    parent      TEXT,
    definition  TEXT
);

CREATE TABLE IF NOT EXISTS segments (
    id          INTEGER PRIMARY KEY,
    article_id  INTEGER NOT NULL REFERENCES articles(id),
    code        TEXT NOT NULL REFERENCES codes(code),
    start_char  INTEGER NOT NULL,
    end_char    INTEGER NOT NULL,
    memo        TEXT,
    coder       TEXT,
    created_at  TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def add_article(conn, url: str, via: str, hint_title: str | None = None) -> bool:
    """Insert a discovered URL. Returns True if it was new."""
    url = url.strip()
    domain = urlsplit(url).netloc.lower()
    cur = conn.execute(
        "INSERT OR IGNORE INTO articles (url, domain, discovered_via, discovered_at, hint_title) "
        "VALUES (?, ?, ?, ?, ?)",
        (url, domain, via, now(), hint_title),
    )
    return cur.rowcount == 1
