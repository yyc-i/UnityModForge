"""OpenAI 兼容大模型客户端：调用 /chat/completions，解析返回的代码。"""
import json
import re
from typing import Callable, List, Optional

import requests

from .config import AppConfig


class LLMError(Exception):
    """LLM 调用失败。"""


def _is_local_endpoint(base_url: str) -> bool:
    """本地服务（Ollama 等）不需要 API Key。"""
    low = base_url.lower()
    return "127.0.0.1" in low or "localhost" in low


def call_chat_completion(cfg: AppConfig, messages: List[dict],
                         temperature: float = 0.3, timeout: int = 240,
                         on_log: Optional[Callable[[str], None]] = None) -> str:
    """向 OpenAI 兼容端点发聊天请求，返回模型文本内容。"""
    if not cfg.api_key.strip() and not _is_local_endpoint(cfg.api_base_url):
        raise LLMError("未填写 API Key（在“设置”页选择免费模型预设并注册获取；本地 Ollama 可留空）")
    url = cfg.api_base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {"Content-Type": "application/json"}
    if cfg.api_key.strip():
        headers["Authorization"] = "Bearer " + cfg.api_key.strip()
    if on_log:
        on_log(f"正在请求 API：{cfg.api_base_url}  模型：{cfg.model}")
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise LLMError(f"无法连接 API（{e}）")
    if resp.status_code != 200:
        detail = resp.text[:500]
        raise LLMError(f"API 返回错误 {resp.status_code}：{detail}")
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise LLMError(f"API 响应格式异常（{e}）")


def detect_ollama_models(base_url: str = "http://127.0.0.1:11434/v1",
                         timeout: int = 4) -> List[str]:
    """探测本地 Ollama 服务并返回已安装的模型 ID 列表；未安装/未启动返回空列表。"""
    try:
        resp = requests.get(base_url.rstrip("/") + "/models", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
    except requests.exceptions.RequestException:
        pass
    return []


def extract_csharp_blocks(text: str) -> List[str]:
    """从模型输出中提取所有 ```csharp/``` 代码块。"""
    blocks = re.findall(r"```(?:csharp|cs)?\s*\n(.*?)```", text, re.S)
    return [b.strip() for b in blocks if b.strip()]


def extract_xml_block(text: str) -> str:
    """从模型输出中提取 ```xml 代码块（csproj）。"""
    blocks = re.findall(r"```xml\s*\n(.*?)```", text, re.S)
    return blocks[0].strip() if blocks else ""
