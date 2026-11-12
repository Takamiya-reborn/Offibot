# Excel (.xlsx) 工具

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook

from offibot.tools.base import resolve_existing, resolve_output, tool


@tool
def xlsx_list_sheets(path: str) -> str:
    """列出 Excel 工作簿中的所有工作表名称。

    Args:
        path: 工作簿路径
    """
    wb = load_workbook(resolve_existing(path), read_only=True)
    return "工作表: " + ", ".join(wb.sheetnames)


@tool
def xlsx_read(path: str, sheet: str = "", max_rows: int = 50) -> str:
    """读取 Excel 工作表内容,以表格形式返回(单元格间用 | 分隔)。

    Args:
        path: 工作簿路径
        sheet: 工作表名,留空则读第一个
        max_rows: 最多读取的行数
    """
    wb = load_workbook(resolve_existing(path), read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    lines: list[str] = [f"[{ws.title}] 共 {ws.max_row} 行 x {ws.max_column} 列(最多显示 {max_rows} 行)"]
    for row in ws.iter_rows(max_row=max_rows, values_only=True):
        lines.append(" | ".join("" if v is None else str(v) for v in row))
    return "\n".join(lines)


@tool
def xlsx_write(path: str, data: list[list], sheet: str = "Sheet1") -> str:
    """把二维数组写入 Excel 工作簿(第一行为表头)。

    文件不存在则创建;已存在则保留其他工作表,只覆盖指定 sheet 的内容。

    Args:
        path: 输出工作簿路径
        data: 二维数组,例如 [["姓名", "分数"], ["张三", 90]]
        sheet: 工作表名
    """
    path = resolve_output(path)
    existing = Path(path)
    if existing.is_file():
        # 已有文件:保留其他 sheet,仅覆盖目标 sheet
        wb = load_workbook(path)
        if sheet in wb.sheetnames:
            ws = wb[sheet]
            ws.delete_rows(1, ws.max_row)
        else:
            ws = wb.create_sheet(sheet)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = sheet
    for row in data:
        ws.append(row)
    wb.save(path)
    return f"已写入 {len(data)} 行到 {Path(path).resolve()}"
