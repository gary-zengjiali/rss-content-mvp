from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json
import sqlite3

from .config import CONFIG_DIR, DATA_DIR, DB_PATH, load_sources


HEALTH_DIR = DATA_DIR / "health"
HEALTH_STATE_PATH = HEALTH_DIR / "source-health.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def load_health_state() -> Dict:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    if HEALTH_STATE_PATH.exists():
        return json.loads(HEALTH_STATE_PATH.read_text(encoding="utf-8"))
    return {"sources": {}}


def save_health_state(state: Dict) -> None:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    HEALTH_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def gather_db_stats() -> Dict[str, Dict]:
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
              source_id,
              COUNT(*) AS total_items,
              MAX(published_at) AS latest_published_at,
              MAX(fetched_at) AS latest_fetched_at,
              SUM(CASE WHEN substr(published_at,1,10)=date('now') THEN 1 ELSE 0 END) AS items_today
            FROM items
            GROUP BY source_id
            """
        ).fetchall()
        return {row["source_id"]: dict(row) for row in rows}
    finally:
        conn.close()


def build_health_report() -> Dict:
    sources = load_sources()
    db_stats = gather_db_stats()
    state = load_health_state()
    now = _utc_now()

    report_sources: List[Dict] = []
    summary = defaultdict(int)

    for source in sources:
        stats = db_stats.get(source.id, {})
        source_state = state.setdefault("sources", {}).setdefault(source.id, {})

        total_items = int(stats.get("total_items", 0) or 0)
        items_today = int(stats.get("items_today", 0) or 0)
        latest_published_at = stats.get("latest_published_at")
        latest_fetched_at = stats.get("latest_fetched_at")

        zero_streak = int(source_state.get("zero_streak", 0) or 0)
        if items_today == 0:
            zero_streak += 1
        else:
            zero_streak = 0
        source_state["zero_streak"] = zero_streak
        source_state["last_checked_at"] = now.isoformat()

        age_days = None
        latest_dt = _parse_dt(latest_published_at)
        if latest_dt:
            age_days = (now - latest_dt).days

        status = "healthy"
        reasons: List[str] = []

        if total_items == 0:
            status = "warning"
            reasons.append("数据库里还没有抓到任何条目")
        if age_days is not None and age_days >= 14:
            status = "warning"
            reasons.append(f"最近内容距离现在已有 {age_days} 天")
        if zero_streak >= 3:
            status = "warning"
            reasons.append(f"连续 {zero_streak} 次检查没有今日新条目")
        if age_days is not None and age_days >= 30:
            status = "critical"
            reasons.append(f"最近更新已超过 {age_days} 天")
        if zero_streak >= 7:
            status = "critical"
            reasons.append(f"连续 {zero_streak} 次检查没有今日新条目")

        summary[status] += 1
        report_sources.append(
            {
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "category": source.category,
                "priority": source.priority,
                "status": status,
                "reasons": reasons,
                "total_items": total_items,
                "items_today": items_today,
                "latest_published_at": latest_published_at,
                "latest_fetched_at": latest_fetched_at,
                "age_days": age_days,
                "zero_streak": zero_streak,
            }
        )

    save_health_state(state)
    report_sources.sort(key=lambda x: ({"critical": 2, "warning": 1, "healthy": 0}[x["status"]], x["priority"]), reverse=True)
    return {
        "generated_at": now.isoformat(),
        "summary": dict(summary),
        "sources": report_sources,
    }


def write_health_report(report: Dict) -> Dict[str, str]:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    json_path = HEALTH_DIR / "source-health-report.json"
    md_path = HEALTH_DIR / "source-health-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# RSS 源健康检查", "", f"- 生成时间：{report['generated_at']}", f"- 摘要：{report['summary']}", "", "## 源状态", ""]
    for item in report["sources"]:
        lines.append(f"### {item['name']} ({item['status']})")
        lines.append(f"- id: {item['id']}")
        lines.append(f"- 分类: {item['category']}")
        lines.append(f"- 今日条数: {item['items_today']}")
        lines.append(f"- 累计条数: {item['total_items']}")
        lines.append(f"- 最近发布时间: {item['latest_published_at']}")
        lines.append(f"- 连续空窗检查: {item['zero_streak']}")
        if item['reasons']:
            lines.append(f"- 原因: {'；'.join(item['reasons'])}")
        lines.append(f"- URL: {item['url']}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
