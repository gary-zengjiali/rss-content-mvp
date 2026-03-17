import json
from pathlib import Path
from typing import Dict, Iterable, List

from .config import OUTPUT_DIR
from .digest import to_dict_rows
from .scoring import score_item


def _trim_summary(text: str, limit: int = 80) -> str:
    text = (text or "").replace("\n", " ").strip()
    if not text:
        return "暂无摘要，可点原文查看详情。"
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def build_whatsapp_brief(date_str: str, rows: Iterable, topic_config: Dict, source_meta: Dict[str, Dict], limit: int = 15) -> Dict:
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
    top = enriched[:limit]

    entries = []
    for idx, item in enumerate(top, start=1):
        summary = item.get("content_text") or item.get("summary") or ""
        entries.append(
            {
                "rank": idx,
                "title": item["title"],
                "source": item["source_name"],
                "summary_80": _trim_summary(summary, 80),
                "link": item["link"],
                "score": item["score"],
            }
        )

    text_lines = [f"AI 今日简报｜{date_str}", ""]
    for entry in entries:
        text_lines.append(f"{entry['rank']}. {entry['title']}")
        text_lines.append(f"来源：{entry['source']}")
        text_lines.append(f"摘要：{entry['summary_80']}")
        text_lines.append(f"链接：{entry['link']}")
        text_lines.append("")

    return {
        "date": date_str,
        "count": len(entries),
        "entries": entries,
        "whatsapp_text": "\n".join(text_lines).strip(),
    }


def build_video_script(date_str: str, brief: Dict) -> Dict:
    top = brief.get("entries", [])[:5]
    hooks = [f"今天 AI 圈最值得看的 {len(top)} 条动态，我帮你压缩成 1 分钟。"]
    bullets = []
    for item in top:
        bullets.append(f"第{item['rank']}条，{item['title']}。核心点：{item['summary_80']}")
    outro = "如果你要，我可以把这份简报继续展开成长文、PPT 或者选题策划。"
    script = "\n".join(hooks + bullets + [outro])
    return {
        "date": date_str,
        "title": f"AI 今日热点速览 {date_str}",
        "duration_seconds": 60,
        "script": script,
        "shots": [
            {"scene": 1, "visual": "封面 + 今日日期 + AI 热点速览", "voiceover": hooks[0]},
            *[
                {
                    "scene": idx + 1,
                    "visual": f"新闻卡片：{item['title']}",
                    "voiceover": f"{item['title']}。{item['summary_80']}",
                }
                for idx, item in enumerate(top)
            ],
            {"scene": len(top) + 2, "visual": "结尾 CTA", "voiceover": outro},
        ],
    }


def build_ppt_outline(date_str: str, brief: Dict) -> Dict:
    top = brief.get("entries", [])[:8]
    slides: List[Dict] = [
        {
            "slide": 1,
            "title": f"AI 今日资讯简报 - {date_str}",
            "bullets": ["15 条精选资讯", "覆盖模型、工程、产品、商业动态", "适合晨会/自媒体选题"],
        }
    ]
    for idx, item in enumerate(top, start=2):
        slides.append(
            {
                "slide": idx,
                "title": item["title"],
                "bullets": [
                    f"来源：{item['source']}",
                    f"摘要：{item['summary_80']}",
                    "建议：可延展成快讯、解读或案例拆解",
                ],
            }
        )
    slides.append(
        {
            "slide": len(slides) + 1,
            "title": "今日可跟进方向",
            "bullets": ["继续跟踪高热度模型更新", "挑 1-2 条做深度内容", "同步到视频/PPT/公众号选题池"],
        }
    )
    return {
        "date": date_str,
        "title": f"AI 今日 PPT 大纲 {date_str}",
        "slides": slides,
    }


def write_content_outputs(date_str: str, brief: Dict, video_script: Dict, ppt_outline: Dict) -> Dict[str, str]:
    out_dir = OUTPUT_DIR / "content"
    out_dir.mkdir(parents=True, exist_ok=True)
    brief_json = out_dir / f"{date_str}-whatsapp-brief.json"
    brief_md = out_dir / f"{date_str}-whatsapp-brief.md"
    video_json = out_dir / f"{date_str}-video-script.json"
    video_md = out_dir / f"{date_str}-video-script.md"
    ppt_json = out_dir / f"{date_str}-ppt-outline.json"
    ppt_md = out_dir / f"{date_str}-ppt-outline.md"

    brief_json.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    brief_md.write_text(brief["whatsapp_text"], encoding="utf-8")
    video_json.write_text(json.dumps(video_script, ensure_ascii=False, indent=2), encoding="utf-8")
    video_md.write_text(video_script["script"], encoding="utf-8")
    ppt_json.write_text(json.dumps(ppt_outline, ensure_ascii=False, indent=2), encoding="utf-8")

    ppt_lines = [f"# {ppt_outline['title']}", ""]
    for slide in ppt_outline["slides"]:
        ppt_lines.append(f"## Slide {slide['slide']}: {slide['title']}")
        for bullet in slide["bullets"]:
            ppt_lines.append(f"- {bullet}")
        ppt_lines.append("")
    ppt_md.write_text("\n".join(ppt_lines), encoding="utf-8")

    return {
        "brief_json": str(brief_json),
        "brief_md": str(brief_md),
        "video_json": str(video_json),
        "video_md": str(video_md),
        "ppt_json": str(ppt_json),
        "ppt_md": str(ppt_md),
    }
