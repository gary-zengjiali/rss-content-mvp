import hashlib
import html
import re
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlsplit, urlunsplit

import feedparser
from dateutil import parser as dtparser

from .models import Item, Source


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = TAG_RE.sub(" ", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()


def normalize_title_key(title: str) -> str:
    title = normalize_text(title).lower()
    title = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", title)
    return title.strip("-")


def normalize_link(url: str) -> str:
    try:
        parts = urlsplit(url)
        clean = parts._replace(query="", fragment="")
        return urlunsplit(clean)
    except Exception:
        return url


def make_dedupe_key(link: str, title: str) -> str:
    base = normalize_link(link) or normalize_title_key(title)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def parse_published(entry) -> str:
    candidates = [
        getattr(entry, "published", None),
        getattr(entry, "updated", None),
        entry.get("published"),
        entry.get("updated"),
    ]
    for raw in candidates:
        if raw:
            try:
                dt = dtparser.parse(raw)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                continue
    return datetime.now(timezone.utc).isoformat()


def entry_content_text(entry) -> str:
    if entry.get("content"):
        chunks = [normalize_text(c.get("value", "")) for c in entry.get("content", [])]
        text = "\n".join(filter(None, chunks))
        if text:
            return text
    return normalize_text(entry.get("summary", ""))


def parse_feed(source: Source) -> List[Item]:
    parsed = feedparser.parse(source.url)
    items: List[Item] = []
    for entry in parsed.entries:
        title = normalize_text(entry.get("title", "(untitled)"))
        link = normalize_link(entry.get("link", ""))
        published_at = parse_published(entry)
        summary = normalize_text(entry.get("summary", ""))
        content_text = entry_content_text(entry)
        author = normalize_text(entry.get("author", ""))
        items.append(
            Item(
                source_id=source.id,
                title=title,
                link=link,
                published_at=published_at,
                author=author,
                summary=summary,
                content_text=content_text,
                category=source.category,
                dedupe_key=make_dedupe_key(link, title),
                title_key=normalize_title_key(title),
            )
        )
    return items
