# Word (.docx) 工具

from __future__ import annotations

from pathlib import Path

from docx import Document

from offibot.tools.base import resolve_existing, resolve_output, tool


@tool
def docx_read(path: str, max_chars: int = 8000) -> str:
    """读取 Word 文档的全部文本内容(含段落和表格)。

    Args:
        path: 文档路径
        max_chars: 返回文本的最大字符数
    """
    path = resolve_existing(path)
    doc = Document(path)
    parts: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            style = f" [{para.style.name}]" if para.style.name != "Normal" else ""
            parts.append(f"{para.text}{style}")
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    text = "\n".join(parts) or "(空文档)"
    return text[:max_chars]


@tool
def docx_create(path: str, title: str = "", paragraphs: list[str] | None = None) -> str:
    """创建新的 Word 文档,可包含标题和若干段落。

    Args:
        path: 输出文档路径(.docx)
        title: 文档主标题,可为空
        paragraphs: 正文段落列表,按顺序写入
    """
    path = resolve_output(path)
    doc = Document()
    if title:
        doc.add_heading(title, level=0)
    for text in paragraphs or []:
        if text.startswith("# "):
            doc.add_heading(text[2:], level=1)
        elif text.startswith("## "):
            doc.add_heading(text[3:], level=2)
        else:
            doc.add_paragraph(text)
    doc.save(path)
    return f"已创建 {Path(path).resolve()}"


@tool
def docx_append(path: str, text: str, style: str = "") -> str:
    """向已有 Word 文档追加一个段落。

    Args:
        path: 文档路径
        text: 段落内容
        style: 可选样式名,如 Heading 1、List Bullet
    """
    path = resolve_existing(path)
    doc = Document(path)
    para = doc.add_paragraph(text)
    if style:
        para.style = style
    doc.save(path)
    return f"已向 {path} 追加段落"
