"""Unity 游戏扫描：检测游戏类型（Mono/IL2CPP）、定位关键文件、生成供 LLM 参考的 API 索引。"""
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class GameInfo:
    game_dir: str
    game_name: str
    data_dir: str
    is_il2cpp: bool
    managed_dir: str = ""
    assembly_csharp: str = ""          # Mono 主程序集
    global_metadata: str = ""          # IL2CPP 元数据
    game_assembly: str = ""            # IL2CPP 原生程序集
    bepinex_dir: str = ""
    bepinex_dll: str = ""
    dummy_dll_dir: str = ""            # 用户用 Il2CppDumper 生成的 DummyDll 目录
    notes: List[str] = field(default_factory=list)

    @property
    def engine_desc(self) -> str:
        return "IL2CPP（需要 Il2CppDumper 导出 DummyDll）" if self.is_il2cpp else "Mono (.NET)"


def find_unity_game(game_dir: str) -> Optional[GameInfo]:
    """在游戏根目录里寻找 Unity 数据目录，返回 GameInfo；不是 Unity 游戏返回 None。"""
    game_dir = os.path.abspath(game_dir)
    if not os.path.isdir(game_dir):
        return None

    data_dir, game_name = None, os.path.basename(game_dir)
    try:
        entries = os.listdir(game_dir)
    except OSError:
        return None
    for entry in entries:
        full = os.path.join(game_dir, entry)
        if os.path.isdir(full) and entry.endswith("_Data"):
            has_managed = os.path.isdir(os.path.join(full, "Managed"))
            has_il2cpp = os.path.isdir(os.path.join(full, "il2cpp_data"))
            if has_managed or has_il2cpp:
                data_dir, game_name = full, entry[:-5]
                break
    if data_dir is None:
        return None

    is_il2cpp = os.path.isdir(os.path.join(data_dir, "il2cpp_data"))
    info = GameInfo(game_dir=game_dir, game_name=game_name,
                    data_dir=data_dir, is_il2cpp=is_il2cpp)
    if is_il2cpp:
        info.global_metadata = os.path.join(data_dir, "il2cpp_data", "Metadata", "global-metadata.dat")
        for cand in (os.path.join(data_dir, "Native", "GameAssembly.dll"),
                     os.path.join(game_dir, "GameAssembly.dll")):
            if os.path.isfile(cand):
                info.game_assembly = cand
                break
        if not info.game_assembly:
            info.notes.append("未找到 GameAssembly.dll；IL2CPP 游戏需要先用 Il2CppDumper 导出 DummyDll 才能获得可靠的游戏类型信息。")
    else:
        info.managed_dir = os.path.join(data_dir, "Managed")
        info.assembly_csharp = os.path.join(info.managed_dir, "Assembly-CSharp.dll")
        if not os.path.isfile(info.assembly_csharp):
            info.notes.append("未找到 Assembly-CSharp.dll（游戏可能做过混淆或改名，索引可能不完整）。")

    bepinex_dir = os.path.join(game_dir, "BepInEx")
    if os.path.isdir(bepinex_dir):
        info.bepinex_dir = bepinex_dir
        core_dll = os.path.join(bepinex_dir, "core", "BepInEx.dll")
        if os.path.isfile(core_dll):
            info.bepinex_dll = core_dll
    return info


def find_unityengine_dll(info: GameInfo) -> str:
    """在游戏 Managed 或 DummyDll 里找一个可引用的 UnityEngine.dll。"""
    dirs = []
    if info.managed_dir and os.path.isdir(info.managed_dir):
        dirs.append(info.managed_dir)
    if info.dummy_dll_dir and os.path.isdir(info.dummy_dll_dir):
        dirs.append(info.dummy_dll_dir)
    for d in dirs:
        for name in ("UnityEngine.dll", "UnityEngine.CoreModule.dll"):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return ""


def dump_api_index(info: GameInfo, max_chars: int = 8000) -> Tuple[str, str]:
    """生成游戏 API 索引（类型/方法列表），供 LLM 写挂钩代码时参考。

    返回 (索引文本, 使用的工具名)。
    Mono：优先 ilspycmd -l，其次 monodis --typedef。
    IL2CPP：需要用户先提供 DummyDll 目录，否则返回空索引。
    """
    if info.is_il2cpp:
        if not info.dummy_dll_dir or not os.path.isdir(info.dummy_dll_dir):
            return "", "无（IL2CPP 游戏未提供 DummyDll）"
        target = os.path.join(info.dummy_dll_dir, "Assembly-CSharp.dll")
        if not os.path.isfile(target):
            return "", "无（DummyDll 目录里没有 Assembly-CSharp.dll）"
        return _dump_mono_index(target, max_chars)

    if not info.assembly_csharp or not os.path.isfile(info.assembly_csharp):
        return "", "无可用程序集"
    return _dump_mono_index(info.assembly_csharp, max_chars)


def _dump_mono_index(target_dll: str, max_chars: int) -> Tuple[str, str]:
    ilspy = shutil.which("ilspycmd")
    if ilspy:
        try:
            out = subprocess.run([ilspy, "-l", target_dll], capture_output=True,
                                 text=True, timeout=180).stdout
            lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
            index = "\n".join(lines[:800])[:max_chars]
            if index:
                return index, "ilspycmd"
        except Exception:
            pass
    monodis = shutil.which("monodis")
    if monodis:
        try:
            out = subprocess.run([monodis, "--typedef", target_dll], capture_output=True,
                                 text=True, timeout=180).stdout
            if out.strip():
                return out.strip()[:max_chars], "monodis"
        except Exception:
            pass
    return "", "未安装 ilspycmd/monodis（可运行 `dotnet tool install -g ilspycmd` 安装）"
