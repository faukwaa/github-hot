from __future__ import annotations

import os

# 默认数据库固定在项目根目录，避免在不同工作目录运行时误建新库
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(_PROJECT_ROOT, "data", "github_hot.db")
DEFAULT_LIMIT = 30
DEFAULT_TOP_API = 30
DEFAULT_SINCE = "weekly"

TRENDING_URL = "https://github.com/trending/{lang}?since={since}"
API_BASE_URL = "https://api.github.com"

# AI 总结（OpenAI 兼容接口）：默认关闭，配置 AI_API_KEY / DEEPSEEK_API_KEY 后自动开启。
AI_BASE_URL = "https://api.openai.com/v1"
AI_MODEL = "gpt-4o-mini"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
AI_BATCH_SIZE = 20  # 一句话简介每次请求处理的仓库数

USER_AGENT = "github-hot/0.1 (AI open source research tool)"
REQUEST_TIMEOUT = 25
MAX_RETRIES = 4

# 空字符串表示 GitHub Trending 的“全部语言”页。
DEFAULT_LANGUAGES = [
    "",
    "python",
    "typescript",
    "javascript",
    "go",
    "rust",
    "c++",
    "jupyter-notebook",
]

SEARCH_TOPICS = [
    "ai",
    "llm",
    "machine-learning",
    "artificial-intelligence",
    "deep-learning",
    "rag",
    "agents",
    "gpt",
]


_ENV_FILE = os.path.join(_PROJECT_ROOT, ".env")


def _load_dotenv(path: str = _ENV_FILE) -> None:
    """加载项目根目录 .env（标准库实现，不覆盖已有环境变量）。"""
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except OSError:
        pass


_load_dotenv()


def github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


def ai_config() -> tuple[str, str, str] | None:
    """返回 (base_url, api_key, model)；未配置 API Key 时返回 None。

    优先级：AI_API_KEY > DEEPSEEK_API_KEY > OPENAI_API_KEY。
    使用 DEEPSEEK_API_KEY 时默认走 DeepSeek 端点与 deepseek-chat 模型，
    AI_BASE_URL / AI_MODEL 环境变量可覆盖。
    """
    api_key = (
        os.environ.get("AI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or None
    )
    if not api_key:
        return None
    is_deepseek = api_key == os.environ.get("DEEPSEEK_API_KEY") and not os.environ.get("AI_API_KEY")
    base_url = os.environ.get("AI_BASE_URL") or (
        DEEPSEEK_BASE_URL if is_deepseek else AI_BASE_URL
    )
    model = os.environ.get("AI_MODEL") or (
        DEEPSEEK_MODEL if is_deepseek else AI_MODEL
    )
    return base_url.rstrip("/"), api_key, model
