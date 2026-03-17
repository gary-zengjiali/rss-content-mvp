from dataclasses import dataclass
from typing import Optional


@dataclass
class Source:
    id: str
    name: str
    url: str
    category: str = "general"
    enabled: bool = True
    priority: int = 0


@dataclass
class Item:
    source_id: str
    title: str
    link: str
    published_at: str
    author: str = ""
    summary: str = ""
    content_text: str = ""
    category: str = "general"
    dedupe_key: str = ""
    title_key: str = ""
    fetched_at: Optional[str] = None
