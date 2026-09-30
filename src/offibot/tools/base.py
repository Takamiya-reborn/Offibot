"""工具基类与注册表。

用法::

    from offibot.tools.base import tool

    @tool
    def docx_read(path: str, max_chars: int = 8000) -> str:
        \"\"\"读取 Word 文档的全部文本内容。

        Args:
            path: 文档路径
            max_chars: 返回文本的最大字符数

        ...

装饰器会从类型注解和 docstring 自动生成 OpenAI function calling 的 JSON Schema,
工具函数返回 str(非 str 返回值会被自动转成 str)。
"""

from __future__ import annotations

import inspect
import types
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, get_args, get_origin, get_type_hints

_TOOLS: dict[str, "Tool"] = {}

_MAX_OUTPUT_CHARS = 20_000

# 默认输出目录:模型只传文件名时,按扩展名归类到 ./docx ./xlsx ./pptx
_OUTPUT_DIRS = {".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx"}


def resolve_output(path: str | Path) -> Path:
    """解析输出路径:未指定目录的文件名重定向到对应的默认目录;父目录不存在则自动创建。"""
    p = Path(path)
    out_dir = _OUTPUT_DIRS.get(p.suffix.lower())
    if p.parent == Path(".") and out_dir:
        p = Path.cwd() / out_dir / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def resolve_existing(path: str | Path) -> Path:
    """解析已有文件路径:裸文件名在当前目录找不到时,去默认输出目录找。"""
    p = Path(path)
    if p.parent == Path(".") and not p.is_file():
        out_dir = _OUTPUT_DIRS.get(p.suffix.lower())
        if out_dir:
            candidate = Path.cwd() / out_dir / p
            if candidate.is_file():
                return candidate
    return p


_PY_TYPE_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict[str, Any] = field(default_factory=dict)
    category: str = "general"

    def run(self, **kwargs: Any) -> str:
        result = self.func(**kwargs)
        if result is None:
            return "OK"
        text = str(result)
        if len(text) > _MAX_OUTPUT_CHARS:
            text = (
                text[:_MAX_OUTPUT_CHARS] + f"\n...[输出过长,已截断,共 {len(text)} 字符]"
            )
        return text


def _json_type(annotation: Any) -> dict[str, Any]:
    """把 Python 类型注解映射为 JSON Schema 片段。"""
    if annotation in (inspect.Signature.empty, Any):
        return {"type": "string"}

    origin = get_origin(annotation)
    if origin is typing.Union or (
        isinstance(origin, type) and issubclass(origin, types.UnionType)
    ):
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            return _json_type(non_none[0])
        return {"type": "string"}

    if origin in (list, typing.List):
        args = get_args(annotation)
        items = _json_type(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": items}
    if origin in (dict, typing.Dict):
        return {"type": "object"}

    if annotation in _PY_TYPE_TO_JSON:
        return {"type": _PY_TYPE_TO_JSON[annotation]}
    if annotation is Path:
        return {"type": "string"}
    if isinstance(annotation, type) and issubclass(annotation, (list, dict)):
        return {"type": _PY_TYPE_TO_JSON.get(annotation, "string")}
    return {"type": "string"}


def _parse_docstring(func: Callable[..., Any]) -> tuple[str, dict[str, str]]:
    """取 docstring 第一段作为描述,解析 Args: 段落得到每个参数的说明。"""
    doc = inspect.getdoc(func) or ""
    lines = doc.splitlines()
    param_docs: dict[str, str] = {}
    description_lines: list[str] = []
    in_args = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().rstrip(":") in ("args", "arguments", "parameters"):
            in_args = True
            continue
        if stripped.lower().startswith(("returns", "raises", "yields")):
            in_args = False
            continue
        if in_args:
            if ":" in stripped and stripped.split(":")[0].split()[0].isidentifier():
                name, _, desc = stripped.partition(":")
                param_docs[name.strip()] = desc.strip()
        elif stripped:
            description_lines.append(stripped)
    return "\n".join(description_lines).strip(), param_docs


def _build_schema(func: Callable[..., Any]) -> dict[str, Any]:
    hints = get_type_hints(func)
    signature = inspect.signature(func)
    description, param_docs = _parse_docstring(func)
    if not description:
        description = func.__name__

    properties: dict[str, Any] = {}
    required: list[str] = []
    for param_name, param in signature.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        annotation = hints.get(param_name, str)
        schema = _json_type(annotation)
        if param_name in param_docs:
            schema["description"] = param_docs[param_name]
        properties[param_name] = schema
        if param.default is inspect.Signature.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """注册一个工具函数,函数本身原样返回。"""
    schema = _build_schema(func)
    registered = Tool(
        name=schema["function"]["name"],
        description=schema["function"]["description"],
        func=func,
        parameters=schema,
        category=func.__module__.rsplit(".", 1)[-1],
    )
    if registered.name in _TOOLS:
        raise ValueError(f"工具重名: {registered.name}")
    _TOOLS[registered.name] = registered
    return func


def register_tool(func: Callable[..., Any], *, name: str | None = None) -> None:
    """以编程方式注册工具(用于闭包/带状态的内置工具)。"""
    schema = _build_schema(func)
    if name:
        schema["function"]["name"] = name
        # name 也必须与函数名一致,运行时按 name 分发
    registered = Tool(
        name=schema["function"]["name"],
        description=schema["function"]["description"],
        func=func,
        parameters=schema,
        category="builtin",
    )
    if registered.name in _TOOLS:
        raise ValueError(f"工具重名: {registered.name}")
    _TOOLS[registered.name] = registered


def get_tools() -> dict[str, Tool]:
    return dict(_TOOLS)


def get_tool_schemas() -> list[dict[str, Any]]:
    return [t.parameters for t in _TOOLS.values()]


def get_tool(name: str) -> Tool | None:
    return _TOOLS.get(name)


def clear_tools() -> None:
    """仅测试用。"""
    _TOOLS.clear()
