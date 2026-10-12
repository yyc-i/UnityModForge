@echo off
chcp 65001 >nul
title UnityModForge 一键打包 EXE
echo ================================================
echo   UnityModForge - Windows EXE 一键打包
echo   （需要已安装 Python 3.9+，并勾选 Add to PATH）
echo ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python。
    echo 请先到 https://www.python.org/downloads/ 安装 Python 3.9+，
    echo 安装时务必勾选 "Add Python to PATH"，装完重开本窗口再运行。
    pause
    exit /b 1
)

echo [1/4] 安装依赖（首次较慢，请耐心等待）...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
)

echo [2/4] 校验源码...
python -c "import sys; sys.path.insert(0, '.'); import app; print('源码 OK')"
if errorlevel 1 (
    echo [错误] 源码校验失败，请把报错发回。
    pause
    exit /b 1
)

echo [3/4] 打包 EXE（约 1-3 分钟）...
python -m PyInstaller --noconfirm --clean UnityModForge.spec
if errorlevel 1 (
    echo [错误] 打包失败，请把上方红色报错信息发回。
    pause
    exit /b 1
)

echo.
echo ================================================
echo   打包完成！
echo   程序位置：dist\UnityModForge.exe
echo.
echo   使用方式：
echo   - 双击即可运行，无需安装，绿色单文件
echo   - 想复制到别的电脑/发给别人，直接复制这一个 exe 即可
echo   - 第一次运行时 Windows 可能提示"未知发布者"，点"仍要运行"
echo ================================================
pause
