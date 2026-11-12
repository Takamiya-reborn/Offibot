# Agent 主循环:基于 OpenAI Chat Completions 的 function calling

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openai import OpenAI

from offibot.core.config import Settings, app_work_dir
from offibot.tools import base as tool_registry

SYSTEM_PROMPT = """你是 Offibot,一个命令行 Office 助手,可以帮助用户创建和编辑 \
Word(.docx)、Excel(.xlsx)、PowerPoint(.pptx) 文件。

工作方式:
1. 先理解任务,判断是否需要使用工具;涉及文件操作时必须调用工具完成。
2. 如果任务与某个技能相关,先调用 list_skills 查看可用技能,再用 load_skill \
加载对应技能,并严格按技能中的说明执行。
3. 生成的最终文件默认按类型自动归类:只传文件名即可,Word 会存到 .output/docx/,\
Excel 存到 .output/xlsx/,PowerPoint 存到 .output/pptx/(目录自动创建)。仅当用户 \
明确要求其他位置时才传带目录的路径。工具返回值包含实际保存路径,汇报时以此为准。
4. 任务过程中的中间/草稿内容(对比数据、大纲、临时清单等)用 save_intermediate \
保存到工作区,不要混进最终产出目录;需要时用 read_intermediate / list_intermediate 取回。
5. 每一步工具调用后,根据结果决定下一步;任务完成后用简短中文总结结果。
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
        self._history: list[dict[str, Any]] = []
        self.reset()
        self._log_path = _init_log_file()

    def _log(self, text: str) -> None:
        # 会话过程写入 .offibot/logs/,失败不影响主流程
        try:
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(text.rstrip("\n") + "\n")
        except OSError:
            pass

    @property
    def history(self) -> list[dict[str, Any]]:
        return self._history

    def reset(self) -> None:
        self._history = [{"role": "system", "content": self.system_prompt}]

    def run(self, user_input: str) -> str:
        # 执行一轮完整任务(可能含多次工具调用),返回最终回复文本
        self._history.append({"role": "user", "content": user_input})
        self._log(f"\n[{_now()}] USER: {user_input}")
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
                self._log(f"[{_now()}] ASSISTANT: {content}")
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
                    if not isinstance(kwargs, dict):
                        raise ValueError("arguments 必须是 JSON 对象")
                except (json.JSONDecodeError, ValueError) as exc:
                    # 参数不是合法 JSON 时明确回传错误,而不是带着空参数执行
                    result = f"工具参数不是合法 JSON 对象({exc}),请重新调用 {name} 并给出完整的 JSON 参数。"
                    self._log(f"[{_now()}] TOOL {name} 参数解析失败: {exc}")
                    self.on_tool_result(name, result)
                    self._history.append(
                        {"role": "tool", "tool_call_id": call.id, "content": result}
                    )
                    continue
                tool = tool_registry.get_tool(name)
                if tool is None:
                    result = f"错误: 未注册的工具 '{name}'"
                else:
                    try:
                        self.on_tool_call(name, kwargs)
                        result = tool.run(**kwargs)
                    except Exception as exc:  # 工具报错回传给模型自行修正
                        result = f"工具执行出错: {type(exc).__name__}: {exc}"
                self._log(
                    f"[{_now()}] TOOL {name}({json.dumps(kwargs, ensure_ascii=False)})\n"
                    f"  -> {result[:500]}"
                )
                self.on_tool_result(name, result)
                self._history.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )

        max_turns_note = (
            "(已达最大工具调用轮数,任务未完成,请尝试拆分任务或调大 OFFIBOT_MAX_TURNS)"
        )
        self._history.append({"role": "assistant", "content": max_turns_note})
        self._log(f"[{_now()}] {max_turns_note}")
        return max_turns_note


def _init_log_file() -> Path:
    # 本次会话的日志文件:.offibot/logs/年月日-时分秒.log
    try:
        log_dir = app_work_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"{time.strftime('%Y%m%d-%H%M%S')}.log"
    except OSError:
        # 目录创建失败时退到临时文件,保证 _log() 不抛异常
        import tempfile

        return Path(tempfile.gettempdir()) / "offibot-unusable.log"


def _now() -> str:
    return time.strftime("%H:%M:%S")


def _default_on_tool_call(name: str, kwargs: dict[str, Any]) -> None:
    print(f"  ⚙ {name}({', '.join(f'{k}=...' for k in kwargs)})")


def _default_on_tool_result(name: str, result: str) -> None:
    preview = result if len(result) <= 120 else result[:120] + "..."
    print(f"  ✓ {preview}")
