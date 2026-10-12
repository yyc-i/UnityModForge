"""端到端 CLI 演练：假 Unity 游戏 + mock API + 真实 dotnet 编译，验证全链路。"""
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# mock 回复：直接使用示例插件源码，保证能编译通过
SAMPLE_PLUGIN = open(os.path.join(REPO, "examples", "SampleBepInExPlugin", "Plugin.cs")).read()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        reply = "# 方案：示例\n```csharp\n" + SAMPLE_PLUGIN + "\n```\n"
        data = json.dumps({"choices": [{"message": {"content": reply}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def build_fake_game(root):
    """造一个 Mono Unity 假游戏：Managed + Assembly-CSharp + UnityEngine + BepInEx。"""
    game = os.path.join(root, "FakeGame")
    managed = os.path.join(game, "FakeGame_Data", "Managed")
    os.makedirs(managed)
    open(os.path.join(managed, "Assembly-CSharp.dll"), "w").close()
    shutil.copy2(os.path.join(REPO, "examples", "SampleBepInExPlugin", "lib", "UnityEngine.dll"),
                 os.path.join(managed, "UnityEngine.dll"))
    core = os.path.join(game, "BepInEx", "core")
    os.makedirs(core)
    shutil.copy2(os.path.join(REPO, "examples", "SampleBepInExPlugin", "lib", "BepInEx.dll"),
                 os.path.join(core, "BepInEx.dll"))
    return game


def main():
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    tmp = tempfile.mkdtemp(prefix="umf_e2e_")
    game = build_fake_game(tmp)
    out = os.path.join(tmp, "out")

    env = dict(os.environ)
    dotnet_dir = "/tmp/dotnet8"
    if os.path.isdir(dotnet_dir):
        env["PATH"] = dotnet_dir + os.pathsep + env.get("PATH", "")

    cmd = [
        sys.executable, os.path.join(REPO, "app.py"), "--cli",
        "--game", game,
        "--request", "给游戏加一个按 F9 切换无敌的按键",
        "--api-key", "test-key",
        "--base-url", f"http://127.0.0.1:{port}/v1",
        "--model", "mock-model",
        "--output-dir", out,
        "--install",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    print(proc.stdout[-2000:])
    if proc.stderr:
        print("STDERR:", proc.stderr[-800:], file=sys.stderr)
    assert proc.returncode == 0, f"CLI 退出码 {proc.returncode}"
    dlls = []
    for root, _, files in os.walk(out):
        for n in files:
            if n.endswith(".dll") and "BepInEx" not in n and "UnityEngine" not in n:
                dlls.append(os.path.join(root, n))
    assert dlls, "没有找到编译出的 Mod DLL"
    bin_dlls = [d for d in dlls if os.sep + "bin" + os.sep in d]
    assert bin_dlls, f"未在 bin 输出里找到 DLL：{dlls}"
    print("PASS e2e_cli -> DLL:", bin_dlls[0])
    # 一键安装：应出现在游戏 BepInEx/plugins/<Mod名>/ 下
    installed = os.path.join(game, "BepInEx", "plugins", "FakeGameMod", "FakeGameMod.dll")
    assert os.path.isfile(installed), f"未安装到游戏目录：{installed}"
    print("PASS e2e_cli -> 已一键安装到游戏:", installed)


if __name__ == "__main__":
    main()
