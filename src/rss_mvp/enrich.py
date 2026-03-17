from typing import Iterable, Tuple

import httpx
import trafilatura

from .db import update_item_content


HEADERS = {
    "User-Agent": "rss-content-mvp/0.1 (+OpenClaw)"
}


def fetch_article_text(url: str, timeout: int = 20) -> str:
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
            downloaded = trafilatura.extract(
                resp.text,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
            return (downloaded or "").strip()
    except Exception:
        return ""


def enrich_rows(rows: Iterable[dict]) -> Tuple[int, int]:
    updated = 0
    skipped = 0
    for row in rows:
        if row.get("content_text") and len(row.get("content_text", "")) >= 300:
            skipped += 1
            continue
        text = fetch_article_text(row.get("link", ""))
        if not text:
            skipped += 1
            continue
        update_item_content(row["id"], text)
        updated += 1
    return updated, skipped
