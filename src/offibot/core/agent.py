"""Agent 主循环:基于 OpenAI Chat Completions 的 function calling。"""

from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI

from offibot.core.config import Settings
from offibot.tools import base as tool_registry

SYSTEM_PROMPT = """你是 Offibot,一个命令行 Office 助手,可以帮助用户创建和编辑 \
Word(.docx)、Excel(.xlsx)、PowerPoint(.pptx) 文件。

工作方式:
1. 先理解任务,判断是否需要使用工具;涉及文件操作时必须调用工具完成。
2. 如果任务与某个技能相关,先调用 list_skills 查看可用技能,再用 load_skill \
加载对应技能,并严格按技能中的说明执行。
3. 生成的文件默认按类型自动归类:只传文件名即可,Word 会存到 ./docx/,Excel 存到 \
./xlsx/,PowerPoint 存到 ./pptx/(目录自动创建)。仅当用户明确要求其他位置时才传 \
带目录的路径。工具返回值包含实际保存路径,汇报时以此为准。
4. 每一步工具调用后,根据结果决定下一步;任务完成后用简短中文总结结果。
"""


class Agent:
    def __init__(
        self,
        settings: Settings,
        *,
        system_prompt: str | None = None,
        on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
    ) -> None:
        self.client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        self.model = settings.model
        self.max_turns = settings.max_turns
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.on_tool_call = on_tool_call or _default_on_tool_call
        self.on_tool_result = on_tool_result or _default_on_tool_result

    @property
    def history(self) -> list[dict[str, Any]]:
        return self._history

    def reset(self) -> None:
        self._history = [{"role": "system", "content": self.system_prompt}]

    def run(self, user_input: str) -> str:
        """执行一轮完整任务(可能包含多次工具调用),返回最终回复文本。"""
        if not hasattr(self, "_history"):
            self.reset()
        self._history.append({"role": "user", "content": user_input})
        schemas = tool_registry.get_tool_schemas()

        for _ in range(self.max_turns):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self._history,  # type: ignore[arg-type]
                tools=schemas or None,
            )
            message = response.choices[0].message

            if not message.tool_calls:
                content = message.content or ""
                self._history.append({"role": "assistant", "content": content})
                return content

            # 记录助手的工具调用请求
            self._history.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in message.tool_calls
                    ],
                }
            )

            for call in message.tool_calls:
                name = call.function.name
                try:
                    kwargs = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    kwargs = {}
                tool = tool_registry.get_tool(name)
                if tool is None:
                    result = f"错误: 未注册的工具 '{name}'"
                else:
                    try:
                        self.on_tool_call(name, kwargs)
                        result = tool.run(**kwargs)
                    except Exception as exc:  # 工具报错回传给模型自行修正
                        result = f"工具执行出错: {type(exc).__name__}: {exc}"
                self.on_tool_result(name, result)
                self._history.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )

        return (
            "(已达最大工具调用轮数,任务未完成,请尝试拆分任务或调大 OFFIBOT_MAX_TURNS)"
        )


def _default_on_tool_call(name: str, kwargs: dict[str, Any]) -> None:
    print(f"  ⚙ {name}({', '.join(f'{k}=...' for k in kwargs)})")


def _default_on_tool_result(name: str, result: str) -> None:
    preview = result if len(result) <= 120 else result[:120] + "..."
    print(f"  ✓ {preview}")
