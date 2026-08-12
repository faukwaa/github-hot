from __future__ import annotations

import base64
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, quote, urlparse

from . import config
from .ai import is_mostly_chinese, translate_text
from .dashboard import render_dashboard
from .fetch import FetchError, get_json
from .pipeline import CollectOptions, collect, utc_now
from .report import build_report
from .store import Store

_STATE: dict[str, Any] = {
    "db_path": config.DEFAULT_DB_PATH,
    "limit": config.DEFAULT_LIMIT,
    "token": None,
    "api_top": 0,
    "lock": threading.Lock(),
}

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")


def _send_file(handler: BaseHTTPRequestHandler, file_path: str, content_type: str) -> None:
    """读取并发送本地文件。"""
    try:
        with open(file_path, "rb") as fh:
            data = fh.read()
    except OSError:
        handler._send_text("Not Found", "text/plain; charset=utf-8", 404)
        return
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".json": "application/json; charset=utf-8",
    ".woff2": "font/woff2",
}


def _fetch_readme(full_name: str, token: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """抓取仓库 README 原文，返回 (内容, 错误信息)。"""
    owner, _, name = full_name.partition("/")
    if not owner or not name:
        return None, "仓库名格式不正确"
    path = f"{quote(owner, safe='')}/{quote(name, safe='')}"
    url = f"{config.API_BASE_URL}/repos/{path}/readme"
    try:
        payload = get_json(url, token=token, timeout=30)
    except FetchError as err:
        if "HTTP 404" in str(err):
            return None, "该仓库没有 README"
        return None, str(err)
    content = payload.get("content") or ""
    try:
        text = base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - base64 解码失败
        return None, "README 内容解码失败"
    # 限制超长 README，避免页面与翻译开销过大
    if len(text) > 200_000:
        text = text[:200_000] + "\n\n<!-- 内容过长，已截断 -->"
    return text, None


def _repo_readme_payload(full_name: str, translate: bool = False) -> dict[str, Any]:
    """返回仓库 README 详情（含缓存与按需翻译逻辑）。"""
    store = Store(_STATE["db_path"]).connect()
    cached = store.get_readme(full_name)
    if cached and cached.get("readme_raw"):
        translated = cached.get("readme_translated")
        is_zh = bool(cached.get("is_zh"))
        if translate and not is_zh and not translated:
            translated, translate_error = translate_text(cached["readme_raw"])
            if translate_error:
                print(f"[github-hot] 翻译失败 {full_name}: {translate_error}", file=sys.stderr)
                store.close()
                return {
                    "full_name": full_name,
                    "readme_raw": cached["readme_raw"],
                    "readme_translated": None,
                    "is_zh": False,
                    "translate_error": translate_error,
                    "cached": True,
                    "error": None,
                }
            store.save_readme(full_name, cached["readme_raw"], translated, False, utc_now())
        store.close()
        return {
            "full_name": full_name,
            "readme_raw": cached["readme_raw"],
            "readme_translated": translated,
            "is_zh": is_zh,
            "cached": True,
            "error": None,
        }

    raw, fetch_error = _fetch_readme(full_name, _STATE["token"])
    if fetch_error or raw is None:
        store.close()
        return {"full_name": full_name, "error": fetch_error or "README 获取失败"}

    is_zh = is_mostly_chinese(raw)
    translated: Optional[str] = None
    translate_error: Optional[str] = None
    if not is_zh and translate:
        translated, translate_error = translate_text(raw)
        if translate_error:
            print(f"[github-hot] 翻译失败 {full_name}: {translate_error}", file=sys.stderr)

    store.save_readme(full_name, raw, translated, is_zh, utc_now())
    store.close()
    return {
        "full_name": full_name,
        "readme_raw": raw,
        "readme_translated": translated,
        "is_zh": is_zh,
        "translate_error": translate_error,
        "cached": False,
        "error": None,
    }


def _payload(
    error: Optional[str] = None,
    collect_now: bool = False,
    task_id: Optional[int] = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    if collect_now:
        store = Store(_STATE["db_path"]).connect()
        options = CollectOptions(
            token=_STATE["token"], api_top=_STATE["api_top"], with_ai=True
        )
        try:
            result = collect(store, options)
            warnings = result.warnings
        except Exception as err:  # noqa: BLE001 - 展示给用户的采集失败信息
            error = f"采集失败: {err}"
        store.close()

    store = Store(_STATE["db_path"]).connect()
    if task_id is not None:
        task = store.get_task(task_id)
        if task is None:
            store.close()
            return {
                "data": None,
                "tasks": [],
                "warnings": [],
                "error": f"任务 #{task_id} 不存在",
                "generated_at": utc_now(),
            }
        rows = store.load_repos_by_collected_at(task["collected_at"], limit=1000)
        report = build_report(rows, limit=1000)  # Web 端展示该任务全部收录仓库
        report["meta"]["collected_at"] = task["collected_at"]
        store.close()
        return {
            "data": report,
            "task": task,
            "warnings": warnings,
            "error": error,
            "generated_at": utc_now(),
        }

    rows = store.load_latest(limit=1000)
    # 任务全部返回，由前端按时间分组折叠（30 天内平铺 / 当年更早 / 按年度）
    tasks = store.list_tasks(limit=_STATE.get("task_limit", 500))
    store.close()
    report = build_report(rows, limit=1000)  # Web 端展示全部收录仓库，不做截断
    return {
        "data": report,
        "tasks": tasks,
        "warnings": warnings,
        "error": error,
        "generated_at": utc_now(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "github-hot/0.1"

    def _send_text(self, body: str, content_type: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        self._send_text(
            json.dumps(payload, ensure_ascii=False),
            "application/json; charset=utf-8",
            status,
        )

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            index = os.path.join(_FRONTEND_DIR, "index.html")
            if os.path.exists(index):
                _send_file(self, index, "text/html; charset=utf-8")
            else:
                # 未构建前端时回退到内联仪表盘
                self._send_text(render_dashboard(_payload()), "text/html; charset=utf-8")
        elif path.startswith("/assets/") and _FRONTEND_DIR:
            safe = path.lstrip("/")
            file_path = os.path.normpath(os.path.join(_FRONTEND_DIR, safe))
            if file_path.startswith(_FRONTEND_DIR) and os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1]
                _send_file(self, file_path, _CONTENT_TYPES.get(ext, "application/octet-stream"))
            else:
                self._send_text("Not Found", "text/plain; charset=utf-8", 404)
        elif path == "/static/marked.min.js":
            # 本地化 marked 渲染库（随项目分发，无 CDN 依赖）
            asset = os.path.join(os.path.dirname(__file__), "static", "marked.min.js")
            try:
                with open(asset, "rb") as fh:
                    data = fh.read()
            except OSError:
                self._send_text("Not Found", "text/plain; charset=utf-8", 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/data":
            task_param = query.get("task", [None])[0]
            task_id = int(task_param) if task_param and task_param.isdigit() else None
            self._send_json(_payload(task_id=task_id))
        elif path == "/api/tasks":
            store = Store(_STATE["db_path"]).connect()
            tasks = store.list_tasks(limit=500)
            store.close()
            self._send_json({"tasks": tasks})
        elif path == "/api/repo":
            name = query.get("name", [""])[0].strip()
            translate = query.get("translate", ["0"])[0] == "1"
            if not name:
                self._send_json({"error": "缺少仓库名参数"}, 400)
            else:
                self._send_json(_repo_readme_payload(name, translate=translate))
        elif path == "/api/watched":
            store = Store(_STATE["db_path"]).connect()
            watched = store.list_watched()
            store.close()
            self._send_json({"watched": watched})
        elif path == "/api/watched/repos":
            store = Store(_STATE["db_path"]).connect()
            repos = store.list_watched_repos()
            store.close()
            self._send_json({"repos": repos})
        else:
            # SPA history fallback：前端路由路径（如 /repo/owner/name）返回 index.html
            index = os.path.join(_FRONTEND_DIR, "index.html")
            if os.path.exists(index):
                _send_file(self, index, "text/html; charset=utf-8")
            else:
                self._send_text("Not Found", "text/plain; charset=utf-8", 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/api/tasks/delete":
            task_param = query.get("task", [""])[0]
            if not task_param or not task_param.isdigit():
                self._send_json({"error": "缺少任务 ID"}, 400)
                return
            store = Store(_STATE["db_path"]).connect()
            deleted = store.delete_task(int(task_param))
            store.close()
            if not deleted:
                self._send_json({"error": f"任务 #{task_param} 不存在"}, 404)
                return
            self._send_json({"ok": True, "deleted": int(task_param)})
            return
        if path == "/api/watched/toggle":
            name = query.get("name", [""])[0].strip()
            if not name:
                self._send_json({"error": "缺少仓库名参数"}, 400)
                return
            store = Store(_STATE["db_path"]).connect()
            if store.is_watched(name):
                store.remove_watch(name)
                watched = False
            else:
                store.add_watch(name, utc_now())
                watched = True
            watched_list = store.list_watched()
            store.close()
            self._send_json({"watched": watched, "watched_list": watched_list})
            return
        if path != "/api/refresh":
            self._send_text("Not Found", "text/plain; charset=utf-8", 404)
            return
        if not _STATE["lock"].acquire(blocking=False):
            self._send_json({"error": "采集正在进行中，请稍候"}, 429)
            return
        try:
            self._send_json(_payload(collect_now=True))
        finally:
            _STATE["lock"].release()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        print(f"[github-hot] {self.address_string()} - {format % args}")


def create_server(
    host: str,
    port: int,
    db_path: str,
    limit: int,
    token: Optional[str],
) -> ThreadingHTTPServer:
    _STATE["db_path"] = db_path
    _STATE["limit"] = limit
    _STATE["token"] = token
    _STATE["api_top"] = config.DEFAULT_TOP_API if token else 0

    store = Store(db_path).connect()
    has_data = bool(store.latest_collected_at())
    store.close()
    if not has_data:
        print("首次启动，先采集一次数据...")
        payload = _payload(collect_now=True)
        if payload["error"]:
            print(f"首次采集失败: {payload['error']}", file=sys.stderr)
        elif payload["warnings"]:
            for warning in payload["warnings"]:
                print(f"  警告: {warning}", file=sys.stderr)

    return ThreadingHTTPServer((host, port), Handler)


def run_server(
    host: str,
    port: int,
    db_path: str,
    limit: int,
    token: Optional[str],
) -> int:
    server = create_server(host, port, db_path, limit, token)
    print(f"GitHub 热度周榜: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
