# 模型草稿区工具:中间文件统一存放在 .offibot/drafts/,不混进 .output/ 最终产出

from __future__ import annotations

from pathlib import Path

from offibot.core.config import app_work_dir
from offibot.tools.base import tool

_DRAFTS_SUBDIR = "drafts"


def _drafts_dir() -> Path:
    d = app_work_dir() / _DRAFTS_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(name: str) -> Path:
    # 校验草稿文件名:必须是相对路径,不允许目录穿越
    p = Path(name)
    if p.is_absolute() or ".." in p.parts or not p.name:
        raise ValueError(
            f"非法文件名 '{name}':只能使用工作区内的相对文件名(如 notes.txt 或 temp/data.md)"
        )
    return _drafts_dir() / p


@tool
def save_intermediate(name: str, content: str) -> str:
    """把中间/草稿文件保存到模型工作区(不会出现在最终产出目录中)。

    Args:
        name: 文件名,相对于工作区,例如 notes.txt 或 temp/outline.md
        content: 要写入的文本内容
    """
    p = _safe_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"已保存到工作区: {p.resolve()}"


@tool
def read_intermediate(name: str, max_chars: int = 20000) -> str:
    """读取之前保存在工作区的中间/草稿文件内容。

    Args:
        name: 文件名,相对于工作区
        max_chars: 返回文本的最大字符数
    """
    p = _safe_path(name)
    if not p.is_file():
        return f"文件不存在: {name}(可用 list_intermediate 查看已有文件)"
    text = p.read_text(encoding="utf-8")
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n...[已截断,共 {len(text)} 字符]"
    return text


@tool
def list_intermediate() -> str:
    """列出工作区中已保存的全部中间/草稿文件。"""
    d = _drafts_dir()
    files = sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file())
    if not files:
        return "(工作区为空)"
    return "工作区文件:\n" + "\n".join(f"- {f}" for f in files)
