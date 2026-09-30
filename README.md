# Offibot

命令行 Office AI 助手:通过自然语言创建和编辑 Word / Excel / PowerPoint 文件。无前端,打包后是一个独立的 `offibot.exe`。

## 普通用户使用方法(非开发者)

只需两个东西:`offibot.exe` 和一个 API Key。

### 1. 首次配置

在 exe 所在目录新建一个名为 `.env` 的文本文件,内容:

```ini
OPENAI_API_KEY=sk-你的密钥
```

> 也可以不建文件,改为在系统环境变量中设置 `OPENAI_API_KEY`(设置 → 系统 → 高级系统设置 → 环境变量),一次配置永久生效。

可选配置项:

```ini
OPENAI_BASE_URL=https://api代理地址/v1   # 使用兼容接口/代理时填写
OFFIBOT_MODEL=gpt-4o-mini                # 默认模型
OFFIBOT_MAX_TURNS=20                     # 单次任务最大工具调用轮数
```

### 2. 运行

打开「命令提示符」或「PowerShell」,cd 到 exe 所在目录:

```bat
.\offibot.exe                          :: 进入交互式对话(推荐)
.\offibot.exe run "创建一个记录团队分工的 Excel 表"
.\offibot.exe skills                   :: 查看可用技能
.\offibot.exe tools                    :: 查看支持的文件操作
```

交互模式中可以连续对话,输入 `/reset` 清空上下文,`/skills` 查看技能,`/exit` 或 `Ctrl+C` 退出。

生成的文件按类型自动归档到当前目录下的三个文件夹:`./docx`(Word)、`./xlsx`(Excel)、`./pptx`(PowerPoint),文件夹会自动创建;也可以直接告诉 AI 保存到其他位置。

### 3. 自定义技能(可选)

在 exe 所在目录新建 `skills` 文件夹,放入 `.md` 技能文件即可被自动识别,无需重新下载程序。

## 开发者指南

### 结构

```
src/offibot/
├── cli.py                # 命令行入口(chat / run / skills / tools 子命令)
├── core/                 # AI 部分
│   ├── config.py         # 配置(.env、模型、轮数)
│   ├── agent.py          # Agent 主循环(OpenAI function calling)
│   └── skill.py          # 技能加载器(skills/*.md 的调用接口)
├── tools/                # Office 工具
│   ├── base.py           # @tool 装饰器 + 注册表(自动生成 JSON Schema)
│   ├── docx_tools.py     # Word 工具
│   ├── xlsx_tools.py     # Excel 工具
│   └── pptx_tools.py     # PowerPoint 工具
└── assets/
    └── skills/           # 内置技能 markdown(随包打包)
```

技能搜索顺序:包内 `assets/skills/` → 当前目录 `./skills/` → `--skills-dir` 指定的目录。

### 快速开始

```bash
uv sync
cp .env.example .env   # 填入 OPENAI_API_KEY

uv run offibot chat
uv run offibot run "创建一个记录团队分工的 Excel 表"
```

### 添加工具

在 `src/offibot/tools/` 新建模块,用 `@tool` 装饰函数,然后在 `tools/__init__.py` 中 import 该模块即可。参数类型注解和 docstring 会自动生成 OpenAI function calling 的 JSON Schema:

```python
from offibot.tools.base import tool

@tool
def my_tool(path: str, limit: int = 10) -> str:
    """工具描述(模型据此决定何时调用)。

    Args:
        path: 参数说明
        limit: 参数说明
    """
    ...
    return "结果文本"
```

### 添加技能

在 `src/offibot/assets/skills/`(随程序打包)或项目根目录 `skills/`(仅本机)下写 `.md` 文件:

```markdown
---
name: my-skill
description: 技能用途一句话(模型靠它决定何时加载)
---

技能正文:具体的工作流程、格式要求、注意事项……
```

模型会通过内置的 `list_skills` / `load_skill` 工具按需加载技能内容。

### 打包为 offibot.exe

```powershell
.\build.ps1
```

脚本内部执行 `uv run python -m PyInstaller package.spec --noconfirm`,产物为 `dist/offibot.exe`。打包配置在 [package.spec](package.spec) 中维护:通过 `collect_data_files("offibot")` 把 `assets/skills/` 下的技能一起打进 exe。若后续新增了依赖(Python 包),PyInstaller 一般能自动发现,遇到隐藏导入问题时在 spec 的 `hiddenimports` 中补充。
