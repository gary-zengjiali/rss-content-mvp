import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Tuple

from .config import DB_PATH, ensure_dirs
from .models import Item


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    published_at TEXT NOT NULL,
    author TEXT,
    summary TEXT,
    content_text TEXT,
    category TEXT,
    dedupe_key TEXT NOT NULL,
    title_key TEXT NOT NULL,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dedupe_key),
    UNIQUE(source_id, title_key, published_at)
);

CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_source_id ON items(source_id);
"""


@contextmanager
def get_conn():
    ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_items(items: Iterable[Item]) -> Tuple[int, int]:
    inserted = 0
    skipped = 0
    sql = """
    INSERT OR IGNORE INTO items (
        source_id, title, link, published_at, author, summary,
        content_text, category, dedupe_key, title_key, fetched_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
    """
    with get_conn() as conn:
        for item in items:
            cur = conn.execute(
                sql,
                (
                    item.source_id,
                    item.title,
                    item.link,
                    item.published_at,
                    item.author,
                    item.summary,
                    item.content_text,
                    item.category,
                    item.dedupe_key,
                    item.title_key,
                    item.fetched_at,
                ),
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
    return inserted, skipped


def fetch_items_by_date(date_str: str) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT *
            FROM items
            WHERE substr(published_at, 1, 10) = ?
            ORDER BY published_at DESC
            """,
            (date_str,),
        )
        return cur.fetchall()


def update_item_content(item_id: int, content_text: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE items SET content_text = ? WHERE id = ?",
            (content_text, item_id),
        )


def fetch_recent_items(limit: int = 100) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM items ORDER BY published_at DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()
