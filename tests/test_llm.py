"""LLM 客户端测试：本地 mock API 验证调用、代码块提取、错误处理。"""
import http.server
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unitymodforge.config import AppConfig
from unitymodforge.llm_client import (LLMError, call_chat_completion,
                                      detect_ollama_models,
                                      extract_csharp_blocks, extract_xml_block)

FAKE_REPLY = (
    "# 方案：示例\n"
    "```csharp\npublic class HelloMod { public void Run() { } }\n```\n"
    "```xml\n<Project Sdk=\"Microsoft.NET.Sdk\"></Project>\n```\n"
    "```text\n安装说明：复制到 BepInEx/plugins\n```\n"
)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        self.rfile.read(length)
        data = json.dumps({"choices": [{"message": {"content": FAKE_REPLY}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def _start_mock():
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def test_call_and_extract():
    server, port = _start_mock()
    cfg = AppConfig(api_base_url=f"http://127.0.0.1:{port}/v1", api_key="test-key")
    text = call_chat_completion(cfg, [{"role": "user", "content": "你好"}])
    assert "HelloMod" in text
    blocks = extract_csharp_blocks(text)
    assert len(blocks) == 1 and "HelloMod" in blocks[0]
    xml = extract_xml_block(text)
    assert "<Project" in xml
    server.shutdown()


def test_local_endpoint_no_key_needed():
    # 本地端点（Ollama 模式）允许空 Key 直接调用
    server, port = _start_mock()
    cfg = AppConfig(api_base_url=f"http://127.0.0.1:{port}/v1", api_key="")
    text = call_chat_completion(cfg, [{"role": "user", "content": "你好"}])
    assert "HelloMod" in text
    server.shutdown()


def test_missing_key_raises():
    # 非本地端点 + 空 Key：应提示填写（不发请求）
    try:
        call_chat_completion(AppConfig(api_base_url="https://api.example.com/v1", api_key=""),
                             [{"role": "user", "content": "x"}])
        raise AssertionError("应当报错")
    except LLMError as e:
        assert "API Key" in str(e)


def test_connection_error():
    try:
        call_chat_completion(AppConfig(api_base_url="http://127.0.0.1:1/v1", api_key="k"),
                             [{"role": "user", "content": "x"}], timeout=2)
        raise AssertionError("应当报错")
    except LLMError:
        pass


def test_detect_ollama_offline():
    # Ollama 未运行时探测应返回空列表而不是抛异常
    models = detect_ollama_models("http://127.0.0.1:1/v1", timeout=2)
    assert models == []


if __name__ == "__main__":
    for fn in [test_call_and_extract, test_local_endpoint_no_key_needed,
               test_missing_key_raises, test_connection_error,
               test_detect_ollama_offline]:
        fn()
        print("PASS", fn.__name__)
    print("全部通过")
