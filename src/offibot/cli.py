"""Offibot 命令行入口。

用法:
    offibot chat              交互式对话(默认)
    offibot run "任务描述"     一次性执行任务
    offibot skills list       查看可用技能
    offibot tools list        查看已注册工具
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 导入 tools 包以触发工具注册
import offibot.tools  # noqa: F401
from offibot.core.agent import Agent
from offibot.core.config import Settings
from offibot.core.skill import SkillLoader, make_skill_tools
from offibot.tools import base as tool_registry


def build_agent(args: argparse.Namespace) -> Agent:
    settings = Settings.load(
        skills_dir=Path(args.skills_dir) if args.skills_dir else None,
        model=args.model,
    )
    loader = SkillLoader(
        extra_dirs=[Path(args.skills_dir)] if args.skills_dir else None
    )
    make_skill_tools(loader)
    return Agent(settings)


def cmd_chat(args: argparse.Namespace) -> int:
    agent = build_agent(args)
    loader = SkillLoader()
    print(f"Offibot 已启动 (model: {agent.model})。输入 /exit 退出,/reset 清空对话。")
    print(loader.catalog())
    while True:
        try:
            user_input = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user_input:
            continue
        if user_input in ("/exit", "/quit", "/q"):
            return 0
        if user_input == "/reset":
            agent.reset()
            print("(对话已清空)")
            continue
        if user_input == "/skills":
            print(loader.catalog())
            continue
        try:
            print(agent.run(user_input))
        except KeyboardInterrupt:
            print("\n(已中断本轮任务)")
        except Exception as exc:
            print(f"出错: {exc}", file=sys.stderr)


def cmd_run(args: argparse.Namespace) -> int:
    agent = build_agent(args)
    print(agent.run(args.task))
    return 0


def cmd_skills(_: argparse.Namespace) -> int:
    print(SkillLoader().catalog())
    return 0


def cmd_tools(_: argparse.Namespace) -> int:
    for name, t in sorted(tool_registry.get_tools().items()):
        desc = t.description.splitlines()[0] if t.description else ""
        print(f"- {name} ({t.category}): {desc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Windows 控制台默认 GBK,强制 UTF-8 避免中文乱码
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    parser = argparse.ArgumentParser(
        prog="offibot",
        description="Offibot —— 命令行 Office AI 助手",
    )
    parser.add_argument("--model", help="覆盖模型名(默认读 OFFIBOT_MODEL)")
    parser.add_argument("--skills-dir", help="额外的技能目录(默认: 包内 skills/ 和 ./skills/)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("chat", help="交互式对话").set_defaults(func=cmd_chat)
    run_parser = sub.add_parser("run", help="一次性执行任务")
    run_parser.add_argument("task", help="任务描述")
    run_parser.set_defaults(func=cmd_run)
    sub.add_parser("skills", help="查看可用技能").set_defaults(func=cmd_skills)
    sub.add_parser("tools", help="查看已注册工具").set_defaults(func=cmd_tools)

    args = parser.parse_args(argv)
    if args.command is None:  # 不带子命令时默认进入交互模式
        args.func = cmd_chat
    return args.func(args)
