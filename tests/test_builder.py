"""Mod 工程脚手架与编译测试：BepInEx.dll 获取、工程生成、无 dotnet 时友好报错。"""
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unitymodforge.config import AppConfig, CACHE_DIR
from unitymodforge.game_scanner import GameInfo
from unitymodforge.mod_builder import (build_mod, ensure_bepinex_dll,
                                       install_mod, scaffold_project,
                                       sanitize_namespace)


def _fake_info(tmp, name="MyGame", with_unityengine=True):
    data = os.path.join(tmp, name + "_Data", "Managed")
    os.makedirs(data, exist_ok=True)
    open(os.path.join(data, "Assembly-CSharp.dll"), "w").close()
    if with_unityengine:
        open(os.path.join(data, "UnityEngine.dll"), "w").close()
    return GameInfo(game_dir=tmp, game_name=name, data_dir=data,
                    is_il2cpp=False, managed_dir=data,
                    assembly_csharp=os.path.join(data, "Assembly-CSharp.dll"))


def test_namespace_sanitize():
    assert sanitize_namespace("My Game 2") == "MyGame2"
    assert sanitize_namespace("123中文!")[0].isdigit() is False


def test_ensure_bepinex_from_local_zip(tmp_path=None):
    tmp = tmp_path or tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "bepinex.zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("BepInEx/core/BepInEx.dll", b"FAKE-BEPINEX-DLL")
    cfg = AppConfig(bepinex_auto_download=False, bepinex_zip_path=zip_path)
    dll = ensure_bepinex_dll(cfg, None)
    assert os.path.isfile(dll) and open(dll, "rb").read() == b"FAKE-BEPINEX-DLL"


def test_scaffold_project():
    tmp = tempfile.mkdtemp()
    cache = os.path.join(CACHE_DIR, "BepInEx.dll")
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.isfile(cache):
        open(cache, "wb").write(b"FAKE")
    info = _fake_info(tmp)
    info.bepinex_dll = cache
    proj = scaffold_project(os.path.join(tmp, "out"), info, "public class A{}")
    assert os.path.isfile(os.path.join(proj, "Plugin.cs"))
    assert os.path.isfile(os.path.join(proj, "MyGameMod.csproj"))
    assert os.path.isfile(os.path.join(proj, "lib", "BepInEx.dll"))
    assert os.path.isfile(os.path.join(proj, "lib", "UnityEngine.dll"))  # 用游戏自带
    csproj = open(os.path.join(proj, "MyGameMod.csproj")).read()
    assert "<AssemblyName>MyGameMod</AssemblyName>" in csproj
    assert "UnityEngine.dll" in csproj


def test_scaffold_without_unityengine_and_dotnet_raises():
    # 游戏没有 UnityEngine.dll 且机器没有 dotnet 时，应给出可读错误而不是崩溃
    tmp = tempfile.mkdtemp()
    cache = os.path.join(CACHE_DIR, "BepInEx.dll")
    info = _fake_info(tmp, with_unityengine=False)
    info.bepinex_dll = cache
    old_path = os.environ.get("PATH", "")
    # 临时剔除 dotnet，模拟"机器没装 .NET SDK"
    os.environ["PATH"] = os.pathsep.join(
        [p for p in old_path.split(os.pathsep) if "dotnet" not in p.lower()])
    try:
        try:
            scaffold_project(os.path.join(tmp, "out"), info, "public class A{}")
            raise AssertionError("应当报错")
        except RuntimeError as e:
            assert "UnityEngine" in str(e) and "dotnet" in str(e)
    finally:
        os.environ["PATH"] = old_path


def test_build_without_dotnet():
    ok, dll, log = build_mod("/tmp/nonexistent")
    assert not ok
    assert "dotnet" in log


def test_install_mod_to_existing_bepinex():
    tmp = tempfile.mkdtemp()
    info = _fake_info(tmp)
    os.makedirs(os.path.join(tmp, "BepInEx", "core"))
    info.bepinex_dir = os.path.join(tmp, "BepInEx")
    info.bepinex_dll = os.path.join(info.bepinex_dir, "core", "BepInEx.dll")
    dll = os.path.join(tmp, "MyGameMod.dll")
    open(dll, "wb").write(b"DLL-CONTENT")
    cfg = AppConfig(bepinex_auto_download=False)
    dest = install_mod(cfg, info, dll)
    expected = os.path.join(tmp, "BepInEx", "plugins", "MyGameMod", "MyGameMod.dll")
    assert dest == expected
    assert os.path.isfile(expected)
    assert open(expected, "rb").read() == b"DLL-CONTENT"


def test_install_mod_auto_installs_bepinex():
    # 游戏目录没有 BepInEx 时，应自动解压安装包并装上 Mod
    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "bepinex.zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("BepInEx/core/BepInEx.dll", b"FAKE-BEPINEX-DLL")
        z.writestr("BepInEx/winhttp.dll", b"FAKE-WINHTTP")
    game = os.path.join(tmp, "Game")
    info = _fake_info(game)          # 无 BepInEx 目录
    dll = os.path.join(tmp, "GameMod.dll")
    open(dll, "wb").write(b"DLL")
    cfg = AppConfig(bepinex_auto_download=False, bepinex_zip_path=zip_path)
    dest = install_mod(cfg, info, dll)
    assert os.path.isfile(os.path.join(game, "BepInEx", "core", "BepInEx.dll"))
    assert os.path.isfile(os.path.join(game, "BepInEx", "winhttp.dll"))
    assert os.path.isfile(os.path.join(game, "BepInEx", "plugins", "GameMod", "GameMod.dll"))
    assert dest.endswith("GameMod.dll")


if __name__ == "__main__":
    for fn in [test_namespace_sanitize, test_ensure_bepinex_from_local_zip,
               test_scaffold_project, test_scaffold_without_unityengine_and_dotnet_raises,
               test_build_without_dotnet, test_install_mod_to_existing_bepinex,
               test_install_mod_auto_installs_bepinex]:
        fn()
        print("PASS", fn.__name__)
    print("全部通过")
