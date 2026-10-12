"""游戏扫描模块测试：Mono / IL2CPP / 非 Unity 目录 / 索引降级。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unitymodforge.game_scanner import dump_api_index, find_unity_game


def make_game(root, name="MyGame", il2cpp=False):
    game = os.path.join(root, name)
    data = os.path.join(game, name + "_Data")
    if il2cpp:
        meta = os.path.join(data, "il2cpp_data", "Metadata")
        native = os.path.join(data, "Native")
        os.makedirs(meta)
        os.makedirs(native)
        open(os.path.join(meta, "global-metadata.dat"), "w").close()
        open(os.path.join(native, "GameAssembly.dll"), "w").close()
    else:
        managed = os.path.join(data, "Managed")
        os.makedirs(managed)
        open(os.path.join(managed, "Assembly-CSharp.dll"), "w").close()
        open(os.path.join(managed, "UnityEngine.dll"), "w").close()
    return game


def test_mono_detection():
    root = tempfile.mkdtemp()
    game = make_game(root, "MyGame")
    info = find_unity_game(game)
    assert info is not None, "应识别 Mono Unity 游戏"
    assert not info.is_il2cpp
    assert info.game_name == "MyGame"
    assert info.assembly_csharp.endswith("Assembly-CSharp.dll")
    assert os.path.basename(info.managed_dir) == "Managed"
    assert "Mono" in info.engine_desc


def test_il2cpp_detection():
    root = tempfile.mkdtemp()
    game = make_game(root, "IL2Game", il2cpp=True)
    info = find_unity_game(game)
    assert info is not None
    assert info.is_il2cpp
    assert info.global_metadata.endswith("global-metadata.dat")
    assert info.game_assembly.endswith("GameAssembly.dll")
    assert "IL2CPP" in info.engine_desc


def test_not_a_game():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "随便一个文件夹"))
    assert find_unity_game(root) is None


def test_index_graceful_degradation():
    root = tempfile.mkdtemp()
    game = make_game(root, "MyGame")
    info = find_unity_game(game)
    idx, tool = dump_api_index(info)
    # 本机没装 ilspycmd/monodis 时应返回空索引 + 可读提示（不崩溃）
    if idx == "":
        assert "未安装" in tool or "无可用" in tool or "ilspycmd" in tool
    else:
        assert tool in ("ilspycmd", "monodis")


def test_il2cpp_without_dummy():
    root = tempfile.mkdtemp()
    game = make_game(root, "IL2Game", il2cpp=True)
    info = find_unity_game(game)
    idx, tool = dump_api_index(info)
    assert idx == ""
    assert "DummyDll" in tool


if __name__ == "__main__":
    for fn in [test_mono_detection, test_il2cpp_detection, test_not_a_game,
               test_index_graceful_degradation, test_il2cpp_without_dummy]:
        fn()
        print("PASS", fn.__name__)
    print("全部通过")
