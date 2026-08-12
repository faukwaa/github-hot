from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class TrendingRepo:
    """一次采集得到的仓库热度快照。"""

    full_name: str
    url: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    weekly_stars: Optional[int] = None
    source: str = "trending"
    created_at: Optional[str] = None
    pushed_at: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    ai_reasons: list[str] = field(default_factory=list)
    ai_summary: Optional[str] = None

    @property
    def owner(self) -> str:
        return self.full_name.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.full_name.split("/", 1)[-1]

    @property
    def is_ai(self) -> bool:
        return bool(self.ai_reasons)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["owner"] = self.owner
        data["name"] = self.name
        return data
