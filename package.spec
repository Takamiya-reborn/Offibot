# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置:产物为 dist/offibot.exe(单文件)
# 执行:uv run python -m PyInstaller package.spec --noconfirm

from PyInstaller.utils.hooks import collect_data_files

# 把包内 assets/(技能 md)一起打进 exe
datas = collect_data_files("offibot")

a = Analysis(
    ["offibot_entry.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="offibot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
