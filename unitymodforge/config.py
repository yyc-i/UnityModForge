"""配置读写：API 地址/Key/模型、输出目录、BepInEx 平台等，持久化到用户目录 JSON。"""
import json
import os
from dataclasses import dataclass, asdict

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".unitymodforge")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
CACHE_DIR = os.path.join(CONFIG_DIR, "cache")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "UnityModForgeOutput")

# 常见 OpenAI 兼容 API 预设（base_url 都兼容 /chat/completions）
# free=True 表示模型调用免费；need_key=False 表示无需 API Key（本地模型）
API_PRESETS = {
    "本地免费 · Ollama（免注册免Key）": {
        "base": "http://127.0.0.1:11434/v1", "model": "qwen2.5-coder:7b",
        "free": True, "need_key": False,
    },
    "免费 · 智谱 GLM-4.7-Flash": {
        "base": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4.7-flash",
        "free": True, "need_key": True,
    },
    "免费 · 硅基流动 Qwen2.5-7B": {
        "base": "https://api.siliconflow.cn/v1", "model": "Qwen/Qwen2.5-7B-Instruct",
        "free": True, "need_key": True,
    },
    "免费 · OpenRouter :free 模型": {
        "base": "https://openrouter.ai/api/v1", "model": "meta-llama/llama-3.3-70b-instruct:free",
        "free": True, "need_key": True,
    },
    "免费 · Groq Llama3.3-70B": {
        "base": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile",
        "free": True, "need_key": True,
    },
    "DeepSeek": {"base": "https://api.deepseek.com/v1", "model": "deepseek-chat",
                 "free": False, "need_key": True},
    "Moonshot Kimi": {"base": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k",
                      "free": False, "need_key": True},
    "OpenAI": {"base": "https://api.openai.com/v1", "model": "gpt-4o-mini",
               "free": False, "need_key": True},
    "智谱 GLM（付费）": {"base": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-plus",
                        "free": False, "need_key": True},
    "通义千问": {"base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus",
                "free": False, "need_key": True},
}

# 本地 Ollama 默认地址（OpenAI 兼容端点）与推荐代码模型
OLLAMA_BASE = "http://127.0.0.1:11434/v1"
OLLAMA_DEFAULT_MODEL = "qwen2.5-coder:7b"

BEPINEX_PLATFORMS = ["x64", "x86", "unix"]


@dataclass
class AppConfig:
    api_base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    model: str = "deepseek-chat"
    output_dir: str = DEFAULT_OUTPUT_DIR
    bepinex_platform: str = "x64"          # x64 / x86 / unix
    bepinex_auto_download: bool = True     # True=自动下载 BepInEx；False=用本地 zip
    bepinex_zip_path: str = ""             # 本地 BepInEx 安装包路径（自动下载关闭时必填）


def load_config() -> AppConfig:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid = {k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__}
        return AppConfig(**valid)
    except Exception:
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
