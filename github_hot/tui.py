from __future__ import annotations

import threading
import time
from typing import Any, Optional

from . import config
from .cli import print_table, parse_args
from .pipeline import CollectOptions, collect
from .report import build_report
from .store import Store

_STATE: dict[str, Any] = {"server": None, "thread": None, "port": None}


def _report(db_path: str, limit: int, ai_only: bool = False) -> dict[str, Any]:
    store = Store(db_path).connect()
    rows = store.load_latest(limit=1000)
    store.close()
    if ai_only:
        rows = [row for row in rows if row.get("ai_reasons")]
    return build_report(rows, limit=limit)


def _run_collect(
    db_path: str,
    token: Optional[str],
    options: Optional[CollectOptions] = None,
) -> None:
    store = Store(db_path).connect()
    if options is None:
        options = CollectOptions(
            token=token,
            api_top=config.DEFAULT_TOP_API if token else 0,
        )
    started = time.monotonic()
    from .cli import _end_progress, _make_progress

    result = collect(store, options, progress=_make_progress(stderr=False))
    _end_progress()
    store.close()
    elapsed = time.monotonic() - started
    print(
        f"已收录 {result.stored} 个项目"
        f"（其中 {result.ai_count} 个标注为 AI），耗时 {elapsed:.1f}s"
    )
    for warning in result.warnings:
        print(f"  警告: {warning}")


def _start_server(port: int, db_path: str, limit: int, token: Optional[str]) -> None:
    if _STATE["server"] is not None:
        print(f"Web 仪表盘已在运行: http://127.0.0.1:{_STATE['port']}")
        return
    from .server import create_server

    server = create_server("127.0.0.1", port, db_path, limit, token)
    thread = threading.Thread(target=server.serve_forever, name="github-hot-web", daemon=True)
    thread.start()
    _STATE["server"] = server
    _STATE["thread"] = thread
    _STATE["port"] = port
    print(f"Web 仪表盘已启动: http://127.0.0.1:{port}")


def _stop_server() -> None:
    server = _STATE["server"]
    if server is None:
        print("Web 仪表盘未在运行")
        return
    server.shutdown()
    server.server_close()
    if _STATE["thread"] is not None:
        _STATE["thread"].join(timeout=5)
    _STATE["server"] = None
    _STATE["thread"] = None
    _STATE["port"] = None
    print("Web 仪表盘已停止")


def _status_line(db_path: str) -> str:
    store = Store(db_path).connect()
    collected_at = store.latest_collected_at()
    store.close()
    collected = collected_at or "尚未采集"
    if _STATE["server"] is not None:
        web = f"运行中 (http://127.0.0.1:{_STATE['port']})"
    else:
        web = "未启动"
    return f"数据库: {db_path}\n最新采集: {collected}\nWeb 服务: {web}"


def _ask(text: str, default: str = "") -> str:
    """带默认值的输入提示。"""
    suffix = f"（回车用默认 {default}）" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or default


def _custom_collect(db_path: str, token: Optional[str]) -> None:
    """自定义采集：语言 / 时间范围 / 搜索补充 / API 补全。"""
    langs_raw = _ask("语言（逗号分隔，如 python,go，留空用默认列表）")
    languages = [lang.strip() for lang in langs_raw.split(",") if lang.strip()] or list(
        config.DEFAULT_LANGUAGES
    )
    since = _ask("时间范围（daily/weekly/monthly）", "weekly")
    if since not in ("daily", "weekly", "monthly"):
        print(f"无效时间范围: {since}，使用 weekly")
        since = "weekly"
    with_search = _ask("是否用 Search 补充一周内新建的 AI 仓库（y/n）", "n").lower() == "y"
    api_top_raw = _ask("API 补全前 N 个仓库元数据（0 跳过）", "0")
    try:
        api_top = max(int(api_top_raw), 0)
    except ValueError:
        api_top = 0
    options = CollectOptions(
        languages=languages,
        since=since,
        with_search=with_search,
        api_top=api_top if api_top > 0 else (config.DEFAULT_TOP_API if token else 0),
        token=token,
    )
    _run_collect(db_path, token, options=options)


def _custom_report(db_path: str) -> None:
    """自定义榜单：条数 / JSON。"""
    limit_raw = _ask("榜单条数", "30")
    try:
        limit = max(int(limit_raw), 1)
    except ValueError:
        limit = 30
    as_json = _ask("JSON 输出（y/n）", "n").lower() == "y"
    report = _report(db_path, limit)
    if as_json:
        import json

        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"数据采集时间: {report['meta']['collected_at']}")
        print_table(report["items"])


def _delete_task(db_path: str) -> None:
    """删除任务（含榜单快照）。"""
    from .cli import delete_task_cmd, show_tasks

    show_tasks(db_path, limit=10)
    task_id = _ask("输入要删除的任务 ID（留空取消）")
    if not task_id:
        print("已取消")
        return
    try:
        task_id_int = int(task_id)
    except ValueError:
        print(f"无效的任务 ID: {task_id}")
        return
    delete_task_cmd(db_path, task_id_int)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    token = config.github_token()

    while True:
        print()
        print("GitHub 热度周榜 - 终端工具")
        print("-" * 40)
        print(_status_line(args.db))
        print("-" * 40)
        print("1. 采集数据（默认参数，自动生成 AI 总结）")
        print("2. 采集数据 - 自定义（语言 / 时间范围 / 搜索补充）")
        print("3. 查看全部榜单")
        print("4. 查看 AI 榜单")
        print("5. 查看榜单 - 自定义（条数 / JSON）")
        print("6. 查看采集任务历史")
        print("7. 删除任务")
        print("8. 启动 Web 仪表盘")
        print("9. 停止 Web 仪表盘")
        print("0. 退出")
        try:
            choice = input("请输入选项: ").strip()
        except EOFError:
            break

        if choice == "1":
            _run_collect(args.db, token)
        elif choice == "2":
            _custom_collect(args.db, token)
        elif choice == "3":
            report = _report(args.db, args.limit)
            print(f"数据采集时间: {report['meta']['collected_at']}")
            print_table(report["items"])
        elif choice == "4":
            report = _report(args.db, args.limit, ai_only=True)
            print(f"数据采集时间: {report['meta']['collected_at']}")
            print_table(report["items"])
        elif choice == "5":
            _custom_report(args.db)
        elif choice == "6":
            from .cli import show_tasks

            show_tasks(args.db)
        elif choice == "7":
            _delete_task(args.db)
        elif choice == "8":
            _start_server(args.port, args.db, args.limit, token)
        elif choice == "9":
            _stop_server()
        elif choice == "0":
            break
        else:
            print("无效选项，请输入 0-9 之间的数字")

        if choice not in ("0",):
            input("\n按回车返回菜单...")

    if _STATE["server"] is not None:
        _stop_server()
    print("已退出")
    return 0
