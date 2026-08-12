from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

from . import config
from .models import TrendingRepo

_TASK_SYSTEM = (
    "你是开源技术观察助手，擅长从榜单数据里提炼一周热点。"
    "只输出 JSON，不要输出任何解释。"
)

_REPO_SYSTEM = (
    "你是开源项目简介撰稿人，能用一句话说清一个仓库是做什么的。"
    "只输出 JSON，不要输出任何解释。"
)

_TRANSLATE_SYSTEM = (
    "你是资深技术文档译者，擅长把英文 README 翻译成通顺、专业的中文。"
    "保留所有 Markdown 标记、代码块、链接 URL、图片路径、表格结构与专有名词不变，"
    "只翻译自然语言部分。不要使用 em-dash（——或—），用逗号或句号替代。"
    "只输出 JSON，不要输出任何解释。"
)

_TRANSLATE_CHUNK = 3200  # 单次翻译的最大字符数（按段落切块）


class AIError(RuntimeError):
    pass


def _chat(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: int = 120,
) -> str:
    """调用 OpenAI 兼容 chat completions 接口，返回文本内容。

    优先请求 JSON 输出模式；服务商不支持时（HTTP 400）降级为普通模式重试。
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for use_json_mode in (True, False):
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.4,
        }
        if use_json_mode:
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
            break
        except urllib.error.HTTPError as err:
            detail = ""
            if err.fp:
                detail = err.fp.read(1000).decode("utf-8", errors="replace")
            if err.code == 400 and use_json_mode:
                continue  # 部分兼容服务不支持 response_format，降级重试
            raise AIError(f"AI 接口 HTTP {err.code}: {detail[:300]}") from err
        except (urllib.error.URLError, OSError) as err:
            raise AIError(f"AI 接口请求失败: {err}") from err
    else:
        raise AIError("AI 接口无法返回有效内容")

    try:
        return body["choices"][0]["message"]["content"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as err:
        raise AIError(f"AI 接口响应格式异常: {body}") from err


def _parse_json(raw: str) -> Optional[dict[str, Any]]:
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def summarize_task(items: list[dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    """对一次采集生成任务总结。返回 (总结文本, 错误信息)，至少一个为 None。"""
    ai = config.ai_config()
    if ai is None:
        return None, "未配置 AI_API_KEY / DEEPSEEK_API_KEY，跳过任务总结"
    base_url, api_key, model = ai

    lines: list[str] = []
    for rank, item in enumerate(items[:15], start=1):
        summary = item.get("ai_summary") or item.get("description") or ""
        lines.append(
            f"{rank}. {item['full_name']} "
            f"(语言: {item.get('language') or '未知'}, 本周 +{item.get('weekly_stars') or 0} Star) "
            f"简介: {summary[:120]}"
        )
    user_prompt = (
        "下面是最近一周 Star 增长最快的开源项目榜单：\n"
        + "\n".join(lines)
        + "\n\n请用 120 字以内的中文写一段任务总结，包含：本周热点方向、"
        "最值得关注的 2 到 3 个项目及原因、一句趋势展望。"
        '只输出 JSON: {"summary": "总结文本"}'
    )
    try:
        raw = _chat(
            base_url,
            api_key,
            model,
            [
                {"role": "system", "content": _TASK_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
    except AIError as err:
        return None, str(err)

    parsed = _parse_json(raw)
    if parsed and isinstance(parsed.get("summary"), str) and parsed["summary"].strip():
        return parsed["summary"].strip(), None
    if raw and raw.strip() and not raw.strip().startswith("{"):
        return raw.strip()[:300], None
    return None, "任务总结返回格式无法解析"


def summarize_repo_batch(
    repos: list[TrendingRepo],
    progress: Optional[Callable[[int, int], None]] = None,
) -> tuple[list[Optional[str]], list[str]]:
    """批量生成一句话简介，按输入顺序返回；失败项为 None 并记录警告。

    progress 回调接收 (已完成批次, 总批次)。
    """
    ai = config.ai_config()
    if ai is None:
        return [None] * len(repos), ["未配置 AI_API_KEY / DEEPSEEK_API_KEY，跳过仓库简介"]
    base_url, api_key, model = ai

    summaries: list[Optional[str]] = [None] * len(repos)
    warnings: list[str] = []
    total_batches = max((len(repos) + config.AI_BATCH_SIZE - 1) // config.AI_BATCH_SIZE, 1)
    for start in range(0, len(repos), config.AI_BATCH_SIZE):
        if progress:
            progress(start // config.AI_BATCH_SIZE + 1, total_batches)
        chunk = repos[start : start + config.AI_BATCH_SIZE]
        lines: list[str] = []
        for index, repo in enumerate(chunk):
            topics = ", ".join(repo.topics[:6]) if repo.topics else "无"
            lines.append(
                f"{index + 1}. full_name: {repo.full_name} | language: {repo.language or '未知'} "
                f"| stars: {repo.stars} | topics: {topics} | description: {(repo.description or '无')[:200]}"
            )
        user_prompt = (
            "为下面的 GitHub 仓库各写一句中文简介（25 到 45 字），"
            "说明该项目是做什么的、解决什么问题。不要用 em-dash，不要加引号。\n"
            + "\n".join(lines)
            + "\n\n直接输出 JSON: "
            '{"summaries": ["简介1", "简介2", ...]}，数量与输入一致'
        )
        try:
            raw = _chat(
                base_url,
                api_key,
                model,
                [
                    {"role": "system", "content": _REPO_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except AIError as err:
            warnings.append(f"仓库简介批次 {start // config.AI_BATCH_SIZE + 1}: {err}")
            continue

        parsed = _parse_json(raw)
        batch: list[Any] = []
        if parsed and isinstance(parsed.get("summaries"), list):
            batch = parsed["summaries"]
        if len(batch) != len(chunk):
            warnings.append(
                f"仓库简介批次 {start // config.AI_BATCH_SIZE + 1} 返回数量不符"
                f"（{len(batch)}/{len(chunk)}），该批跳过"
            )
            continue
        for offset, text in enumerate(batch):
            if isinstance(text, str) and text.strip():
                summaries[start + offset] = text.strip()
    return summaries, warnings


def is_mostly_chinese(text: str, sample: int = 2000) -> bool:
    """粗略判断文本是否以中文为主（采样前 N 个字符）。"""
    head = text[:sample]
    if not head:
        return False
    chinese = sum(1 for ch in head if "\u4e00" <= ch <= "\u9fff")
    return chinese / len(head) > 0.15


def _split_chunks(text: str, limit: int = _TRANSLATE_CHUNK) -> list[str]:
    """按段落切分文本为不超过 limit 字符的块，避免切断代码块。"""
    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        if not para.strip():
            continue
        if len(current) + len(para) + 2 <= limit:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > limit:
                # 超长段落（多为代码块）按行切分
                for start in range(0, len(para), limit):
                    chunks.append(para[start : start + limit])
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


def translate_text(text: str) -> tuple[Optional[str], Optional[str]]:
    """把英文 README 翻译成中文。返回 (译文, 错误信息)，失败时译文为 None。"""
    ai = config.ai_config()
    if ai is None:
        return None, "未配置 AI_API_KEY / DEEPSEEK_API_KEY，无法翻译"
    base_url, api_key, model = ai

    chunks = _split_chunks(text)
    translated_parts: list[str] = []
    for index, chunk in enumerate(chunks):
        user_prompt = (
            f"请把下面的 README 内容（第 {index + 1}/{len(chunks)} 部分）翻译成中文，"
            "保留 Markdown 标记、代码、URL 与表格结构：\n\n"
            + chunk
            + '\n\n只输出 JSON: {"translation": "译文"}'
        )
        try:
            raw = _chat(
                base_url,
                api_key,
                model,
                [
                    {"role": "system", "content": _TRANSLATE_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except AIError as err:
            return None, f"翻译第 {index + 1}/{len(chunks)} 块失败: {err}"
        parsed = _parse_json(raw)
        if parsed and isinstance(parsed.get("translation"), str) and parsed["translation"].strip():
            translated_parts.append(parsed["translation"].strip())
        else:
            return None, f"翻译第 {index + 1}/{len(chunks)} 块返回格式无法解析"
    return "\n\n".join(translated_parts), None
