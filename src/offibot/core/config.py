# 全局配置:从 .env 与环境变量读取;目录约定(.output / .offibot)也在这里

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def app_root() -> Path:
    # 应用根目录:开发环境=项目根目录,PyInstaller 打包后=exe 所在目录
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def app_output_dir() -> Path:
    # 生成文件的默认输出根目录:.output
    return app_root() / ".output"


def app_work_dir() -> Path:
    # 程序工作目录(模型草稿、日志等内部数据):.offibot
    return app_root() / ".offibot"


_ENV_FILE_CANDIDATES = (
    Path.cwd() / ".env",
    app_root() / ".env",
)


def _load_env_file() -> None:
    # 极简 .env 加载(KEY=VALUE,支持 # 注释),不覆盖已存在的环境变量
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
                "未找到 OPENAI_API_KEY。请在程序所在目录新建 .env 文件(内容: "
                "OPENAI_API_KEY=你的密钥),或在系统环境变量中设置 OPENAI_API_KEY。"
                "开发环境也可放在项目根目录的 .env(参考 .env.example)。"
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
            model=model or os.environ.get("OFFIBOT_MODEL", "gpt-4o-mini"),
            max_turns=int(os.environ.get("OFFIBOT_MAX_TURNS", "20")),
            skills_dir=skills_dir,
        )
