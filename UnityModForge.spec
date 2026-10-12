# -*- mode: python ; coding: utf-8 -*-
# UnityModForge 的 PyInstaller 打包配置。
# Windows 上通过 build_windows.bat 调用；本机验证时也可直接 `pyinstaller UnityModForge.spec`。
import sys

icon_arg = "assets/icon.ico" if sys.platform.startswith("win") else None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "unitymodforge.config",
        "unitymodforge.game_scanner",
        "unitymodforge.llm_client",
        "unitymodforge.mod_builder",
        "unitymodforge.prompts",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PIL", "numpy", "pandas", "matplotlib", "scipy", "PyQt5", "PySide6"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="UnityModForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI 程序：不弹出黑色控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
