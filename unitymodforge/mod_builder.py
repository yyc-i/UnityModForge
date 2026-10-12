"""Mod 工程脚手架、BepInEx 运行时获取、dotnet 编译与安装说明生成。"""
import os
import re
import shutil
import subprocess
import urllib.request
import zipfile
from typing import Callable, Optional, Tuple

from .config import AppConfig, CACHE_DIR
from .game_scanner import GameInfo, find_unityengine_dll

BEPINEX_URLS = {
    "x64": "https://github.com/BepInEx/BepInEx/releases/download/v5.4.22/BepInEx_x64_5.4.22.0.zip",
    "x86": "https://github.com/BepInEx/BepInEx/releases/download/v5.4.22/BepInEx_x86_5.4.22.0.zip",
    "unix": "https://github.com/BepInEx/BepInEx/releases/download/v5.4.22/BepInEx_unix_5.4.22.0.zip",
}

DEFAULT_CSPROJ_TEMPLATE = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net461</TargetFramework>
    <LangVersion>7.3</LangVersion>
    <AssemblyName>{assembly_name}</AssemblyName>
    <RootNamespace>{namespace}</RootNamespace>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
    <NoWarn>CS0618;CS0649</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NETFramework.ReferenceAssemblies" Version="1.0.3" PrivateAssets="all" />
  </ItemGroup>
  <ItemGroup>
    <Reference Include="BepInEx">
      <HintPath>lib\\BepInEx.dll</HintPath>
      <Private>false</Private>
    </Reference>{unityengine_ref}
  </ItemGroup>
</Project>
"""

# 编译用 UnityEngine 桩工程/源码：仅在游戏/DummyDll 里找不到任何 UnityEngine 程序集时，
# 自动生成一个同名桩供编译期引用（BepInEx 的 BaseUnityPlugin 继承 MonoBehaviour，
# 编译时必须能解析该类型）；运行时由游戏真实的 UnityEngine 程序集提供实现。
STUB_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net461</TargetFramework>
    <LangVersion>7.3</LangVersion>
    <AssemblyName>UnityEngine</AssemblyName>
    <RootNamespace>UnityEngine</RootNamespace>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
    <NoWarn>CS0067;CS0649;CS0414</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NETFramework.ReferenceAssemblies" Version="1.0.3" PrivateAssets="all" />
  </ItemGroup>
</Project>
"""

STUB_SOURCE = """// 编译用 UnityEngine 桩（仅用于让依赖 MonoBehaviour 的 BepInEx 插件可编译；
// 运行时由游戏真实的 UnityEngine 程序集提供实现，桩本身不参与运行）。
namespace UnityEngine
{
    public class Object { }
    public class Component : Object { }
    public class Behaviour : Component { }
    public class MonoBehaviour : Behaviour { }
    public class GameObject : Object { }
    public class Transform : Component { }
    public struct Vector2 { public float x; public float y; }
    public struct Vector3 { public float x; public float y; public float z; }
    public struct Quaternion { public float x; public float y; public float z; public float w; }
    public struct Color { public float r; public float g; public float b; public float a; }
    public enum KeyCode
    {
        None = 0, Escape = 27, Return = 13, Space = 32, LeftShift = 304, RightShift = 303,
        LeftControl = 306, RightControl = 305, LeftAlt = 308, RightAlt = 307,
        UpArrow = 273, DownArrow = 274, LeftArrow = 276, RightArrow = 275,
        A = 97, B = 98, C = 99, D = 100, E = 101, F = 102, G = 103, H = 104, I = 105,
        J = 106, K = 107, L = 108, M = 109, N = 110, O = 111, P = 112, Q = 113, R = 114,
        S = 115, T = 116, U = 117, V = 118, W = 119, X = 120, Y = 121, Z = 122,
        F1 = 282, F2 = 283, F3 = 284, F4 = 285, F5 = 286, F6 = 287, F7 = 288,
        F8 = 289, F9 = 290, F10 = 291, F11 = 292, F12 = 293
    }
    public static class Debug
    {
        public static void Log(object message) { }
        public static void LogWarning(object message) { }
        public static void LogError(object message) { }
    }
    public static class Time
    {
        public static float deltaTime => 0f;
        public static float time => 0f;
    }
    public static class Input
    {
        public static bool GetKeyDown(KeyCode key) => false;
        public static bool GetKey(KeyCode key) => false;
    }
}
"""


def sanitize_namespace(game_name: str) -> str:
    """把游戏名转成合法 C# 命名空间/程序集名。"""
    ns = re.sub(r"[^A-Za-z0-9_]", "", game_name)
    if not ns or ns[0].isdigit():
        ns = "Game" + ns
    return ns


def _log(on_log: Optional[Callable[[str], None]], msg: str) -> None:
    if on_log:
        on_log(msg)


def ensure_bepinex_dll(cfg: AppConfig, info: Optional[GameInfo],
                       on_log: Optional[Callable[[str], None]] = None) -> str:
    """拿到一个可编译引用的 BepInEx.dll 路径。

    优先级：游戏自带 BepInEx/core/BepInEx.dll > 本地 zip > 自动下载。
    """
    if info and info.bepinex_dll and os.path.isfile(info.bepinex_dll):
        _log(on_log, f"使用游戏目录里的 BepInEx.dll：{info.bepinex_dll}")
        return info.bepinex_dll

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_dll = os.path.join(CACHE_DIR, "BepInEx.dll")
    if os.path.isfile(cache_dll):
        _log(on_log, f"使用缓存 BepInEx.dll：{cache_dll}")
        return cache_dll

    if cfg.bepinex_zip_path and os.path.isfile(cfg.bepinex_zip_path):
        _log(on_log, f"从本地安装包解压 BepInEx.dll：{cfg.bepinex_zip_path}")
        _extract_bepinex_dll(cfg.bepinex_zip_path, cache_dll)
        return cache_dll

    if cfg.bepinex_auto_download:
        url = BEPINEX_URLS.get(cfg.bepinex_platform, BEPINEX_URLS["x64"])
        _log(on_log, f"自动下载 BepInEx 5.4.22（{cfg.bepinex_platform}）：{url}")
        zip_path = os.path.join(CACHE_DIR, f"BepInEx_{cfg.bepinex_platform}_5.4.22.0.zip")
        _download(url, zip_path, on_log)
        _extract_bepinex_dll(zip_path, cache_dll)
        return cache_dll

    raise RuntimeError("未找到 BepInEx.dll：请在“设置”页提供本地 BepInEx 安装包路径，或开启自动下载。")


def _download(url: str, dest: str, on_log: Optional[Callable[[str], None]]) -> None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UnityModForge/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:
        raise RuntimeError(f"下载 BepInEx 失败（{e}）。网络不通时可手动下载并填到“设置→本地 BepInEx 安装包”。")


def _extract_bepinex_dll(zip_path: str, out_dll: str) -> None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            target = next(n for n in zf.namelist() if n.endswith("BepInEx/core/BepInEx.dll")
                          or n.endswith("core/BepInEx.dll"))
            with zf.open(target) as src, open(out_dll, "wb") as dst:
                shutil.copyfileobj(src, dst)
    except Exception as e:
        raise RuntimeError(f"解压 BepInEx.dll 失败：{e}")


def scaffold_project(out_dir: str, info: GameInfo, plugin_code: str,
                     csproj_content: str = "",
                     on_log: Optional[Callable[[str], None]] = None) -> str:
    """生成可编译的 BepInEx 插件工程目录，返回项目目录路径。"""
    os.makedirs(out_dir, exist_ok=True)
    ns = sanitize_namespace(info.game_name)
    assembly_name = ns + "Mod"

    lib_dir = os.path.join(out_dir, "lib")
    os.makedirs(lib_dir, exist_ok=True)

    bepinex_dll = info.bepinex_dll if (info.bepinex_dll and os.path.isfile(info.bepinex_dll)) \
        else os.path.join(CACHE_DIR, "BepInEx.dll")
    if not os.path.isfile(bepinex_dll):
        raise RuntimeError("缺少 BepInEx.dll，请先运行“准备编译环境”或检查设置。")
    shutil.copy2(bepinex_dll, os.path.join(lib_dir, "BepInEx.dll"))

    unityengine_src = find_unityengine_dll(info)
    unityengine_ref = ""
    if unityengine_src:
        shutil.copy2(unityengine_src, os.path.join(lib_dir, "UnityEngine.dll"))
        unityengine_ref = _unityengine_ref("UnityEngine.dll")
        _log(on_log, f"使用游戏提供的 UnityEngine 程序集：{unityengine_src}")
    else:
        _log(on_log, "游戏目录里没有 UnityEngine.dll/CoreModule.dll，将自动生成编译桩（运行时由游戏真实引擎提供）。")
        _build_stub_unityengine(lib_dir, on_log)
        unityengine_ref = _unityengine_ref("UnityEngine.dll")

    csproj = csproj_content if csproj_content.strip() else DEFAULT_CSPROJ_TEMPLATE
    csproj = csproj.replace("{namespace}", ns).replace("{assembly_name}", assembly_name)
    csproj = csproj.replace("{unityengine_ref}", unityengine_ref)

    with open(os.path.join(out_dir, "Plugin.cs"), "w", encoding="utf-8") as f:
        f.write(plugin_code)
    with open(os.path.join(out_dir, assembly_name + ".csproj"), "w", encoding="utf-8") as f:
        f.write(csproj)
    return out_dir


def _unityengine_ref(dll_name: str) -> str:
    return ('\n    <Reference Include="UnityEngine">\n'
            f'      <HintPath>lib\\\\{dll_name}</HintPath>\n'
            '      <Private>false</Private>\n'
            '    </Reference>')


def _build_stub_unityengine(lib_dir: str,
                            on_log: Optional[Callable[[str], None]]) -> None:
    """生成并编译一个最小 UnityEngine 桩程序集到 lib/，供编译期引用。

    桩工程放在全局缓存目录（不在插件工程内部），避免被插件工程的
    SDK 默认编译通配符（**/*.cs）误收录造成类型冲突。
    """
    dotnet = shutil.which("dotnet")
    if not dotnet:
        raise RuntimeError("缺少 UnityEngine.dll 且未找到 dotnet，无法自动生成编译桩。"
                           "请把游戏 Managed 目录里的 UnityEngine.dll（或 UnityEngine.CoreModule.dll）"
                           "手动复制到工程的 lib/ 目录后重试。")
    stub_dir = os.path.join(CACHE_DIR, "stubs", "UnityEngine")
    os.makedirs(stub_dir, exist_ok=True)
    with open(os.path.join(stub_dir, "UnityEngine.csproj"), "w", encoding="utf-8") as f:
        f.write(STUB_CSPROJ)
    with open(os.path.join(stub_dir, "UnityEngine.Stub.cs"), "w", encoding="utf-8") as f:
        f.write(STUB_SOURCE)
    _log(on_log, "正在编译 UnityEngine 编译桩…")
    proc = subprocess.run(
        [dotnet, "build", stub_dir, "-c", "Release", "-v", "q", "-nologo"],
        capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError("生成 UnityEngine 编译桩失败：\n" + (proc.stdout or "")[-600:])
    src = os.path.join(stub_dir, "bin", "Release", "UnityEngine.dll")
    if not os.path.isfile(src):
        raise RuntimeError("编译桩构建完成但未找到输出 UnityEngine.dll")
    shutil.copy2(src, os.path.join(lib_dir, "UnityEngine.dll"))
    _log(on_log, "✅ 已生成 UnityEngine 编译桩（仅编译期使用，运行时由游戏真实引擎提供）。")


def build_mod(project_dir: str, on_log: Optional[Callable[[str], None]] = None) -> Tuple[bool, str, str]:
    """dotnet build -c Release，返回 (是否成功, dll路径, 完整日志)。"""
    dotnet = shutil.which("dotnet")
    if not dotnet:
        return False, "", "未找到 dotnet 命令。请先安装 .NET SDK 8（https://dotnet.microsoft.com/），并确保 dotnet 在 PATH 中。"
    _log(on_log, "开始编译（首次会还原 NuGet 包，可能需要一两分钟）...")
    proc = subprocess.run(
        [dotnet, "build", project_dir, "-c", "Release", "-v", "m", "-nologo"],
        capture_output=True, text=True, timeout=600)
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        tail = "\n".join((log or "").splitlines()[-40:])
        return False, "", f"编译失败（exit {proc.returncode}）：\n{tail}"

    # 找生成的 dll（优先 bin 输出，obj 里的中间产物是同一份但路径不规范）
    dll_path = ""
    candidates = []
    for root, _, files in os.walk(os.path.join(project_dir, "bin")):
        for name in files:
            if name.endswith(".dll") and "BepInEx" not in name and "UnityEngine" not in name and "netstandard" not in name and "Microsoft" not in name:
                candidates.append(os.path.join(root, name))
        if candidates:
            break
    if candidates:
        dll_path = candidates[0]
    return True, dll_path, log


def install_instructions(info: GameInfo, dll_name: str) -> str:
    """生成给玩家的安装说明文本。"""
    game = info.game_name
    if info.bepinex_dir:
        dest = os.path.join(info.bepinex_dir, "plugins")
        lines = [
            f"1. 已检测到游戏目录里有 BepInEx，把 {dll_name} 复制到：",
            f"   {dest}",
            "2. 启动游戏，控制台/日志出现你的 Mod 名字即安装成功。",
        ]
    else:
        lines = [
            "游戏目录里还没有 BepInEx，请先安装：",
            f"1. 把 BepInEx 5.4.22（x64）解压到游戏根目录 {info.game_dir}（即 BepInEx 文件夹与游戏 exe 同级）。",
            "2. 先运行一次游戏再退出，让 BepInEx 生成必要文件夹。",
            f"3. 把编译出的 {dll_name} 复制到 {os.path.join(info.game_dir, 'BepInEx', 'plugins')} 目录。",
            "4. 再次启动游戏。",
        ]
    return "\n".join(lines)


def _resolve_bepinex_zip(cfg: AppConfig) -> str:
    """找一个可用的 BepInEx 安装包 zip：优先用户指定，其次缓存里各平台的包。"""
    if cfg.bepinex_zip_path and os.path.isfile(cfg.bepinex_zip_path):
        return cfg.bepinex_zip_path
    for plat in BEPINEX_URLS:
        p = os.path.join(CACHE_DIR, f"BepInEx_{plat}_5.4.22.0.zip")
        if os.path.isfile(p):
            return p
    return ""


def _safe_extract_zip(zip_path: str, target_dir: str) -> None:
    """安全解压：拒绝 zip-slip（路径穿越）成员。"""
    with zipfile.ZipFile(zip_path) as zf:
        for m in zf.infolist():
            name = m.filename.replace("\\", "/")
            parts = name.split("/")
            if name.startswith("/") or ".." in parts:
                raise RuntimeError(f"安装包包含不安全路径，已中止：{name}")
        zf.extractall(target_dir)


def install_mod(cfg: AppConfig, info: GameInfo, dll_path: str,
                on_log: Optional[Callable[[str], None]] = None) -> str:
    """把编译出的 Mod DLL 一键安装到游戏的 BepInEx/plugins/<Mod名>/ 目录。

    游戏目录里还没有 BepInEx 时，先用缓存/本地的 BepInEx 安装包自动装好。
    返回安装后的 DLL 完整路径。
    """
    if not dll_path or not os.path.isfile(dll_path):
        raise RuntimeError(f"找不到要安装的 DLL：{dll_path}")
    mod_file = os.path.basename(dll_path)
    mod_dir_name = os.path.splitext(mod_file)[0]

    bepinex_root = info.bepinex_dir
    if not bepinex_root or not os.path.isdir(bepinex_root):
        _log(on_log, "游戏目录里还没有 BepInEx，正在自动安装 BepInEx…")
        zip_path = _resolve_bepinex_zip(cfg)
        if not zip_path:
            raise RuntimeError("无法自动安装 BepInEx：缓存/本地都没有安装包。"
                               "请先在“设置”页提供 BepInEx 安装包，或开启自动下载后点一次“准备编译环境”。")
        _safe_extract_zip(zip_path, info.game_dir)
        bepinex_root = os.path.join(info.game_dir, "BepInEx")
        if not os.path.isdir(bepinex_root):
            raise RuntimeError("BepInEx 解压后未找到 BepInEx 目录，请检查安装包是否匹配平台。")
        info.bepinex_dir = bepinex_root
        info.bepinex_dll = os.path.join(bepinex_root, "core", "BepInEx.dll")
        _log(on_log, f"✅ 已自动安装 BepInEx 到：{info.game_dir}\n"
                     f"   注意：请先运行一次游戏再退出（让 BepInEx 生成必要文件），然后再次启动即可加载 Mod。")

    plugins_dir = os.path.join(bepinex_root, "plugins", mod_dir_name)
    os.makedirs(plugins_dir, exist_ok=True)
    dest = os.path.join(plugins_dir, mod_file)
    existed = os.path.exists(dest)
    shutil.copy2(dll_path, dest)
    if existed:
        _log(on_log, f"ℹ 已覆盖旧版本：{dest}")
    _log(on_log, f"✅ Mod 已一键安装到游戏：{dest}")
    return dest
