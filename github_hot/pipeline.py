from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import quote

from . import config
from .ai import summarize_repo_batch, summarize_task
from .fetch import FetchError, get_json
from .filters import annotate_ai_repos, match_repo
from .models import TrendingRepo
from .report import build_report
from .store import Store
from .trending import fetch_trending


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


@dataclass
class CollectOptions:
    languages: list[str] = field(default_factory=lambda: list(config.DEFAULT_LANGUAGES))
    since: str = config.DEFAULT_SINCE
    ai_only: bool = False
    with_search: bool = False
    api_top: int = 0
    token: Optional[str] = None
    with_ai: bool = True


@dataclass
class CollectResult:
    stored: int = 0
    ai_count: int = 0
    skipped: int = 0
    sources: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    collected_at: str = ""
    task_id: Optional[int] = None
    task_summary: Optional[str] = None
    summarized_repos: int = 0


# 进度回调：(kind, text)，kind 为 "phase"（新阶段，换行显示）或 "update"（当前阶段进度，单行刷新）
ProgressFn = Callable[[str, str], None]


def _search_new_ai_repos(
    token: Optional[str], days: int = 7, progress: Optional[ProgressFn] = None
) -> tuple[list[TrendingRepo], list[str]]:
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    results: list[TrendingRepo] = []
    warnings: list[str] = []

    for index, topic in enumerate(config.SEARCH_TOPICS, start=1):
        if progress:
            progress("update", f"  {index}/{len(config.SEARCH_TOPICS)}: topic:{topic}")
        query = quote(f"topic:{topic} created:>={since}")
        url = f"{config.API_BASE_URL}/search/repositories?q={query}&sort=stars&order=desc&per_page=30"
        try:
            payload = get_json(url, token=token)
        except FetchError as err:
            if "HTTP 403" in str(err) or "HTTP 429" in str(err):
                warnings.append("GitHub Search API 触发限流，停止补充搜索")
                break
            warnings.append(f"search {topic}: {err}")
            continue

        for item in payload.get("items", []):
            repo = TrendingRepo(
                full_name=item["full_name"],
                url=item["html_url"],
                description=item.get("description"),
                language=item.get("language"),
                stars=item.get("stargazers_count", 0),
                forks=item.get("forks_count", 0),
                # 一周内新建的仓库，当前总 Star 即一周增量。
                weekly_stars=item.get("stargazers_count", 0),
                source=f"search:{topic}",
                created_at=item.get("created_at"),
                pushed_at=item.get("pushed_at"),
                topics=item.get("topics", []),
            )
            _, reasons = match_repo(repo)
            repo.ai_reasons = reasons
            results.append(repo)
    return results, warnings


def _enrich_top(
    repos: list[TrendingRepo], top: int, token: Optional[str], progress: Optional[ProgressFn] = None
) -> tuple[int, list[str]]:
    ordered = sorted(
        repos, key=lambda r: (r.weekly_stars is None, -(r.weekly_stars or 0))
    )[:top]
    enriched = 0
    errors: list[str] = []
    for index, repo in enumerate(ordered, start=1):
        if progress:
            progress("update", f"  {index}/{len(ordered)}: {repo.full_name}")
        path = f"{quote(repo.owner, safe='')}/{quote(repo.name, safe='')}"
        url = f"{config.API_BASE_URL}/repos/{path}"
        try:
            payload = get_json(url, token=token)
        except FetchError as err:
            if "HTTP 403" in str(err) or "HTTP 429" in str(err):
                errors.append(f"enrich {repo.full_name}: API 限流，停止补全")
                break
            errors.append(f"enrich {repo.full_name}: {err}")
            continue
        repo.description = payload.get("description") or repo.description
        repo.language = payload.get("language") or repo.language
        repo.topics = payload.get("topics") or []
        repo.created_at = payload.get("created_at")
        repo.pushed_at = payload.get("pushed_at")
        enriched += 1
    return enriched, errors


def collect(
    store: Store,
    options: CollectOptions,
    progress: Optional[ProgressFn] = None,
) -> CollectResult:
    result = CollectResult()
    fetched: dict[str, list[TrendingRepo]] = {}

    def report(kind: str, text: str) -> None:
        if progress:
            progress(kind, text)

    # 阶段 1：抓取 Trending 语言页
    report("phase", "抓取 GitHub Trending 语言页")
    total_langs = len(options.languages)
    done_langs = 0
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fetch_trending, lang, options.since, options.token): lang
            for lang in options.languages
        }
        for future in as_completed(futures):
            lang = futures[future]
            done_langs += 1
            try:
                fetched[lang] = future.result()
                report("update", f"  {done_langs}/{total_langs} 完成: {lang or 'all'}")
            except FetchError as err:
                result.warnings.append(f"trending {lang or 'all'}: {err}")
                report("update", f"  {done_langs}/{total_langs} 完成: {lang or 'all'}（失败）")

    merged: dict[str, TrendingRepo] = {}
    total_raw = 0
    for lang in options.languages:
        for repo in fetched.get(lang, []):
            total_raw += 1
            prev = merged.get(repo.full_name)
            if prev is None or (prev.weekly_stars is None and repo.weekly_stars is not None):
                merged[repo.full_name] = repo

    if options.with_search:
        report("phase", "GitHub Search 补充新建 AI 仓库")
        search_repos, search_warnings = _search_new_ai_repos(options.token, progress=progress)
        result.warnings.extend(search_warnings)
        for repo in search_repos:
            prev = merged.get(repo.full_name)
            if prev is None or (prev.weekly_stars is None and repo.weekly_stars is not None):
                merged[repo.full_name] = repo

    final_repos = list(merged.values())
    final_repos = annotate_ai_repos(final_repos)
    if options.ai_only:
        final_repos = [repo for repo in final_repos if repo.ai_reasons]

    if options.api_top > 0:
        report("phase", "GitHub API 补全仓库元数据")
        enriched, errors = _enrich_top(final_repos, options.api_top, options.token, progress=progress)
        result.warnings.extend(errors)
        result.sources["api-enrich"] = enriched

    result.collected_at = utc_now()
    store.save_repos(final_repos, result.collected_at)
    store.set_meta("last_collect_at", result.collected_at)

    for repo in final_repos:
        result.sources[repo.source] = result.sources.get(repo.source, 0) + 1
    result.stored = len(final_repos)
    result.ai_count = sum(1 for repo in final_repos if repo.ai_reasons)
    result.skipped = max(total_raw - result.stored, 0)

    # 每次拉取登记为一个任务，AI 负责生成仓库简介与任务总结；失败不阻断采集。
    result.task_id = store.create_task(
        result.collected_at,
        repo_count=result.stored,
        ai_count=result.ai_count,
        since=options.since,
    )
    task_error: Optional[str] = None
    if options.with_ai:
        if final_repos:
            report("phase", "AI 生成仓库一句话简介")

            def _batch_progress(done: int, total: int) -> None:
                report("update", f"  批次 {done}/{total}")

            summaries, summary_warnings = summarize_repo_batch(final_repos, progress=_batch_progress)
            result.warnings.extend(summary_warnings)
            for repo, summary in zip(final_repos, summaries):
                if summary:
                    repo.ai_summary = summary
                    result.summarized_repos += 1
            if result.summarized_repos:
                store.save_repos(final_repos, result.collected_at)
        report("phase", "AI 生成任务总结")
        task_summary, summary_error = summarize_task(
            build_report(store.load_latest(limit=1000), limit=50)["items"]
        )
        if summary_error:
            result.warnings.append(summary_error)
            # 未配置 AI 只是降级提示，不算任务失败。
            if not summary_error.startswith("未配置"):
                task_error = summary_error
        else:
            result.task_summary = task_summary
    store.finish_task(result.task_id, summary=result.task_summary, error=task_error)
    return result
