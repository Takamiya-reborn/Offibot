# 工具包:导入各工具模块即完成注册(装饰器副作用)

from __future__ import annotations

# 新增工具文件后,在下面加一行 import 即可被自动注册
from offibot.tools import docx_tools, pptx_tools, workspace_tools, xlsx_tools
from offibot.tools.base import (
    clear_tools,
    get_tool,
    get_tool_schemas,
    get_tools,
    register_tool,
    tool,
)

__all__ = [
    "clear_tools",
    "docx_tools",
    "get_tool",
    "get_tool_schemas",
    "get_tools",
    "pptx_tools",
    "register_tool",
    "tool",
    "workspace_tools",
    "xlsx_tools",
]
