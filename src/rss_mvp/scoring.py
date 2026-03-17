from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple


def score_item(item: dict, topic_config: Dict) -> Tuple[int, List[str]]:
    text = " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            item.get("content_text", ""),
            item.get("category", ""),
        ]
    ).lower()

    score = 0
    reasons: List[str] = []

    for keyword in topic_config.get("boost_keywords", []):
        if keyword.lower() in text:
            score += 2
            reasons.append(f"命中关键词: {keyword}")

    for topic, keywords in topic_config.get("topic_keywords", {}).items():
        hits = [k for k in keywords if k.lower() in text]
        if hits:
            score += len(hits) * 3
            reasons.append(f"主题 {topic}: {', '.join(hits[:3])}")

    if len(item.get("summary", "")) > 120:
        score += 1
        reasons.append("摘要信息较丰富")

    if item.get("author"):
        score += 1
        reasons.append("带作者信息")

    priority = int(item.get("source_priority", 0) or 0)
    if priority:
        score += priority
        reasons.append(f"来源优先级 +{priority}")

    return score, reasons


def group_topics(items: Iterable[dict], topic_config: Dict) -> Dict[str, List[dict]]:
    grouped = defaultdict(list)
    for item in items:
        text = " ".join(
            [item.get("title", ""), item.get("summary", ""), item.get("content_text", "")]
        ).lower()
        matched = False
        for topic, keywords in topic_config.get("topic_keywords", {}).items():
            if any(k.lower() in text for k in keywords):
                grouped[topic].append(item)
                matched = True
        if not matched:
            grouped["other"].append(item)
    return dict(grouped)
