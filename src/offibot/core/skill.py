# Skill 加载器:skills 目录下每个 *.md 对应一个技能
# 格式:frontmatter(name/description)+ 正文(技能指令,模型按需加载为上下文)
# 接口:SkillLoader.load() 扫描全部技能;make_skill_tools() 注册 list_skills / load_skill 工具

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offibot.tools.base import register_tool

_BUILTIN_SKILLS_DIR = Path(__file__).resolve().parent.parent / "assets" / "skills"


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    content: str


def _parse_skill_md(path: Path) -> Skill:
    # 解析单个技能 md:frontmatter 取 name/description,缺省用文件名/正文首行
    text = path.read_text(encoding="utf-8")
    name = path.stem
    description = ""
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter, body = parts[1], parts[2].lstrip("\n")
            for line in frontmatter.splitlines():
                key, _, value = line.partition(":")
                key = key.strip().lower()
                if key == "name" and value.strip():
                    name = value.strip()
                elif key == "description" and value.strip():
                    description = value.strip()

    if not description:
        # 没有 frontmatter 时,把正文第一行(非标题)当描述
        for line in body.splitlines():
            line = line.strip().lstrip("#").strip()
            if line:
                description = line
                break
    return Skill(name=name, description=description, path=path, content=body.strip())


class SkillLoader:
    # 扫描一个或多个 skills 目录
    def __init__(self, extra_dirs: list[Path] | None = None) -> None:
        dirs = [_BUILTIN_SKILLS_DIR, Path.cwd() / "skills"]
        if extra_dirs:
            dirs.extend(extra_dirs)
        self.dirs: list[Path] = dirs

    def load(self) -> dict[str, Skill]:
        # 每次调用都重新扫描,支持热更新;_ 开头的文件跳过
        skills: dict[str, Skill] = {}
        for directory in self.dirs:
            if not directory.is_dir():
                continue
            for md_file in sorted(directory.glob("*.md")):
                if md_file.name.startswith("_"):
                    continue
                skill = _parse_skill_md(md_file)
                skills[skill.name] = skill
        return skills

    def catalog(self) -> str:
        # 技能清单文本(list_skills 工具的返回值)
        skills = self.load()
        if not skills:
            return "(当前没有可用技能,可在 skills/ 目录下添加 .md 文件)"
        lines = []
        for skill in skills.values():
            lines.append(f"- {skill.name}: {skill.description}")
        return "可用技能:\n" + "\n".join(lines)


def make_skill_tools(loader: SkillLoader) -> None:
    # 注册两个技能相关的内置工具(供模型在对话中调用)

    def list_skills() -> str:
        """列出当前所有可用技能及其用途说明。"""
        return loader.catalog()

    def load_skill(name: str) -> str:
        """加载指定技能的完整指令内容,加载后请按照技能中的说明完成任务。

        Args:
            name: 技能名称,可先用 list_skills 查询
        """
        skills = loader.load()
        skill = skills.get(name)
        if skill is None:
            return f"未找到技能 '{name}'。{loader.catalog()}"
        return f"# 技能: {skill.name}\n\n{skill.content}"

    register_tool(list_skills, name="list_skills")
    register_tool(load_skill, name="load_skill")
