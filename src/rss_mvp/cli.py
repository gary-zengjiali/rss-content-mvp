import argparse
from datetime import datetime
from typing import Optional

from .config import ensure_dirs, load_sources, load_topic_config
from .db import fetch_items_by_date, init_db, upsert_items
from .contentgen import build_ppt_outline, build_video_script, build_whatsapp_brief, write_content_outputs
from .digest import build_digest, build_topics, write_digest_files, write_topics_files
from .enrich import enrich_rows
from .fetcher import parse_feed
from .healthcheck import build_health_report, write_health_report
from .sync import sync_to_github, sync_to_obsidian


def command_init_db(_args):
    init_db()
    print("Database initialized.")


def command_fetch(_args):
    ensure_dirs()
    sources = load_sources()
    total_inserted = 0
    total_skipped = 0

    for source in sources:
        items = parse_feed(source)
        inserted, skipped = upsert_items(items)
        total_inserted += inserted
        total_skipped += skipped
        print(f"[{source.id}] inserted={inserted} skipped={skipped} total_parsed={len(items)}")

    print(f"Done. inserted={total_inserted}, skipped={total_skipped}")


def source_meta_map():
    return {
        s.id: {
            "name": s.name,
            "priority": s.priority,
            "category": s.category,
            "url": s.url,
        }
        for s in load_sources()
    }


def resolve_date(date_arg: Optional[str]) -> str:
    if date_arg:
        return date_arg
    return datetime.now().date().isoformat()


def command_digest(args):
    date_str = resolve_date(args.date)
    rows = fetch_items_by_date(date_str)
    digest = build_digest(date_str, rows, source_meta_map())
    paths = write_digest_files(date_str, digest)
    print(f"Digest written: {paths['markdown']} | {paths['json']}")


def command_enrich(args):
    date_str = resolve_date(args.date)
    rows = [dict(r) for r in fetch_items_by_date(date_str)]
    if args.limit:
        rows = rows[: args.limit]
    updated, skipped = enrich_rows(rows)
    print(f"Enriched date={date_str} updated={updated} skipped={skipped}")


def command_topics(args):
    date_str = resolve_date(args.date)
    rows = fetch_items_by_date(date_str)
    payload = build_topics(date_str, rows, load_topic_config(), source_meta_map())
    paths = write_topics_files(date_str, payload)
    print(f"Topics written: {paths['markdown']} | {paths['json']}")


def command_sync(args):
    date_str = resolve_date(args.date)
    if args.target in ("obsidian", "all"):
        result = sync_to_obsidian(date_str)
        print(f"Obsidian sync: {result}")
    if args.target in ("github", "all"):
        result = sync_to_github(date_str)
        print(f"GitHub sync: {result}")


def command_healthcheck(_args):
    report = build_health_report()
    paths = write_health_report(report)
    print(f"Healthcheck written: {paths['markdown']} | {paths['json']}")
    print(f"Summary: {report['summary']}")


def command_content(args):
    date_str = resolve_date(args.date)
    rows = fetch_items_by_date(date_str)
    brief = build_whatsapp_brief(date_str, rows, load_topic_config(), source_meta_map(), limit=args.limit)
    video = build_video_script(date_str, brief)
    ppt = build_ppt_outline(date_str, brief)
    paths = write_content_outputs(date_str, brief, video, ppt)
    print(f"Content written: {paths}")


def command_run_daily(args):
    date_str = resolve_date(args.date)
    command_fetch(args)
    enrich_args = argparse.Namespace(date=date_str, limit=args.enrich_limit)
    command_enrich(enrich_args)
    digest_rows = fetch_items_by_date(date_str)
    digest = build_digest(date_str, digest_rows, source_meta_map())
    digest_paths = write_digest_files(date_str, digest)
    topics = build_topics(date_str, digest_rows, load_topic_config(), source_meta_map())
    topic_paths = write_topics_files(date_str, topics)
    content_paths = None
    if args.generate_content:
        brief = build_whatsapp_brief(date_str, digest_rows, load_topic_config(), source_meta_map(), limit=args.brief_limit)
        video = build_video_script(date_str, brief)
        ppt = build_ppt_outline(date_str, brief)
        content_paths = write_content_outputs(date_str, brief, video, ppt)
        print(f"Content written: {content_paths}")
    if args.sync_target != "none":
        if args.sync_target in ("obsidian", "all"):
            print(f"Obsidian sync: {sync_to_obsidian(date_str)}")
        if args.sync_target in ("github", "all"):
            print(f"GitHub sync: {sync_to_github(date_str)}")
    if args.healthcheck:
        report = build_health_report()
        paths = write_health_report(report)
        print(f"Healthcheck written: {paths['markdown']} | {paths['json']}")
    print(f"Daily run complete. digest={digest_paths['markdown']} topics={topic_paths['markdown']} content={content_paths}")


def build_parser():
    parser = argparse.ArgumentParser(description="RSS Content MVP")
    sub = parser.add_subparsers(dest="command", required=True)

    init_db_parser = sub.add_parser("init-db")
    init_db_parser.set_defaults(func=command_init_db)

    fetch_parser = sub.add_parser("fetch")
    fetch_parser.set_defaults(func=command_fetch)

    enrich_parser = sub.add_parser("enrich")
    enrich_parser.add_argument("--date", help="YYYY-MM-DD")
    enrich_parser.add_argument("--limit", type=int, default=20, help="最大补抓正文条数")
    enrich_parser.set_defaults(func=command_enrich)

    digest_parser = sub.add_parser("digest")
    digest_parser.add_argument("--date", help="YYYY-MM-DD")
    digest_parser.set_defaults(func=command_digest)

    topics_parser = sub.add_parser("topics")
    topics_parser.add_argument("--date", help="YYYY-MM-DD")
    topics_parser.set_defaults(func=command_topics)

    sync_parser = sub.add_parser("sync")
    sync_parser.add_argument("--date", help="YYYY-MM-DD")
    sync_parser.add_argument("--target", choices=["github", "obsidian", "all"], default="all")
    sync_parser.set_defaults(func=command_sync)

    health_parser = sub.add_parser("healthcheck")
    health_parser.set_defaults(func=command_healthcheck)

    content_parser = sub.add_parser("content")
    content_parser.add_argument("--date", help="YYYY-MM-DD")
    content_parser.add_argument("--limit", type=int, default=15, help="WhatsApp 简报条数")
    content_parser.set_defaults(func=command_content)

    run_daily_parser = sub.add_parser("run-daily")
    run_daily_parser.add_argument("--date", help="YYYY-MM-DD")
    run_daily_parser.add_argument("--enrich-limit", type=int, default=20, help="daily 流程里最大正文抽取条数")
    run_daily_parser.add_argument("--sync-target", choices=["none", "github", "obsidian", "all"], default="none")
    run_daily_parser.add_argument("--healthcheck", action="store_true")
    run_daily_parser.add_argument("--generate-content", action="store_true")
    run_daily_parser.add_argument("--brief-limit", type=int, default=15)
    run_daily_parser.set_defaults(func=command_run_daily)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
