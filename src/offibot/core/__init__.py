# core 包:AI 核心(配置、Agent 循环、技能加载)
# 导出用 __all__ + __getattr__ 惰性完成,避免 tools.base ↔ core.skill 循环导入

from typing import Any

__all__ = ["Agent", "Settings", "Skill", "SkillLoader", "make_skill_tools"]

_LAZY_IMPORTS = {
    "Agent": "offibot.core.agent",
    "Settings": "offibot.core.config",
    "Skill": "offibot.core.skill",
    "SkillLoader": "offibot.core.skill",
    "make_skill_tools": "offibot.core.skill",
}


def __getattr__(name: str) -> Any:
    module_path = _LAZY_IMPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(module_path), name)
    globals()[name] = value  # 缓存,后续访问不再走 __getattr__
    return value
