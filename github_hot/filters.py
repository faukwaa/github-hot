from __future__ import annotations

import re
from typing import Iterable

from .models import TrendingRepo

AI_KEYWORDS = {
    "agent",
    "agents",
    "agi",
    "ai",
    "ai-agents",
    "agentic",
    "artificial-intelligence",
    "asr",
    "autogen",
    "chatgpt",
    "claude",
    "computer-vision",
    "copilot",
    "crewai",
    "deep-learning",
    "deepseek",
    "diffusers",
    "diffusion",
    "dspy",
    "embedding",
    "embeddings",
    "fine-tuning",
    "finetuning",
    "gemini",
    "generative",
    "genai",
    "ggml",
    "gguf",
    "gpt",
    "gpt-4",
    "gpt4",
    "gradio",
    "inference",
    "keras",
    "langchain",
    "llama",
    "llm",
    "llms",
    "llmops",
    "machine-learning",
    "mcp",
    "milvus",
    "mistral",
    "mlx",
    "multimodal",
    "neural",
    "neural-network",
    "nlp",
    "object-detection",
    "ocr",
    "ollama",
    "openai",
    "prompt",
    "pytorch",
    "qwen",
    "rag",
    "rlhf",
    "sglang",
    "speech-to-text",
    "stable-diffusion",
    "tensorflow",
    "text-to-image",
    "text-to-speech",
    "tokenizer",
    "transformer",
    "transformers",
    "tts",
    "vllm",
    "whisper",
    "yolo",
}

CHINESE_KEYWORDS = {
    "人工智能",
    "大模型",
    "多模态",
    "机器学习",
    "深度学习",
    "神经网络",
    "生成式",
    "文生图",
    "智能",
    "智能体",
}

PHRASE_KEYWORDS = {
    "large language model",
    "large language models",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "natural language processing",
    "computer vision",
    "stable diffusion",
    "text to speech",
    "speech to text",
    "text to image",
}

_TOKEN_RE = re.compile(r"[a-z0-9+#._-]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def match_repo(repo: TrendingRepo) -> tuple[bool, list[str]]:
    """按名称、简介与 topics 判断是否为 AI 项目，并返回命中原因。"""
    reasons: list[str] = []
    seen: set[str] = set()

    text = f"{repo.full_name} {repo.description or ''} {repo.language or ''}"
    lowered = re.sub(r"\s+", " ", text.lower())
    tokens = _tokens(text)

    for keyword in AI_KEYWORDS:
        if keyword in tokens and keyword not in seen:
            reasons.append(f"name/desc:{keyword}")
            seen.add(keyword)
    for keyword in CHINESE_KEYWORDS:
        if keyword in lowered and keyword not in seen:
            reasons.append(f"name/desc:{keyword}")
            seen.add(keyword)
    for phrase in PHRASE_KEYWORDS:
        if phrase in lowered and f"phrase:{phrase}" not in reasons:
            reasons.append(f"phrase:{phrase}")

    topic_set = {topic.lower() for topic in repo.topics}
    for keyword in AI_KEYWORDS:
        if keyword in topic_set and f"topic:{keyword}" not in reasons:
            reasons.append(f"topic:{keyword}")
    for keyword in CHINESE_KEYWORDS:
        if keyword in topic_set and f"topic:{keyword}" not in reasons:
            reasons.append(f"topic:{keyword}")

    return bool(reasons), reasons[:8]


def filter_ai_repos(repos: Iterable[TrendingRepo]) -> list[TrendingRepo]:
    return [repo for repo in annotate_ai_repos(repos) if repo.ai_reasons]


def annotate_ai_repos(repos: Iterable[TrendingRepo]) -> list[TrendingRepo]:
    """给每个仓库标注是否 AI，不删除任何项目。"""
    kept: list[TrendingRepo] = []
    for repo in repos:
        _, reasons = match_repo(repo)
        repo.ai_reasons = reasons
        kept.append(repo)
    return kept
