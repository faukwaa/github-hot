from __future__ import annotations

import html as html_module
import re
from typing import Optional
from urllib.parse import quote

from . import config
from .fetch import get_text
from .models import TrendingRepo

_ARTICLE_RE = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)
_HREF_RE = re.compile(r'<h2[^>]*>.*?href="/([^/"]+/[^/"]+)"', re.S)
_DESC_RE = re.compile(r'<p[^>]*class="col-9[^"]*"[^>]*>(.*?)</p>', re.S)
_LINK_RE = re.compile(r'href="/' + r"({full})" + r'/(stargazers|forks|network/members)"[^>]*>(.*?)</a>', re.S)
_WEEKLY_RE = re.compile(r"([\d,]+)\s+stars this week", re.S)
_MR3_SPAN_RE = re.compile(r'class="d-inline-block mr-3">(.*?)</span>', re.S)
_LANG_RE = re.compile(r'itemprop="programmingLanguage">([^<]+)<')


def _clean(raw: Optional[str]) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", "", raw)
    return html_module.unescape(re.sub(r"\s+", " ", text)).strip()


def _to_int(raw: Optional[str], default: int = 0) -> int:
    text = _clean(raw).replace(",", "")
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


def _extract_language(chunk: str) -> Optional[str]:
    lang_match = _LANG_RE.search(chunk)
    if lang_match:
        language = _clean(lang_match.group(1))
        if language:
            return language
    for raw in _MR3_SPAN_RE.findall(chunk):
        part = _clean(raw)
        if not part:
            continue
        lowered = part.lower()
        if re.fullmatch(r"[\d,]+", part) or "stars" in lowered or lowered == "built by":
            continue
        if re.fullmatch(r"[A-Za-z0-9#+.' ]+", part):
            return part
    return None


def parse_trending_html(html: str) -> list[TrendingRepo]:
    repos: list[TrendingRepo] = []
    for match in _ARTICLE_RE.finditer(html):
        chunk = match.group(0)
        href_match = _HREF_RE.search(chunk)
        if not href_match:
            continue
        full_name = href_match.group(1)

        stars = 0
        forks = 0
        link_re = re.compile(
            r'href="/' + re.escape(full_name) + r'/(stargazers|forks)"[^>]*>(.*?)</a>', re.S
        )
        for link_match in link_re.finditer(chunk):
            kind = link_match.group(1)
            value = _to_int(link_match.group(2))
            if kind == "stargazers":
                stars = value
            elif kind == "forks":
                forks = value

        weekly_raw = _WEEKLY_RE.search(chunk)
        weekly_stars = _to_int(weekly_raw.group(1)) if weekly_raw else None

        desc_raw = _DESC_RE.search(chunk)
        description = _clean(desc_raw.group(1)) if desc_raw else None

        repos.append(
            TrendingRepo(
                full_name=full_name,
                url=f"https://github.com/{full_name}",
                description=description or None,
                language=_extract_language(chunk),
                stars=stars,
                forks=forks,
                weekly_stars=weekly_stars,
            )
        )
    return repos


def fetch_trending(language: str = "", since: str = "weekly", token: Optional[str] = None) -> list[TrendingRepo]:
    url = config.TRENDING_URL.format(lang=quote(language, safe=""), since=since)
    html = get_text(url, token=token)
    repos = parse_trending_html(html)
    for repo in repos:
        repo.source = f"trending:{language or 'all'}"
    return repos
