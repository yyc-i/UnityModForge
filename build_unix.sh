#!/usr/bin/env bash
# ============================================================
#  UnityModForge - Linux / macOS 一键打包脚本（v1.0.0 新增）
#
#  用法：bash build_unix.sh
#  产物：dist/UnityModForge   （当前系统的可执行文件）
#
#  注意：PyInstaller 不支持跨平台交叉编译 ——
#        在 Linux 上打包得到 Linux 可执行文件，在 macOS 上打包得到 macOS 应用，
#        Windows exe 请用 build_windows.bat（在 Windows 电脑上运行）。
# ============================================================
set -e
cd "$(dirname "$0")"

echo "================================================"
echo "  UnityModForge - $(uname -s) 一键打包"
echo "  （需要已安装 Python 3.9+）"
echo "================================================"
echo

# 1. 检查 python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[错误] 未找到 python3。"
    echo "请先安装 Python 3.9+：https://www.python.org/downloads/"
    echo "（Linux 可用系统包管理器，如 sudo apt install python3 python3-pip）"
    exit 1
fi

# 2. 安装依赖 + PyInstaller
echo "[1/4] 安装依赖（首次较慢，请耐心等待）..."
python3 -m pip install --user -r requirements.txt pyinstaller

# 3. 校验源码
echo "[2/4] 校验源码..."
python3 -c "import sys; sys.path.insert(0, '.'); import app; print('源码 OK')"

# 4. 打包（约 1-3 分钟）
echo "[3/4] 打包可执行文件（约 1-3 分钟）..."
python3 -m PyInstaller --noconfirm --clean UnityModForge.spec

echo
echo "================================================"
echo "  打包完成！"
echo "  程序位置：dist/UnityModForge"
echo
echo "  使用方式："
echo "  - 直接运行：./dist/UnityModForge"
echo "  - 想复制到别的电脑/发给别人，直接复制这一个文件即可（同系统可用）"
echo "  - 需要图形界面（tkinter）正常运行；Linux 服务器无桌面时请用 CLI 模式："
echo "    ./dist/UnityModForge --cli --game <游戏目录> --request \"想改什么\" --install"
echo "================================================"
