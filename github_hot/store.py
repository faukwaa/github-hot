from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Iterable, Optional

from .models import TrendingRepo

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
  full_name TEXT PRIMARY KEY,
  owner TEXT NOT NULL,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT,
  language TEXT,
  stars INTEGER NOT NULL DEFAULT 0,
  forks INTEGER NOT NULL DEFAULT 0,
  weekly_stars INTEGER,
  topics TEXT NOT NULL DEFAULT '[]',
  created_at TEXT,
  pushed_at TEXT,
  source TEXT NOT NULL,
  ai_reasons TEXT NOT NULL DEFAULT '[]',
  ai_summary TEXT,
  collected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_repos_collected_at ON repos(collected_at);
CREATE INDEX IF NOT EXISTS idx_repos_weekly ON repos(weekly_stars);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  collected_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'done',
  repo_count INTEGER NOT NULL DEFAULT 0,
  ai_count INTEGER NOT NULL DEFAULT 0,
  summary TEXT,
  error TEXT,
  since TEXT NOT NULL DEFAULT 'weekly',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_collected_at ON tasks(collected_at);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS repo_snapshots (
  full_name TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  owner TEXT NOT NULL,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT,
  language TEXT,
  stars INTEGER NOT NULL DEFAULT 0,
  forks INTEGER NOT NULL DEFAULT 0,
  weekly_stars INTEGER,
  topics TEXT NOT NULL DEFAULT '[]',
  created_at TEXT,
  pushed_at TEXT,
  source TEXT NOT NULL,
  ai_reasons TEXT NOT NULL DEFAULT '[]',
  ai_summary TEXT,
  PRIMARY KEY (full_name, collected_at)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_collected_at ON repo_snapshots(collected_at);
CREATE TABLE IF NOT EXISTS repo_readmes (
  full_name TEXT PRIMARY KEY,
  readme_raw TEXT,
  readme_translated TEXT,
  is_zh INTEGER NOT NULL DEFAULT 0,
  fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS watched_repos (
  full_name TEXT PRIMARY KEY,
  watched_at TEXT NOT NULL
);
"""

_REPO_COLUMNS = [
    "full_name", "owner", "name", "url", "description", "language", "stars", "forks",
    "weekly_stars", "topics", "created_at", "pushed_at", "source", "ai_reasons",
    "ai_summary", "collected_at",
]

_TASK_COLUMNS = ["id", "collected_at", "status", "repo_count", "ai_count", "summary", "error", "since", "created_at"]


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """老库迁移：为 repos 表补充 ai_summary 列、为 tasks 表补充 since 列。"""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(repos)")}
    if "ai_summary" not in cols:
        conn.execute("ALTER TABLE repos ADD COLUMN ai_summary TEXT")
    task_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "since" not in task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN since TEXT NOT NULL DEFAULT 'weekly'")
    conn.commit()


class Store:
    def __init__(self, path: str):
        self.path = path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> "Store":
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        _ensure_columns(self.conn)
        return self

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def save_repos(self, repos: Iterable[TrendingRepo], collected_at: str) -> None:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            for repo in repos:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO repos (
                      full_name, owner, name, url, description, language, stars, forks,
                      weekly_stars, topics, created_at, pushed_at, source, ai_reasons,
                      ai_summary, collected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        repo.full_name,
                        repo.owner,
                        repo.name,
                        repo.url,
                        repo.description,
                        repo.language,
                        repo.stars,
                        repo.forks,
                        repo.weekly_stars,
                        json.dumps(repo.topics, ensure_ascii=False),
                        repo.created_at,
                        repo.pushed_at,
                        repo.source,
                        json.dumps(repo.ai_reasons, ensure_ascii=False),
                        repo.ai_summary,
                        collected_at,
                    ),
                )
                # 保留历史快照：支持按任务查看该次拉取的完整榜单
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO repo_snapshots (
                      full_name, collected_at, owner, name, url, description, language,
                      stars, forks, weekly_stars, topics, created_at, pushed_at, source,
                      ai_reasons, ai_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        repo.full_name,
                        collected_at,
                        repo.owner,
                        repo.name,
                        repo.url,
                        repo.description,
                        repo.language,
                        repo.stars,
                        repo.forks,
                        repo.weekly_stars,
                        json.dumps(repo.topics, ensure_ascii=False),
                        repo.created_at,
                        repo.pushed_at,
                        repo.source,
                        json.dumps(repo.ai_reasons, ensure_ascii=False),
                        repo.ai_summary,
                    ),
                )

    def latest_collected_at(self) -> Optional[str]:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        row = self.conn.execute("SELECT MAX(collected_at) FROM repos").fetchone()
        return row[0] if row else None

    def load_repos_by_collected_at(
        self, collected_at: str, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """加载某次采集（任务）的仓库快照，供按任务查看历史榜单。"""
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        rows = self.conn.execute(
            """
            SELECT full_name, owner, name, url, description, language, stars, forks,
                   weekly_stars, topics, created_at, pushed_at, source, ai_reasons,
                   ai_summary, collected_at
            FROM repo_snapshots WHERE collected_at = ?
            ORDER BY weekly_stars DESC
            LIMIT ?
            """,
            (collected_at, limit),
        ).fetchall()
        items = []
        for row in rows:
            item = dict(zip(_REPO_COLUMNS, row))
            item["topics"] = json.loads(item["topics"] or "[]")
            item["ai_reasons"] = json.loads(item["ai_reasons"] or "[]")
            items.append(item)
        return items

    def load_latest(self, limit: int = 100) -> list[dict[str, Any]]:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        collected_at = self.latest_collected_at()
        if not collected_at:
            return []
        rows = self.conn.execute(
            """
            SELECT full_name, owner, name, url, description, language, stars, forks,
                   weekly_stars, topics, created_at, pushed_at, source, ai_reasons,
                   ai_summary, collected_at
            FROM repos WHERE collected_at = ?
            ORDER BY weekly_stars DESC
            LIMIT ?
            """,
            (collected_at, limit),
        ).fetchall()
        items = []
        for row in rows:
            item = dict(zip(_REPO_COLUMNS, row))
            item["topics"] = json.loads(item["topics"] or "[]")
            item["ai_reasons"] = json.loads(item["ai_reasons"] or "[]")
            items.append(item)
        return items

    def set_meta(self, key: str, value: str) -> None:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
            )

    def get_meta(self, key: str) -> Optional[str]:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    # ── 采集任务 ──────────────────────────────────────────────

    def create_task(
        self,
        collected_at: str,
        repo_count: int = 0,
        ai_count: int = 0,
        since: str = "weekly",
    ) -> int:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO tasks (collected_at, status, repo_count, ai_count, since, created_at)
                VALUES (?, 'running', ?, ?, ?, ?)
                """,
                (collected_at, repo_count, ai_count, since, collected_at),
            )
            return int(cursor.lastrowid)

    def finish_task(
        self,
        task_id: int,
        summary: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            self.conn.execute(
                "UPDATE tasks SET status = ?, summary = ?, error = ? WHERE id = ?",
                ("error" if error and not summary else "done", summary, error, task_id),
            )

    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        rows = self.conn.execute(
            """
            SELECT id, collected_at, status, repo_count, ai_count, summary, error, since, created_at
            FROM tasks ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(zip(_TASK_COLUMNS, row)) for row in rows]

    def get_task(self, task_id: int) -> Optional[dict[str, Any]]:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        row = self.conn.execute(
            """
            SELECT id, collected_at, status, repo_count, ai_count, summary, error, since, created_at
            FROM tasks WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        return dict(zip(_TASK_COLUMNS, row)) if row else None

    def delete_task(self, task_id: int) -> bool:
        """删除任务及其对应的仓库快照，返回是否删除成功。"""
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            row = self.conn.execute(
                "SELECT collected_at FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if not row:
                return False
            self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self.conn.execute(
                "DELETE FROM repo_snapshots WHERE collected_at = ?", (row[0],)
            )
            return True

    # ── README 缓存 ──────────────────────────────────────────

    def get_readme(self, full_name: str) -> Optional[dict[str, Any]]:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        row = self.conn.execute(
            """
            SELECT full_name, readme_raw, readme_translated, is_zh, fetched_at
            FROM repo_readmes WHERE full_name = ?
            """,
            (full_name,),
        ).fetchone()
        if not row:
            return None
        keys = ["full_name", "readme_raw", "readme_translated", "is_zh", "fetched_at"]
        return dict(zip(keys, row))

    def save_readme(
        self,
        full_name: str,
        readme_raw: Optional[str],
        readme_translated: Optional[str],
        is_zh: bool,
        fetched_at: str,
    ) -> None:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO repo_readmes
                  (full_name, readme_raw, readme_translated, is_zh, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (full_name, readme_raw, readme_translated, int(is_zh), fetched_at),
            )

    # ── 特别关注仓库 ────────────────────────────────────────

    def list_watched(self) -> list[str]:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        rows = self.conn.execute(
            "SELECT full_name FROM watched_repos ORDER BY watched_at DESC"
        ).fetchall()
        return [row[0] for row in rows]

    def is_watched(self, full_name: str) -> bool:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        row = self.conn.execute(
            "SELECT 1 FROM watched_repos WHERE full_name = ?", (full_name,)
        ).fetchone()
        return row is not None

    def add_watch(self, full_name: str, watched_at: str) -> None:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO watched_repos (full_name, watched_at) VALUES (?, ?)",
                (full_name, watched_at),
            )

    def remove_watch(self, full_name: str) -> None:
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        with self.conn:
            self.conn.execute(
                "DELETE FROM watched_repos WHERE full_name = ?", (full_name,)
            )

    def list_watched_repos(self) -> list[dict[str, Any]]:
        """关注仓库汇总：每个仓库带最新快照数据与出现在哪些任务中。"""
        if self.conn is None:
            raise RuntimeError("Store is not connected")
        items: list[dict[str, Any]] = []
        for full_name in self.list_watched():
            latest = self.conn.execute(
                """
                SELECT full_name, owner, name, url, description, language, stars, forks,
                       weekly_stars, topics, created_at, pushed_at, source, ai_reasons,
                       ai_summary, collected_at
                FROM repo_snapshots WHERE full_name = ?
                ORDER BY collected_at DESC LIMIT 1
                """,
                (full_name,),
            ).fetchone()
            tasks = self.conn.execute(
                """
                SELECT t.id, t.collected_at, t.since
                FROM tasks t
                JOIN repo_snapshots s ON s.collected_at = t.collected_at
                WHERE s.full_name = ?
                ORDER BY t.id DESC
                """,
                (full_name,),
            ).fetchall()
            repo: dict[str, Any] = {
                "full_name": full_name,
                "watched_at": self.conn.execute(
                    "SELECT watched_at FROM watched_repos WHERE full_name = ?", (full_name,)
                ).fetchone()[0],
                "tasks": [
                    {"id": t[0], "collected_at": t[1], "since": t[2]} for t in tasks
                ],
            }
            if latest:
                item = dict(zip(_REPO_COLUMNS, latest))
                item["topics"] = json.loads(item["topics"] or "[]")
                item["ai_reasons"] = json.loads(item["ai_reasons"] or "[]")
                repo["latest"] = item
            items.append(repo)
        return items
