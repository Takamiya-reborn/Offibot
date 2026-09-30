"""全局配置:从 .env 与环境变量读取。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_ENV_FILE_CANDIDATES = (
    Path.cwd() / ".env",
    Path(__file__).resolve().parents[3] / ".env",
)


def _load_env_file() -> None:
    """极简 .env 加载(KEY=VALUE,支持 # 注释),不覆盖已存在的环境变量。"""
    for candidate in _ENV_FILE_CANDIDATES:
        if not candidate.is_file():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value
        break


@dataclass
class Settings:
    api_key: str
    base_url: str | None
    model: str
    max_turns: int
    skills_dir: Path | None

    @classmethod
    def load(
        cls, *, skills_dir: Path | None = None, model: str | None = None
    ) -> "Settings":
        _load_env_file()
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "未找到 OPENAI_API_KEY,请在项目根目录的 .env 中配置(参考 .env.example)。"
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
            model=model or os.environ.get("OFFIBOT_MODEL", "gpt-4o-mini"),
            max_turns=int(os.environ.get("OFFIBOT_MAX_TURNS", "20")),
            skills_dir=skills_dir,
        )
