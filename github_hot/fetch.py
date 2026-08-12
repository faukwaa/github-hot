from __future__ import annotations

import json
import http.client
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from . import config


class FetchError(RuntimeError):
    pass


def _headers(token: Optional[str], accept: Optional[str]) -> dict[str, str]:
    headers = {"User-Agent": config.USER_AGENT}
    if accept:
        headers["Accept"] = accept
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(
    url: str,
    token: Optional[str] = None,
    accept: Optional[str] = None,
    timeout: Optional[int] = None,
) -> tuple[str, int, dict[str, str]]:
    last_error: Optional[Exception] = None
    for attempt in range(config.MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=_headers(token, accept))
            with urllib.request.urlopen(req, timeout=timeout or config.REQUEST_TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return body, resp.status, dict(resp.headers)
        except urllib.error.HTTPError as err:
            last_error = err
            detail = ""
            if err.fp:
                detail = err.fp.read(2000).decode("utf-8", errors="replace")
            if err.code in (403, 429) and attempt < config.MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
            raise FetchError(f"HTTP {err.code} for {url}: {detail[:300]}") from err
        except urllib.error.URLError as err:
            last_error = err
            if attempt < config.MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
            raise FetchError(f"Network error for {url}: {err.reason}") from err
        except (socket.timeout, TimeoutError) as err:
            last_error = err
            if attempt < config.MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
            raise FetchError(f"Timeout for {url}: {err}") from err
        except (http.client.HTTPException, OSError) as err:
            last_error = err
            if attempt < config.MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
            raise FetchError(f"Connection error for {url}: {err}") from err
    raise FetchError(f"Fetch failed for {url}: {last_error}")


def get_json(url: str, token: Optional[str] = None, timeout: Optional[int] = None) -> Any:
    body, _, _ = _request(url, token=token, accept="application/vnd.github+json", timeout=timeout)
    return json.loads(body)


def get_text(url: str, token: Optional[str] = None, timeout: Optional[int] = None) -> str:
    body, _, _ = _request(url, token=token, timeout=timeout)
    return body
