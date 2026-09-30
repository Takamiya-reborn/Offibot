"""PowerPoint (.pptx) 工具。"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation

from offibot.tools.base import resolve_existing, resolve_output, tool


@tool
def pptx_read(path: str) -> str:
    """读取 PowerPoint 演示文稿的文本内容(逐页列出标题与正文)。

    Args:
        path: 演示文稿路径
    """
    prs = Presentation(resolve_existing(path))
    parts: list[str] = [f"共 {len(prs.slides)} 页"]
    for index, slide in enumerate(prs.slides, start=1):
        parts.append(f"--- 第 {index} 页 ---")
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    parts.append(text)
    return "\n".join(parts)


@tool
def pptx_create(path: str, title: str) -> str:
    """创建一个新的 PowerPoint 演示文稿,包含标题页。

    Args:
        path: 输出文件路径(.pptx)
        title: 演示文稿标题
    """
    path = resolve_output(path)
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    prs.save(path)
    return f"已创建 {Path(path).resolve()}"


@tool
def pptx_add_slide(path: str, title: str, content: list[str]) -> str:
    """向演示文稿追加一页,包含标题和若干条要点。

    Args:
        path: 演示文稿路径
        title: 本页标题
        content: 本页要点列表
    """
    path = resolve_existing(path)
    prs = Presentation(path)
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    for index, line in enumerate(content):
        if index == 0:
            body.paragraphs[0].text = line
        else:
            body.add_paragraph().text = line
    prs.save(path)
    return f"已向 {path} 追加一页: {title}"
