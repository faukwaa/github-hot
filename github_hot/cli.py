from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Optional

from . import config
from .pipeline import CollectOptions, collect
from .report import build_report
from .store import Store


def _fmt(value: Optional[int]) -> str:
    """Star 数格式化：>=1000 用 k 为单位（8,182 -> 8.2k）。"""
    if value is None:
        return "-"
    if value >= 1000:
        text = f"{value / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{text}k"
    return f"{value:,}"


def _display_width(text: str) -> int:
    return sum(2 if ord(char) > 0x2E80 else 1 for char in text)


def _fit(text: str, width: int) -> str:
    if _display_width(text) <= width:
        return text
    out = ""
    for char in text:
        if _display_width(out + char) + 3 > width:
            break
        out += char
    return out + "..."


def _pad(text: str, width: int) -> str:
    return text + " " * max(width - _display_width(text), 0)


def _make_progress(stderr: bool):
    """采集进度显示：每个阶段标题与进度条目逐行输出（兼容管道/重定向环境）。"""
    stream = sys.stderr if stderr else sys.stdout

    def _show(kind: str, text: str) -> None:
        if kind == "phase":
            stream.write(text + "\n")
        else:
            stream.write(text + "\n")
        stream.flush()

    return _show


def _end_progress() -> None:
    pass


def print_table(items: list[dict[str, Any]]) -> None:
    headers = ["#", "项目", "AI", "语言", "本周Star", "总Star", "周增长", "简介"]
    rows: list[list[str]] = []
    for item in items:
        growth = item.get("weekly_growth")
        growth_text = f"+{growth:.1f}%" if growth is not None else "-"
        rows.append(
            [
                str(item["rank"]),
                item["full_name"],
                "AI" if item.get("is_ai") else "-",
                item.get("language") or "-",
                _fmt(item.get("weekly_stars")),
                _fmt(item.get("stars")),
                growth_text,
                _fit(item.get("ai_summary") or item.get("description") or "", 44),
            ]
        )
    widths = [max(_display_width(header), max((_display_width(row[i]) for row in rows), default=0)) for i, header in enumerate(headers)]
    print("  ".join(_pad(header, widths[i]) for i, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(_pad(cell, widths[i]) for i, cell in enumerate(row)))


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="github-hot",
        description="调研 GitHub 最近一周 Star 增长最快的开源项目（标注 AI 项目）",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["collect", "report", "serve", "ui", "tasks"],
        default=None,
        help="collect=采集数据；report=输出榜单；serve=启动 Web 仪表盘；ui=交互式终端工具；tasks=查看采集任务历史（默认先采集再输出榜单）",
    )
    parser.add_argument("--db", default=config.DEFAULT_DB_PATH, help="SQLite 数据库路径")
    parser.add_argument("--limit", type=int, default=config.DEFAULT_LIMIT, help="榜单条数")
    parser.add_argument(
        "--languages",
        default="",
        help="逗号分隔的 Trending 语言页，留空使用默认语言列表",
    )
    parser.add_argument("--since", default=config.DEFAULT_SINCE, choices=["daily", "weekly", "monthly"])
    parser.add_argument(
        "--ai-only",
        action="store_true",
        help="只保留标注为 AI 的项目（默认全部收录并标注）",
    )
    parser.add_argument(
        "--with-search",
        action="store_true",
        help="用 GitHub Search API 补充一周内新建的 AI 仓库",
    )
    parser.add_argument(
        "--api-top",
        type=int,
        default=None,
        help="用 REST API 补全前 N 个仓库的元数据；默认有 GITHUB_TOKEN 时补全前 30 个",
    )
    parser.add_argument("--json", action="store_true", help="榜单以 JSON 输出")
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="跳过 AI 任务总结与仓库一句话简介（默认配置 AI_API_KEY 后自动启用）",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--delete",
        type=int,
        default=None,
        metavar="TASK_ID",
        help="删除指定任务及其榜单快照（配合 tasks 命令使用）",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    token = config.github_token()

    if args.command == "ui":
        from .tui import main as tui_main

        return tui_main(argv)

    api_top = (
        args.api_top
        if args.api_top is not None
        else (config.DEFAULT_TOP_API if token else 0)
    )

    if args.command in (None, "collect"):
        languages = (
            [lang.strip() for lang in args.languages.split(",") if lang.strip()]
            if args.languages
            else list(config.DEFAULT_LANGUAGES)
        )
        store = Store(args.db).connect()
        options = CollectOptions(
            languages=languages,
            since=args.since,
            ai_only=args.ai_only,
            with_search=args.with_search,
            api_top=api_top,
            token=token,
            with_ai=not args.no_ai,
        )
        started = time.monotonic()
        progress = _make_progress(args.json)
        result = collect(store, options, progress=progress)
        _end_progress()
        store.close()
        elapsed = time.monotonic() - started
        summary = (
            f"已收录 {result.stored} 个项目"
            f"（其中 {result.ai_count} 个标注为 AI，跳过 {result.skipped}），耗时 {elapsed:.1f}s"
        )
        print(summary, file=sys.stderr if args.json else sys.stdout)
        if result.task_summary:
            print(f"任务总结: {result.task_summary}", file=sys.stderr if args.json else sys.stdout)
        for warning in result.warnings:
            print(f"  警告: {warning}", file=sys.stderr)
        if args.command == "collect":
            return 0

    if args.command in (None, "report"):
        store = Store(args.db).connect()
        rows = store.load_latest(limit=1000)
        store.close()
        if args.ai_only:
            rows = [row for row in rows if row.get("ai_reasons")]
        report = build_report(rows, limit=args.limit)
        if not report["items"]:
            print("暂无数据，请先运行: python -m github_hot collect", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            meta = report["meta"]
            print(f"数据采集时间: {meta['collected_at']}")
            print_table(report["items"])
        return 0

    if args.command == "serve":
        from .server import run_server

        return run_server(
            host=args.host,
            port=args.port,
            db_path=args.db,
            limit=args.limit,
            token=token,
        )

    if args.command == "tasks":
        if args.delete is not None:
            return delete_task_cmd(args.db, args.delete)
        return show_tasks(args.db, limit=20)

    return 0


def delete_task_cmd(db_path: str, task_id: int) -> int:
    """删除任务及其榜单快照。"""
    store = Store(db_path).connect()
    deleted = store.delete_task(task_id)
    store.close()
    if not deleted:
        print(f"任务 #{task_id} 不存在", file=sys.stderr)
        return 1
    print(f"任务 #{task_id} 已删除（含其榜单快照）")
    return 0


def show_tasks(db_path: str, limit: int = 20) -> int:
    """列出采集任务历史，包含每次拉取的 AI 总结。"""
    store = Store(db_path).connect()
    tasks = store.list_tasks(limit=limit)
    store.close()
    if not tasks:
        print("暂无采集任务，请先运行: python -m github_hot collect", file=sys.stderr)
        return 1
    for task in tasks:
        status = "成功" if task["status"] == "done" else "失败"
        error = task["error"] or ""
        print(f"任务 #{task['id']} | {task['collected_at']} | {status}")
        print(f"  收录 {task['repo_count']} 个项目（其中 {task['ai_count']} 个标注为 AI）")
        if task.get("summary"):
            print(f"  总结: {task['summary']}")
        if error:
            print(f"  提示: {error}")
        print()
    return 0
