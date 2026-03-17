import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from .config import OUTPUT_DIR
from .scoring import group_topics, score_item


def to_dict_rows(rows: Iterable) -> List[Dict]:
    return [dict(r) for r in rows]


def build_digest(date_str: str, rows: Iterable, source_meta: Dict[str, Dict]) -> Dict:
    items = to_dict_rows(rows)
    category_counter = Counter(item.get("category", "other") for item in items)
    source_counter = Counter(item.get("source_id", "unknown") for item in items)

    for item in items:
        meta = source_meta.get(item["source_id"], {})
        item["source_name"] = meta.get("name", item["source_id"])
        item["source_priority"] = meta.get("priority", 0)

    return {
        "date": date_str,
        "total_items": len(items),
        "categories": dict(category_counter),
        "sources": dict(source_counter),
        "items": items,
    }


def render_digest_markdown(digest: Dict) -> str:
    lines = []
    lines.append(f"# AI 资讯日报 - {digest['date']}")
    lines.append("")
    lines.append(f"- 共收录 **{digest['total_items']}** 条")
    lines.append(f"- 分类分布：{digest['categories']}")
    lines.append("")
    lines.append("## 今日条目")
    lines.append("")

    for idx, item in enumerate(digest["items"], start=1):
        lines.append(f"### {idx}. {item['title']}")
        lines.append(f"- 来源：{item.get('source_name', item['source_id'])}")
        lines.append(f"- 时间：{item['published_at']}")
        if item.get("author"):
            lines.append(f"- 作者：{item['author']}")
        lines.append(f"- 链接：{item['link']}")
        if item.get("summary"):
            lines.append(f"- 摘要：{item['summary'][:240]}")
        lines.append("")
    return "\n".join(lines)


def write_digest_files(date_str: str, digest: Dict) -> Dict[str, str]:
    daily_dir = OUTPUT_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    json_path = daily_dir / f"{date_str}-digest.json"
    md_path = daily_dir / f"{date_str}-digest.md"
    json_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_digest_markdown(digest), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def build_topics(date_str: str, rows: Iterable, topic_config: Dict, source_meta: Dict[str, Dict]) -> Dict:
    items = to_dict_rows(rows)
    enriched = []
    for item in items:
        meta = source_meta.get(item["source_id"], {})
        item["source_name"] = meta.get("name", item["source_id"])
        item["source_priority"] = meta.get("priority", 0)
        score, reasons = score_item(item, topic_config)
        item["score"] = score
        item["reasons"] = reasons
        enriched.append(item)

    enriched.sort(key=lambda x: (x.get("score", 0), x.get("published_at", "")), reverse=True)
    grouped = group_topics(enriched, topic_config)
    top_items = enriched[:10]

    topic_ideas = []
    for item in top_items[:5]:
        title = item["title"]
        angle = f"从 {item['source_name']} 这条动态切入，解释它对业务落地/工程实践的影响"
        topic_ideas.append(
            {
                "seed_title": title,
                "proposed_angle": angle,
                "source": item["source_name"],
                "link": item["link"],
                "score": item["score"],
                "reasons": item["reasons"],
            }
        )

    return {
        "date": date_str,
        "top_items": top_items,
        "grouped": grouped,
        "topic_ideas": topic_ideas,
    }


def render_topics_markdown(payload: Dict) -> str:
    lines = [f"# 选题池 - {payload['date']}", ""]
    lines.append("## 推荐选题")
    lines.append("")
    for idx, idea in enumerate(payload["topic_ideas"], start=1):
        lines.append(f"### {idx}. {idea['seed_title']}")
        lines.append(f"- 来源：{idea['source']}")
        lines.append(f"- 角度：{idea['proposed_angle']}")
        lines.append(f"- 得分：{idea['score']}")
        lines.append(f"- 依据：{'；'.join(idea['reasons'][:4])}")
        lines.append(f"- 链接：{idea['link']}")
        lines.append("")

    lines.append("## 主题分组")
    lines.append("")
    for topic, items in payload["grouped"].items():
        lines.append(f"### {topic} ({len(items)})")
        for item in items[:5]:
            lines.append(f"- {item['title']} [{item.get('source_name', item['source_id'])}]")
        lines.append("")
    return "\n".join(lines)


def write_topics_files(date_str: str, payload: Dict) -> Dict[str, str]:
    topic_dir = OUTPUT_DIR / "topics"
    topic_dir.mkdir(parents=True, exist_ok=True)
    json_path = topic_dir / f"{date_str}-topics.json"
    md_path = topic_dir / f"{date_str}-topics.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_topics_markdown(payload), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
