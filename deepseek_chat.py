import os
import json
import sys
import re
import base64
import hashlib
import hmac
import threading
import time
import uuid
import math
import logging
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox, Frame, Label, Toplevel
from tkinter import filedialog, font as tkfont
from tkinter import ttk
from openai import OpenAI

APP_NAME = "个人API调用对话系统"
APP_NAME_EN = "Personal API Chat Client"
APP_PUBLISHER = "heibaiao"
APP_VERSION = "αpiv0004-4"          # 内部版本号（只在「关于」页左下角展示）
APP_VERSION_PUBLIC = "V1.0"
GITHUB_URL = "https://github.com/heibaiao/personal-api-chat-client"      # 对外版本号
AI_DISPLAY_NAME = "DeepSeek-V4.1-Flash-1017"
AI_BRAND_MAIN = "DeepSeek"
AI_BRAND_SUB = "V4.1-Flash-1017"

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
LOG_FILE = os.path.join(BASE_DIR, 'debug.log')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
NO_PASSWORD = 'PACC-NO-PASSWORD'   # 关闭启动密码时使用的内部口令

_logger = logging.getLogger('deepseek_chat')
_logger.setLevel(logging.DEBUG)
try:
    _fh = logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a')
    _fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    _logger.addHandler(_fh)
except Exception:
    pass

def log_info(msg):
    try: _logger.info(msg)
    except Exception: pass

def log_err(msg):
    try: _logger.error(msg)
    except Exception: pass

def log_exc(msg):
    try: _logger.exception(msg)
    except Exception: pass

def enable_dpi_awareness():
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2); return
        except Exception: pass
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception: pass
    except Exception: pass

HISTORY_FILE = os.path.join(BASE_DIR, 'chat_history.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.enc')

# ============ 模型注册表（αpiv0002） ============
# 每个模型独立保存 API Key；未配置 Key 的条目在列表中以淡灰色禁用展示。
# thinking=True 表示该模型支持「深度思考」开关（原生推理或提示词级推理）。
MODEL_REGISTRY = [
    {
        "id": "deepseek-flash",
        "name": "DeepSeek-V4.1-Flash-1017",
        "version": "v4.1 · 1017",
        "vendor": "DeepSeek",
        "mark": "®",
        "base_url": "https://api.deepseek.com",
        "api_model": "deepseek-flash",
        "desc": "官方主力模型 · 低延迟 · 默认",
        "thinking": True,
    },
    {
        "id": "deepseek-chat",
        "name": "DeepSeek-V4-Chat",
        "version": "v4.0",
        "vendor": "DeepSeek",
        "mark": "®",
        "base_url": "https://api.deepseek.com",
        "api_model": "deepseek-chat",
        "desc": "通用对话 · 长上下文",
        "thinking": False,
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek-R1-Reasoner",
        "version": "r1",
        "vendor": "DeepSeek",
        "mark": "®",
        "base_url": "https://api.deepseek.com",
        "api_model": "deepseek-reasoner",
        "desc": "原生推理 · 适合数学与代码",
        "thinking": True,
        "thinking_native": True,
    },
    {
        "id": "qwen-max",
        "name": "Qwen-Max",
        "version": "2025-09",
        "vendor": "Alibaba",
        "mark": "®",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_model": "qwen-max",
        "desc": "通义千问旗舰版 · OpenAI 兼容",
        "thinking": True,
    },
    {
        "id": "qwen-turbo",
        "name": "Qwen-Turbo",
        "version": "2025-09",
        "vendor": "Alibaba",
        "mark": "®",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_model": "qwen-turbo",
        "desc": "轻量快速 · 适合日常问答",
        "thinking": False,
    },
    {
        "id": "kimi-k2",
        "name": "Kimi-K2",
        "version": "0711",
        "vendor": "Moonshot",
        "mark": "™",
        "base_url": "https://api.moonshot.cn/v1",
        "api_model": "kimi-k2-0711-preview",
        "desc": "月之暗面 · 长文本",
        "thinking": True,
    },
    {
        "id": "glm-4.6",
        "name": "GLM-4.6",
        "version": "v4.6",
        "vendor": "Zhipu",
        "mark": "™",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_model": "glm-4.6",
        "desc": "智谱 · 中文优化",
        "thinking": True,
    },
    {
        "id": "glm-4-flash",
        "name": "GLM-4-Flash",
        "version": "v4",
        "vendor": "Zhipu",
        "mark": "™",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_model": "glm-4-flash",
        "desc": "免费额度 · 轻量",
        "thinking": False,
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "version": "2024-11",
        "vendor": "OpenAI",
        "mark": "®",
        "base_url": "https://api.openai.com/v1",
        "api_model": "gpt-4o",
        "desc": "多模态旗舰 · OpenAI 官方",
        "thinking": True,
    },
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o-mini",
        "version": "2024-07",
        "vendor": "OpenAI",
        "mark": "®",
        "base_url": "https://api.openai.com/v1",
        "api_model": "gpt-4o-mini",
        "desc": "低成本 · 快速响应",
        "thinking": False,
    },
    {
        "id": "gemini-2.0-flash",
        "name": "Gemini-2.0-Flash",
        "version": "2.0",
        "vendor": "Google",
        "mark": "®",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_model": "gemini-2.0-flash",
        "desc": "Google · OpenAI 兼容端点",
        "thinking": True,
    },
    {
        "id": "doubao-seed-1.6",
        "name": "Doubao-Seed-1.6",
        "version": "1.6",
        "vendor": "ByteDance",
        "mark": "™",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_model": "doubao-seed-1-6-250615",
        "desc": "火山方舟 · 中文场景",
        "thinking": False,
    },
    {
        "id": "grok-4",
        "name": "Grok-4",
        "version": "4",
        "vendor": "xAI",
        "mark": "™",
        "base_url": "https://api.x.ai/v1",
        "api_model": "grok-4",
        "desc": "xAI · 实时信息偏好",
        "thinking": True,
    },
    {
        "id": "mistral-large",
        "name": "Mistral-Large",
        "version": "latest",
        "vendor": "Mistral",
        "mark": "®",
        "base_url": "https://api.mistral.ai/v1",
        "api_model": "mistral-large-latest",
        "desc": "欧洲模型 · 多语言",
        "thinking": False,
    },
    {
        "id": "groq-llama",
        "name": "Llama-3.3-70B",
        "version": "70B",
        "vendor": "Groq",
        "mark": "™",
        "base_url": "https://api.groq.com/openai/v1",
        "api_model": "llama-3.3-70b-versatile",
        "desc": "Groq · 极快推理速度",
        "thinking": False,
    },
    {
        "id": "siliconflow-qwen3",
        "name": "Qwen3-235B",
        "version": "A22B",
        "vendor": "SiliconFlow",
        "mark": "",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_model": "Qwen/Qwen3-235B-A22B",
        "desc": "硅基流动 · 国内直连",
        "thinking": True,
    },
    {
        "id": "minimax-m1",
        "name": "MiniMax-M1",
        "version": "M1",
        "vendor": "MiniMax",
        "mark": "™",
        "base_url": "https://api.minimax.chat/v1",
        "api_model": "MiniMax-M1",
        "desc": "长上下文推理",
        "thinking": True,
    },
    {
        "id": "hunyuan",
        "name": "Hunyuan-TurboS",
        "version": "turboS",
        "vendor": "Tencent",
        "mark": "™",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "api_model": "hunyuan-turbos-latest",
        "desc": "腾讯混元 · 中文优化",
        "thinking": False,
    },
    {
        "id": "spark",
        "name": "Spark-4.0",
        "version": "4.0",
        "vendor": "iFlytek",
        "mark": "",
        "base_url": "https://spark-api-open.xf-yun.com/v1",
        "api_model": "generalv3.5",
        "desc": "讯飞星火 · 中文场景",
        "thinking": False,
    },
    {
        "id": "openrouter-auto",
        "name": "OpenRouter-Auto",
        "version": "auto",
        "vendor": "OpenRouter",
        "mark": "™",
        "base_url": "https://openrouter.ai/api/v1",
        "api_model": "openrouter/auto",
        "desc": "聚合网关 · 自动选路",
        "thinking": False,
    },
    {
        "id": "claude-sonnet-4",
        "name": "Claude-Sonnet-4",
        "version": "4",
        "vendor": "Anthropic",
        "mark": "™",
        "base_url": "https://openrouter.ai/api/v1",
        "api_model": "anthropic/claude-sonnet-4",
        "desc": "OpenRouter 代理 · 长文本推理",
        "thinking": True,
    },
    {
        "id": "ernie-4.5",
        "name": "ERNIE-4.5",
        "version": "turbo",
        "vendor": "Baidu",
        "mark": "™",
        "base_url": "https://qianfan.baidubce.com/v2",
        "api_model": "ernie-4.5-turbo-128k",
        "desc": "文心一言 · 中文长文",
        "thinking": False,
    },
    {
        "id": "yi-large",
        "name": "Yi-Large",
        "version": "large",
        "vendor": "01.AI",
        "mark": "",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "api_model": "yi-large",
        "desc": "零一万物 · 中英双语",
        "thinking": False,
    },
    {
        "id": "baichuan4",
        "name": "Baichuan4",
        "version": "4",
        "vendor": "Baichuan",
        "mark": "™",
        "base_url": "https://api.baichuan-ai.com/v1",
        "api_model": "Baichuan4",
        "desc": "百川智能 · 中文医疗强项",
        "thinking": False,
    },
    {
        "id": "step-2",
        "name": "Step-2",
        "version": "16k",
        "vendor": "StepFun",
        "mark": "",
        "base_url": "https://api.stepfun.com/v1",
        "api_model": "step-2-16k",
        "desc": "阶跃星辰 · 多模态底座",
        "thinking": False,
    },
    {
        "id": "sensechat-5",
        "name": "SenseChat-5",
        "version": "5",
        "vendor": "SenseTime",
        "mark": "",
        "base_url": "https://api.sensenova.cn/compatible-mode/v1",
        "api_model": "SenseChat-5",
        "desc": "商汤日日新 · 中文对话",
        "thinking": False,
    },
    {
        "id": "pplx-sonar-pro",
        "name": "Sonar-Pro",
        "version": "pro",
        "vendor": "Perplexity",
        "mark": "",
        "base_url": "https://api.perplexity.ai",
        "api_model": "sonar-pro",
        "desc": "自带联网检索",
        "thinking": False,
    },
    {
        "id": "cohere-command-r",
        "name": "Command-R+",
        "version": "plus",
        "vendor": "Cohere",
        "mark": "®",
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "api_model": "command-r-plus",
        "desc": "企业检索增强",
        "thinking": False,
    },
    {
        "id": "jamba-large",
        "name": "Jamba-Large",
        "version": "1.7",
        "vendor": "AI21",
        "mark": "™",
        "base_url": "https://api.ai21.com/studio/v1",
        "api_model": "jamba-large-1.7",
        "desc": "混合 SSM · 超长上下文",
        "thinking": False,
    },
    {
        "id": "nvidia-llama",
        "name": "Llama-3.3-Nemotron",
        "version": "70B",
        "vendor": "NVIDIA",
        "mark": "™",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_model": "meta/llama-3.3-70b-instruct",
        "desc": "NIM 托管 · 免费额度",
        "thinking": False,
    },
    {
        "id": "together-qwen",
        "name": "Qwen2.5-72B",
        "version": "72B",
        "vendor": "Together",
        "mark": "",
        "base_url": "https://api.together.xyz/v1",
        "api_model": "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "desc": "Together 托管 · 开源模型池",
        "thinking": False,
    },
    {
        "id": "fireworks-deepseek",
        "name": "DeepSeek-V3",
        "version": "V3",
        "vendor": "Fireworks",
        "mark": "",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_model": "accounts/fireworks/models/deepseek-v3",
        "desc": "Fireworks 托管 · 低延迟",
        "thinking": False,
    },
    {
        "id": "cerebras-llama",
        "name": "Llama-3.3-70B",
        "version": "70B",
        "vendor": "Cerebras",
        "mark": "™",
        "base_url": "https://api.cerebras.ai/v1",
        "api_model": "llama-3.3-70b",
        "desc": "晶圆级芯片 · 极速",
        "thinking": False,
    },
    {
        "id": "deepinfra-llama",
        "name": "Llama-3.3-70B",
        "version": "70B",
        "vendor": "DeepInfra",
        "mark": "™",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "api_model": "meta-llama/Llama-3.3-70B-Instruct",
        "desc": "按量计费 · 开源模型",
        "thinking": False,
    },
    {
        "id": "hf-llama",
        "name": "Llama-3.3-70B",
        "version": "70B",
        "vendor": "HuggingFace",
        "mark": "™",
        "base_url": "https://router.huggingface.co/v1",
        "api_model": "meta-llama/Llama-3.3-70B-Instruct",
        "desc": "HF Router · 社区模型",
        "thinking": False,
    },
    {
        "id": "ollama-local",
        "name": "Ollama-Local",
        "version": "local",
        "vendor": "Ollama",
        "mark": "",
        "base_url": "http://localhost:11434/v1",
        "api_model": "llama3.1",
        "desc": "本机运行 · 免密钥",
        "thinking": False,
    },
    {
        "id": "lmstudio-local",
        "name": "LMStudio-Local",
        "version": "local",
        "vendor": "LM Studio",
        "mark": "",
        "base_url": "http://localhost:1234/v1",
        "api_model": "local-model",
        "desc": "本机运行 · 免密钥",
        "thinking": False,
    },
]
MODELS_BY_ID = {m["id"]: m for m in MODEL_REGISTRY}
DEFAULT_MODEL_ID = "deepseek-flash"

MODEL = MODELS_BY_ID[DEFAULT_MODEL_ID]["api_model"]
BASE_URL = MODELS_BY_ID[DEFAULT_MODEL_ID]["base_url"]
TITLE_MODEL = MODEL


def model_title(cfg):
    """模型对外展示名 = 自定义模型名 + 商标（如有）。"""
    return f"{cfg['name']}{cfg.get('mark', '')}"


# 参考计费快照（每 100 万 tokens 的输入/输出价格，货币单位随模型；官方调价后需手动更新）
# 支持图片输入的模型（多模态）
# 复核结果：仅这些模型的原生接口支持图片输入
VISION_MODELS = {
    "gpt-4o": "OpenAI 多模态",
    "gpt-4o-mini": "OpenAI 多模态",
    "gemini-2.0-flash": "Google 多模态",
    "claude-sonnet-4": "Claude 多模态（经 OpenRouter）",
    "grok-4": "xAI 多模态",
    "doubao-seed-1.6": "火山方舟多模态",
    "ernie-4.5": "文心 4.5 原生多模态",
}

# 上下文窗口（tokens），未列出的按默认值
CONTEXT_WINDOWS = {
    "deepseek-flash": 128_000, "deepseek-chat": 128_000,
    "deepseek-reasoner": 128_000, "qwen-max": 131_072,
    "qwen-turbo": 131_072, "kimi-k2": 256_000, "glm-4.6": 200_000,
    "gpt-4o": 128_000, "gpt-4o-mini": 128_000,
    "gemini-2.0-flash": 1_000_000, "claude-sonnet-4": 200_000,
    "grok-4": 256_000, "llama-3.3-70b": 128_000,
}
DEFAULT_CONTEXT_WINDOW = 128_000

# 支持“推理强度”调节的模型：参数风格与可选档位
REASONING_CONFIG = {
    # 硅基流动托管的 Qwen3：enable_thinking + thinking_budget
    "siliconflow-qwen3": {"style": "qwen",
                          "levels": ["默认", "低", "中", "高"]},
    # 智谱 GLM-4.6 / 火山方舟豆包：thinking.type = enabled / disabled
    "glm-4.6": {"style": "type", "levels": ["默认", "开启", "关闭"]},
    "doubao-seed-1.6": {"style": "type", "levels": ["默认", "开启", "关闭"]},
}

MODEL_PRICING = {
    "deepseek-flash": (0.5, 2.0, "¥"),
    "deepseek-chat": (2.0, 8.0, "¥"),
    "deepseek-reasoner": (4.0, 16.0, "¥"),
    "qwen-max": (2.4, 9.6, "¥"),
    "qwen-turbo": (0.3, 0.6, "¥"),
    "kimi-k2": (4.0, 16.0, "¥"),
    "glm-4.6": (4.0, 16.0, "¥"),
    "glm-4-flash": (0.0, 0.0, "¥"),
    "gpt-4o": (2.5, 10.0, "$"),
    "gpt-4o-mini": (0.15, 0.6, "$"),
    "gemini-2.0-flash": (0.1, 0.4, "$"),
    "doubao-seed-1.6": (0.8, 8.0, "¥"),
    "grok-4": (3.0, 15.0, "$"),
    "mistral-large": (2.0, 6.0, "$"),
    "groq-llama": (0.59, 0.79, "$"),
    "siliconflow-qwen3": (2.5, 10.0, "¥"),
    "minimax-m1": (4.0, 16.0, "¥"),
    "hunyuan": (0.8, 2.0, "¥"),
    "spark": (2.0, 2.0, "¥"),
    "openrouter-auto": (1.0, 3.0, "$"),
    "claude-sonnet-4": (3.0, 15.0, "$"),
    "ernie-4.5": (0.8, 3.2, "¥"),
    "yi-large": (20.0, 20.0, "¥"),
    "baichuan4": (15.0, 15.0, "¥"),
    "step-2": (3.5, 12.0, "¥"),
    "sensechat-5": (10.0, 10.0, "¥"),
    "pplx-sonar-pro": (3.0, 15.0, "$"),
    "cohere-command-r": (2.5, 10.0, "$"),
    "jamba-large": (2.0, 8.0, "$"),
    "nvidia-llama": (0.0, 0.0, "$"),
    "together-qwen": (0.9, 0.9, "$"),
    "fireworks-deepseek": (0.9, 0.9, "$"),
    "cerebras-llama": (0.6, 0.6, "$"),
    "deepinfra-llama": (0.23, 0.4, "$"),
    "hf-llama": (0.5, 0.5, "$"),
    "ollama-local": (0.0, 0.0, "¥"),
    "lmstudio-local": (0.0, 0.0, "¥"),
}


def image_data_url(path, max_bytes=4_000_000):
    """把本地图片转成 data URL；过大或失败返回 None。"""
    try:
        if os.path.getsize(path) > max_bytes:
            return None
        ext = os.path.splitext(path)[1].lower()
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".gif": "image/gif"}.get(ext, "image/png")
        with open(path, "rb") as f:
            return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return None


def estimate_tokens(text):
    """无 usage 时的保守估算：中文按 1 token/字，其余按 4 字符/token。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return int(cjk + (len(text) - cjk) / 4) + 1


def fmt_usage(n):
    """~1.23K / ~4.56M 这样的两位小数格式。"""
    n = float(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M~"
    if n >= 1_000:
        return f"{n / 1_000:.2f}K~"
    return f"{n:.2f}~"


def usage_cost(model_id, prompt_tokens, completion_tokens):
    in_p, out_p, cur = MODEL_PRICING.get(model_id, (0.0, 0.0, "¥"))
    return (prompt_tokens / 1e6 * in_p + completion_tokens / 1e6 * out_p), cur


def ordered_models(store):
    """已导入 API 的模型置顶，组内按名称首字母排序。"""
    return sorted(MODEL_REGISTRY,
                  key=lambda c: (0 if store.configured(c["id"]) else 1,
                                 c["name"].lower()))


def build_system_prompt(cfg=None):
    cfg = cfg or MODELS_BY_ID[DEFAULT_MODEL_ID]
    name = model_title(cfg)
    return (
        f"你是一个ai助手，你的名字叫{name}。"
        "当需要输出数学公式时，请使用LaTeX语法：行内公式用 $...$ 包裹，独立公式用 $$...$$ 包裹。"
        "当需要输出化学方程式或化学式时，请用 \\ce{...} 包裹，例如 \\ce{H2O}、\\ce{2H2 + O2 -> 2H2O}。"
        "回答可以使用 Markdown：小标题用 #、列表用 -、行内代码用 `code`、代码块用 ```language 包裹。"
    )


SYSTEM_PROMPT = build_system_prompt()

MAX_HISTORY_TURNS = 6
SUMMARY_MAX_CHARS = 1200
SUMMARY_PER_MSG = 150
TITLE_MAX = 16
TITLE_MAX_CHARS = 1600
PER_MSG_CHARS = 200
TITLE_RETRY = 1
TYPE_INTERVAL_MS = 25
TYPE_CHARS_PER_TICK = 1
THINKING_FRAMES = ["●  ", " ● ", "  ●"]
THINKING_INTERVAL = 350
SPIN_INTERVAL_MS = 40
FILE_CHECK_INTERVAL_MS = 1500
API_TIMEOUT_SECONDS = 60
SAFETY_TIMEOUT_MS = 45_000

FORMULA_DPI = 110
FORMULA_FONTSIZE = 11.5
FORMULA_MIN_PNG_BYTES = 50

# 欢迎页配色（DeepSeek 风格深色）
C_WELCOME_BG = "#0b0f19"
C_WELCOME_PANEL = "#1e293b"
C_WELCOME_TEXT = "#e5e7eb"
C_WELCOME_MUTED = "#94a3b8"
C_WELCOME_BLUE = "#60a5fa"
C_WELCOME_BLUE_SOFT = "#3b82f6"

C_PRIMARY = "#2563eb"
C_PRIMARY_HOVER = "#1d4ed8"
C_PRIMARY_SOFT = "#eff6ff"
C_PRIMARY_LIGHT = "#93c5fd"
C_BG_SIDEBAR = "#0f172a"
C_BG_MAIN = "#ffffff"
C_BG_CHAT = "#f8fafc"
C_BG_INPUT = "#f1f5f9"
C_ITEM = "#1e293b"
C_ITEM_HOVER = "#334155"
C_ITEM_ACTIVE = "#2563eb"
C_TEXT_DIM = "#94a3b8"
C_TEXT_DARK = "#0f172a"
C_TEXT_MUTED = "#64748b"
C_DELETE = "#ef4444"
C_DELETE_HOVER = "#dc2626"
C_USER = "#2563eb"
C_AI = "#0f172a"
C_THINKING = "#94a3b8"
C_THINK_DONE = "#94a3b8"
C_BORDER = "#e2e8f0"
C_DISABLED = "#94a3b8"
C_FORMULA_TEXT = "#0f172a"

# ============ 设置持久化 ============
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        log_exc("save_settings failed")

# ============ Unicode 映射 ============
# 注意：这里必须是「字符 -> 字符」的字典。str.maketrans 生成的是「序号 -> 序号」，
# 直接用 dict.get(字符) 会永远 miss，导致降级公式丢失全部上下标（αpiv0001 的缺陷）。
_SUP_MAP = {c: s for c, s in zip('0123456789+-=()nix', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱˣ')}
_SUB_MAP = {c: s for c, s in zip(
    '0123456789+-=()aehijklmnoprstuvx',
    '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ')}

_GREEK = {
    r'\alpha':'α',r'\beta':'β',r'\gamma':'γ',r'\delta':'δ',
    r'\epsilon':'ε',r'\varepsilon':'ε',r'\zeta':'ζ',r'\eta':'η',
    r'\theta':'θ',r'\vartheta':'ϑ',r'\iota':'ι',r'\kappa':'κ',
    r'\lambda':'λ',r'\mu':'μ',r'\nu':'ν',r'\xi':'ξ',
    r'\pi':'π',r'\varpi':'ϖ',r'\rho':'ρ',r'\varrho':'ϱ',
    r'\sigma':'σ',r'\varsigma':'ς',r'\tau':'τ',r'\upsilon':'υ',
    r'\phi':'φ',r'\varphi':'φ',r'\chi':'χ',r'\psi':'ψ',r'\omega':'ω',
    r'\Gamma':'Γ',r'\Delta':'Δ',r'\Theta':'Θ',r'\Lambda':'Λ',
    r'\Xi':'Ξ',r'\Pi':'Π',r'\Sigma':'Σ',r'\Upsilon':'Υ',
    r'\Phi':'Φ',r'\Psi':'Ψ',r'\Omega':'Ω',
}

_SYMBOLS = {
    r'\times':'×',r'\div':'÷',r'\pm':'±',r'\mp':'∓',
    r'\cdot':'·',r'\ast':'∗',r'\star':'⋆',r'\circ':'∘',
    r'\bullet':'•',r'\oplus':'⊕',r'\ominus':'⊖',r'\otimes':'⊗',
    r'\leq':'≤',r'\le':'≤',r'\geq':'≥',r'\ge':'≥',
    r'\neq':'≠',r'\ne':'≠',r'\approx':'≈',r'\equiv':'≡',
    r'\sim':'∼',r'\simeq':'≃',r'\cong':'≅',r'\propto':'∝',
    r'\ll':'≪',r'\gg':'≫',
    r'\infty':'∞',r'\partial':'∂',r'\nabla':'∇',
    r'\sum':'∑',r'\prod':'∏',r'\coprod':'∐',
    r'\int':'∫',r'\iint':'∬',r'\iiint':'∭',r'\oint':'∮',
    r'\rightarrow':'→',r'\to':'→',r'\leftarrow':'←',r'\gets':'←',
    r'\leftrightarrow':'↔',r'\Rightarrow':'⇒',r'\Leftarrow':'⇐',
    r'\Leftrightarrow':'⇔',r'\rightleftharpoons':'⇌',
    r'\uparrow':'↑',r'\downarrow':'↓',
    r'\in':'∈',r'\notin':'∉',r'\ni':'∋',
    r'\subset':'⊂',r'\supset':'⊃',r'\subseteq':'⊆',r'\supseteq':'⊇',
    r'\cup':'∪',r'\cap':'∩',r'\setminus':'∖',
    r'\forall':'∀',r'\exists':'∃',r'\nexists':'∄',r'\neg':'¬',
    r'\land':'∧',r'\lor':'∨',
    r'\emptyset':'∅',r'\varnothing':'∅',
    r'\angle':'∠',r'\triangle':'△',r'\square':'□',
    r'\degree':'°',r'\prime':'′',r'\ldots':'…',r'\cdots':'⋯',
    r'\dots':'…',
    r'\hbar':'ℏ',r'\ell':'ℓ',
    r'\quad':'  ',r'\qquad':'    ',
    r'\,':'',r'\;':'',r'\:':'',r'\!':'',
    r'\left.':'',r'\right.':'',
    r'\langle':'⟨',r'\rangle':'⟩',
    r'\lvert':'|',r'\rvert':'|',r'\lVert':'‖',r'\rVert':'‖',
    r'\{':'{',r'\}':'}',r'\_':'_',r'\%':'%',
    r'\$':'$',r'\&':'&',r'\#':'#',
    r'\\':'; ',
}

_COMBINING = {
    'dot':'\u0307','ddot':'\u0308','dddot':'\u20db','vec':'\u20d7',
    'hat':'\u0302','check':'\u030c','breve':'\u0306',
    'acute':'\u0301','grave':'\u0300','tilde':'\u0303','bar':'\u0304',
}

_MATHBB = {'R':'ℝ','C':'ℂ','N':'ℕ','Z':'ℤ','Q':'ℚ','H':'ℍ','P':'ℙ'}
_MATHCAL = {'L':'ℒ','O':'𝒪','M':'ℳ','B':'ℬ','E':'ℰ','F':'ℱ','H':'ℋ','I':'ℐ','R':'ℛ'}

_FUNC_NAMES = (
    'arcsin','arccos','arctan','sinh','cosh','tanh','coth',
    'sin','cos','tan','cot','sec','csc','log','ln','lg','exp',
    'limsup','liminf','lim','max','min','sup','inf',
    'det','dim','ker','deg','gcd','hom','arg','Pr',
)

def _map_sup(s):
    return ''.join(_SUP_MAP.get(c, c) for c in s)

def _map_sub(s):
    return ''.join(_SUB_MAP.get(c, c) for c in s)

def _frac_repl(m):
    a, b = m.group(1), m.group(2)
    if re.search(r'[+\-*/ ]', a): a = f"({a})"
    if re.search(r'[+\-*/ ]', b): b = f"({b})"
    return f"{a}/{b}"

def _chem_to_unicode(s):
    if not s or not s.strip():
        return None
    s = s.strip()
    s = re.sub(r'\^\{([^{}]*)\}', lambda m: _map_sup(m.group(1)), s)
    s = re.sub(r'_\{([^{}]*)\}', lambda m: _map_sub(m.group(1)), s)
    s = s.replace('<=>', '⇌').replace('<->', '↔')
    s = s.replace('-->', '→').replace('->', '→').replace('<-', '←')
    def _charge(m):
        el, digits, sign = m.group(1), m.group(2), m.group(3)
        return el + _map_sup(digits + sign)
    s = re.sub(r'([A-Za-z\)])(\d*)([+\-])(?![A-Za-z])', _charge, s)
    s = re.sub(r'\^(\S)', lambda m: _map_sup(m.group(1)), s)
    s = re.sub(r'([A-Za-z\)])(\d+)', lambda m: m.group(1) + _map_sub(m.group(2)), s)
    s = re.sub(r'_(\S)', lambda m: _map_sub(m.group(1)), s)
    s = re.sub(r'([A-Za-z\)\u2080-\u2089])\.([A-Za-z\(])', r'\1·\2', s)
    if '\\' in s or '{' in s or '}' in s:
        return None
    return s

_CE_RE = re.compile(r'\\ce\{((?:[^{}]|\{[^{}]*\})*)\}')

def _math_to_unicode(s):
    if not s or not s.strip():
        return ""
    s = s.strip()
    # 先提取 \ce{}
    ce_map = {}
    _CE_PLACEHOLDER_BASE = 0xE000
    def _ce_repl(m):
        idx = len(ce_map)
        key = chr(_CE_PLACEHOLDER_BASE + idx) + chr(0xE800)
        chem = _chem_to_unicode(m.group(1))
        if chem is None or not chem.strip():
            inner = m.group(1)
            inner = re.sub(r'([A-Za-z\)])(\d+)',
                           lambda mm: mm.group(1) + _map_sub(mm.group(2)), inner)
            inner = re.sub(r'\^\{([^{}]*)\}', lambda mm: _map_sup(mm.group(1)), inner)
            inner = re.sub(r'\^(\S)', lambda mm: _map_sup(mm.group(1)), inner)
            inner = inner.replace('{', '').replace('}', '')
            chem = inner
        ce_map[key] = chem
        return key
    s = _CE_RE.sub(_ce_repl, s)

    for cmd, comb in _COMBINING.items():
        s = re.sub(r'\\' + cmd + r'\{([^{}]+)\}',
                   lambda m, c=comb: m.group(1) + c, s)
    s = re.sub(r'\\overrightarrow\{([^{}]+)\}', lambda m: m.group(1) + '\u20d7', s)
    s = re.sub(r'\\overleftarrow\{([^{}]+)\}', lambda m: m.group(1) + '\u20d6', s)
    s = re.sub(r'\\overline\{([^{}]+)\}', lambda m: m.group(1) + '\u0305', s)
    s = re.sub(r'\\underline\{([^{}]+)\}', lambda m: m.group(1) + '\u0332', s)
    s = re.sub(r'\\overbrace\{([^{}]+)\}', lambda m: m.group(1) + '\u23de', s)
    s = re.sub(r'\\underbrace\{([^{}]+)\}', lambda m: m.group(1) + '\u23df', s)

    def _matrix(m):
        env = m.group(1)
        content = m.group(2)
        rows = re.split(r'\\\\', content)
        cells = []
        for row in rows:
            parts = [c.strip() for c in row.split('&')]
            cells.append(', '.join(parts))
        inner = '; '.join(cells)
        if env == 'pmatrix': return '(' + inner + ')'
        if env == 'bmatrix': return '[' + inner + ']'
        if env == 'vmatrix': return '|' + inner + '|'
        if env == 'Vmatrix': return '‖' + inner + '‖'
        return inner
    s = re.sub(
        r'\\begin\{(pmatrix|bmatrix|vmatrix|Vmatrix|matrix|array|cases)\}'
        r'(.+?)'
        r'\\end\{\1\}',
        _matrix, s, flags=re.DOTALL)
    s = re.sub(r'\\begin\{[^}]*\}', '', s)
    s = re.sub(r'\\end\{[^}]*\}', '', s)

    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\\(?:d|t)?frac\{([^{}]*)\}\{([^{}]*)\}', _frac_repl, s)
    s = re.sub(r'\\(?:d|t)?binom\{([^{}]*)\}\{([^{}]*)\}', r'C(\1, \2)', s)
    s = re.sub(r'\\sqrt\[([^\]]*)\]\{([^{}]*)\}', r'\1√(\2)', s)
    s = re.sub(r'\\sqrt\{([^{}]*)\}', r'√(\1)', s)

    content_cmds = (
        'text','textrm','textbf','textit','textsf','texttt','mbox',
        'mathrm','mathbf','mathit','mathsf','mathtt','mathnormal',
        'operatorname',
    )
    prev = None
    while prev != s:
        prev = s
        for cmd in content_cmds:
            s = re.sub(r'\\' + cmd + r'\{([^{}]*)\}', r'\1', s)

    s = re.sub(r'\\mathbb\{(\w)\}', lambda m: _MATHBB.get(m.group(1), m.group(1)), s)
    s = re.sub(r'\\mathcal\{(\w)\}', lambda m: _MATHCAL.get(m.group(1), m.group(1)), s)

    for fn in _FUNC_NAMES:
        s = re.sub(r'\\' + fn + r'(?![a-zA-Z])', fn, s)

    # 负向断言必不可少：否则 \left 会吃掉 \leftarrow、\right 会吃掉 \rightarrow 的前缀
    s = re.sub(r'\\left(?![a-zA-Z])\s*', '', s)
    s = re.sub(r'\\right(?![a-zA-Z])\s*', '', s)
    s = re.sub(r'\\(?:bigg|Bigg|big|Big)[lrm]?(?![a-zA-Z])\s*', '', s)

    s = re.sub(r'\\tag\*?\{[^{}]*\}', '', s)
    s = re.sub(r'\\label\{[^{}]*\}', '', s)
    s = re.sub(r'\\nonumber|\\notag', '', s)

    for k in sorted(_SYMBOLS.keys(), key=len, reverse=True):
        s = s.replace(k, _SYMBOLS[k])
    for k in sorted(_GREEK.keys(), key=len, reverse=True):
        s = s.replace(k, _GREEK[k])

    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\^\{([^{}]*)\}', lambda m: _map_sup(m.group(1)), s)
        s = re.sub(r'_\{([^{}]*)\}', lambda m: _map_sub(m.group(1)), s)
    s = re.sub(r'\^(\S)', lambda m: _map_sup(m.group(1)), s)
    s = re.sub(r'_(\S)', lambda m: _map_sub(m.group(1)), s)

    s = re.sub(r'\\([a-zA-Z]+)\*?', r'\1', s)
    s = re.sub(r'\\(.)', r'\1', s)

    s = s.replace('{', '').replace('}', '')
    s = re.sub(r'[ \t]{2,}', ' ', s)

    for k, v in ce_map.items():
        s = s.replace(k, v)
    return s.strip()

def find_latex_segments(text):
    if not text:
        return []
    candidates = []
    for m in re.finditer(r'\$\$.+?\$\$', text, re.DOTALL):
        candidates.append((1, m.start(), m.end(), m.group(0)))
    for m in re.finditer(r'\\\[.+?\\\]', text, re.DOTALL):
        candidates.append((1, m.start(), m.end(), m.group(0)))
    for m in re.finditer(r'\$[^$\n]+?\$', text):
        candidates.append((2, m.start(), m.end(), m.group(0)))
    for m in re.finditer(r'\\\(.+?\\\)', text, re.DOTALL):
        candidates.append((2, m.start(), m.end(), m.group(0)))
    for m in _CE_RE.finditer(text):
        candidates.append((3, m.start(), m.end(), m.group(0)))
    candidates.sort(key=lambda x: (x[0], -(x[2] - x[1]), x[1]))
    chosen = []
    intervals = []
    for prio, start, end, raw in candidates:
        overlap = False
        for s, e in intervals:
            if start < e and end > s:
                overlap = True
                break
        if overlap:
            continue
        chosen.append((start, end, raw))
        intervals.append((start, end))
    chosen.sort(key=lambda x: x[0])
    return chosen

def _parse_latex_segment(raw):
    if raw.startswith('$$') and raw.endswith('$$') and len(raw) > 4:
        return raw[2:-2], True
    if raw.startswith('\\[') and raw.endswith('\\]') and len(raw) > 4:
        return raw[2:-2], True
    if raw.startswith('$') and raw.endswith('$') and len(raw) > 2:
        return raw[1:-1], False
    if raw.startswith('\\(') and raw.endswith('\\)') and len(raw) > 4:
        return raw[2:-2], False
    return None, False

# ============ matplotlib ============
_MPL_LOCK = threading.Lock()
_mpl_ready = False
_latex_image_cache = {}

def _has_cjk(s):
    return any('\u3400' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef' for ch in s)

def _math_src(formula):
    """matplotlib mathtext 要求公式必须包裹在 $...$ 中；裸串会被当成普通文本，
    渲染出来是 LaTeX 原文而不是排版结果（αpiv0001 的 P0 缺陷）。"""
    return '$' + formula.strip() + '$'

def warm_up_matplotlib():
    global _mpl_ready
    try:
        import matplotlib
        matplotlib.use('Agg')
        # 透明底：公式图片贴合浅色气泡背景，不出现白色方块
        matplotlib.rcParams['savefig.transparent'] = True
        from matplotlib.mathtext import math_to_image
        from matplotlib.font_manager import FontProperties
        import io
        buf = io.BytesIO()
        prop = FontProperties(size=FORMULA_FONTSIZE)
        try:
            math_to_image(_math_src('x^2'), buf, prop=prop, dpi=FORMULA_DPI,
                          format='png', color=C_FORMULA_TEXT)
        except TypeError:
            buf = io.BytesIO()
            math_to_image(_math_src('x^2'), buf, prop=prop, dpi=FORMULA_DPI, format='png')
        _mpl_ready = True
        log_info(f"matplotlib 预热完成 dpi={FORMULA_DPI} size={FORMULA_FONTSIZE}")
    except Exception:
        _mpl_ready = False
        log_exc("matplotlib 预热失败")

def render_formula_png(formula):
    global _mpl_ready
    if not _mpl_ready:
        return None
    if not formula or not formula.strip():
        return None
    # 含中文的公式交给 Unicode 降级：mathtext 缺 CJK 字形，出图是「豆腐块」
    if _has_cjk(formula):
        return None
    with _MPL_LOCK:
        if formula in _latex_image_cache:
            return _latex_image_cache[formula]
        try:
            from matplotlib.mathtext import math_to_image
            from matplotlib.font_manager import FontProperties
            import io
            prop = FontProperties(size=FORMULA_FONTSIZE)
            buf = io.BytesIO()
            try:
                math_to_image(_math_src(formula), buf, prop=prop, dpi=FORMULA_DPI,
                              format='png', color=C_FORMULA_TEXT)
            except TypeError:
                buf = io.BytesIO()
                math_to_image(_math_src(formula), buf, prop=prop, dpi=FORMULA_DPI,
                              format='png')
            png = buf.getvalue()
            if not png or len(png) < FORMULA_MIN_PNG_BYTES:
                log_info(f"[渲染] PNG过小({len(png) if png else 0}B): {formula[:40]!r}")
                return None
            _latex_image_cache[formula] = png
            log_info(f"[渲染] 成功 {len(png)}B: {formula[:40]!r}")
            return png
        except Exception as e:
            log_info(f"[渲染] mathtext失败 {formula[:40]!r}: {e}")
            return None

# ---------- 加密 ----------
KDF_ITERATIONS = 200_000

def _derive_keys(password, salt):
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt,
                             KDF_ITERATIONS, dklen=64)
    return dk[:32], dk[32:]

def _keystream(key, nonce, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(key, nonce + counter.to_bytes(4, 'big'),
                         hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])

def _encrypt_text(plaintext, password):
    salt = os.urandom(16)
    nonce = os.urandom(16)
    enc_key, mac_key = _derive_keys(password, salt)
    raw = plaintext.encode('utf-8')
    ks = _keystream(enc_key, nonce, len(raw))
    ciphertext = bytes(a ^ b for a, b in zip(raw, ks))
    mac = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(salt + nonce + mac + ciphertext)

def _decrypt_text(blob_b64, password):
    try:
        blob = base64.b64decode(blob_b64)
        if len(blob) < 16 + 16 + 32 + 1:
            return None
        salt = blob[:16]; nonce = blob[16:32]; mac = blob[32:64]
        ciphertext = blob[64:]
        enc_key, mac_key = _derive_keys(password, salt)
        expected = hmac.new(mac_key, salt + nonce + ciphertext,
                            hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            return None
        ks = _keystream(enc_key, nonce, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, ks)).decode('utf-8')
    except Exception:
        return None

def save_key_store(password, keys, current):
    """多模型密钥库整体加密落盘：{"v":2,"keys":{model_id:key},"current":id}"""
    payload = json.dumps({"v": 2, "keys": dict(keys), "current": current or ""},
                         ensure_ascii=False)
    with open(CONFIG_FILE, 'wb') as f:
        f.write(_encrypt_text(payload, password))

def load_key_store(password):
    """返回 {"keys": {...}, "current": str}；兼容 αpiv0001 的单 Key 明文结构。"""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'rb') as f:
            blob = f.read().strip()
    except Exception:
        return None
    text = _decrypt_text(blob, password)
    if text is None:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "keys" in obj:
            keys = {k: v for k, v in (obj.get("keys") or {}).items()
                    if isinstance(k, str) and isinstance(v, str) and v.strip()}
            return {"keys": keys, "current": obj.get("current") or ""}
    except Exception:
        pass
    if text.strip():
        return {"keys": {DEFAULT_MODEL_ID: text.strip()}, "current": DEFAULT_MODEL_ID}
    return None

# 兼容旧调用点
def encrypt_and_save_key(api_key, password):
    save_key_store(password, {DEFAULT_MODEL_ID: api_key}, DEFAULT_MODEL_ID)

def load_and_decrypt_key(password):
    data = load_key_store(password)
    if not data:
        return None
    return data["keys"].get(data.get("current") or DEFAULT_MODEL_ID) \
        or next(iter(data["keys"].values()), None)

# ---------- 数据层 ----------
def load_data(strict=False):
    if not os.path.exists(HISTORY_FILE):
        return {"conversations": {}, "current_id": None}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            cid = str(uuid.uuid4())
            return {
                "conversations": {cid: {
                    "title": "旧对话",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "messages": data, "summary": "",
                }},
                "current_id": cid
            }
        if not isinstance(data, dict) or "conversations" not in data:
            raise ValueError("格式错误")
        return data
    except Exception:
        if strict: raise
        return {"conversations": {}, "current_id": None}

def save_data(data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def make_new_conversation_dict(model_id=None):
    cfg = MODELS_BY_ID.get(model_id or DEFAULT_MODEL_ID,
                           MODELS_BY_ID[DEFAULT_MODEL_ID])
    return {
        "title": "新对话",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "messages": [{"role": "system", "content": build_system_prompt(cfg)}],
        "summary": "",
        "model_id": cfg["id"],
    }

def clean_text(s):
    return " ".join((s or "").split())

def center_window(win, width, height):
    win.update_idletasks()
    sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
    x = (sw - width) // 2; y = (sh - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")

class AskPasswordDialog:
    """设置启动密码时用的小对话框（密码 + 确认）。"""

    def __init__(self, parent, title="设置启动密码",
                 hint="设置一个至少 4 位的本地密码"):
        self.result = None
        self.dlg = Toplevel(parent)
        self.dlg.title(title)
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(parent)
        self.dlg.grab_set()
        self.dlg.geometry(f"420x260+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")

        Label(self.dlg, text=title, bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=(FONT_UI, 14, "bold")).pack(pady=(22, 4))
        Label(self.dlg, text=hint, bg=C_BG_MAIN, fg=C_TEXT_MUTED,
              font=(FONT_UI, 9)).pack(pady=(0, 12))
        self.e1 = tk.Entry(self.dlg, width=34, show="•", font=(FONT_MONO, 10),
                           relief=tk.FLAT, bg=C_BG_INPUT, fg=C_TEXT_DARK,
                           insertbackground=C_PRIMARY)
        self.e1.pack(ipady=6)
        self.e2 = tk.Entry(self.dlg, width=34, show="•", font=(FONT_MONO, 10),
                           relief=tk.FLAT, bg=C_BG_INPUT, fg=C_TEXT_DARK,
                           insertbackground=C_PRIMARY)
        self.e2.pack(ipady=6, pady=(8, 0))
        row = Frame(self.dlg, bg=C_BG_MAIN)
        row.pack(pady=16)
        make_rounded_button(row, "确定", self._ok, bg=C_PRIMARY, hover_bg=C_PRIMARY_HOVER,
                            fg="white", font=(FONT_UI, 10, "bold"), width=96).pack(side=tk.LEFT, padx=6)
        make_rounded_button(row, "取消", self._cancel, bg=C_BG_INPUT, fg=C_TEXT_DARK,
                            hover_bg=C_BORDER, font=(FONT_UI, 10), width=96).pack(side=tk.LEFT, padx=6)
        self.e1.focus_set()
        self.dlg.bind("<Return>", lambda e: self._ok())
        self.dlg.bind("<Escape>", lambda e: self._cancel())

    def _ok(self):
        pwd = self.e1.get()
        if len(pwd) < 4:
            messagebox.showwarning("提示", "密码至少 4 位", parent=self.dlg)
            return
        if pwd != self.e2.get():
            messagebox.showwarning("提示", "两次密码不一致", parent=self.dlg)
            return
        self.result = pwd
        self.dlg.destroy()

    def _cancel(self):
        self.result = None
        self.dlg.destroy()

    def show(self):
        self.dlg.wait_window()
        return self.result


class KeySetupDialog:
    def __init__(self, parent, first_time):
        self.parent = parent
        self.first_time = first_time
        self.result = None
        self.dlg = Toplevel(parent)
        self.dlg.title(APP_NAME + " · 添加 API Key" if first_time else AI_DISPLAY_NAME)
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(parent)
        self.dlg.grab_set()
        self._build()
        self._center()

    def _build(self):
        pad = {"padx": 24, "pady": 8}
        if self.first_time:
            Label(self.dlg, text="添加一个 API Key 以开始使用", bg=C_BG_MAIN,
                  fg=C_TEXT_DARK, font=("Microsoft YaHei", 14, "bold")).pack(pady=(24, 4))
            Label(self.dlg, text="先选择模型，再填入该服务的 Key；Key 会加密保存在本地",
                  bg=C_BG_MAIN, fg=C_TEXT_MUTED,
                  font=("Microsoft YaHei", 9)).pack(pady=(0, 14))
            Label(self.dlg, text="模型", bg=C_BG_MAIN, fg=C_TEXT_DARK,
                  font=("Microsoft YaHei", 10), anchor="w").pack(fill=tk.X, **pad)
            self._choices = sorted(MODEL_REGISTRY, key=lambda c: c["name"].lower())
            self.model_box = ttk.Combobox(
                self.dlg, state="readonly", width=42, font=("Microsoft YaHei", 10),
                values=[f"{model_title(c)}  ·  {c.get('vendor', '')}" for c in self._choices])
            default_idx = next((i for i, c in enumerate(self._choices)
                               if c["id"] == DEFAULT_MODEL_ID), 0)
            self.model_box.current(default_idx)
            self.model_box.pack(padx=24, pady=(0, 10), ipady=4)
            Label(self.dlg, text="API Key", bg=C_BG_MAIN, fg=C_TEXT_DARK,
                  font=("Microsoft YaHei", 10), anchor="w").pack(fill=tk.X, **pad)
            self.entry_key = tk.Entry(self.dlg, width=40, font=("Consolas", 10),
                                      show="•", relief=tk.FLAT, bg=C_BG_INPUT,
                                      fg=C_TEXT_DARK, insertbackground=C_PRIMARY)
            self.entry_key.pack(padx=24, pady=(0, 10), ipady=6)
            Label(self.dlg, text="密码", bg=C_BG_MAIN, fg=C_TEXT_DARK,
                  font=("Microsoft YaHei", 10), anchor="w").pack(fill=tk.X, **pad)
            self.entry_pwd = tk.Entry(self.dlg, width=40, font=("Consolas", 10),
                                      show="•", relief=tk.FLAT, bg=C_BG_INPUT,
                                      fg=C_TEXT_DARK, insertbackground=C_PRIMARY)
            self.entry_pwd.pack(padx=24, pady=(0, 10), ipady=6)
            Label(self.dlg, text="确认密码", bg=C_BG_MAIN, fg=C_TEXT_DARK,
                  font=("Microsoft YaHei", 10), anchor="w").pack(fill=tk.X, **pad)
            self.entry_pwd2 = tk.Entry(self.dlg, width=40, font=("Consolas", 10),
                                       show="•", relief=tk.FLAT, bg=C_BG_INPUT,
                                       fg=C_TEXT_DARK, insertbackground=C_PRIMARY)
            self.entry_pwd2.pack(padx=24, pady=(0, 14), ipady=6)
        else:
            Label(self.dlg, text="已保存 API Key", bg=C_BG_MAIN, fg=C_TEXT_DARK,
                  font=("Microsoft YaHei", 14, "bold")).pack(pady=(24, 4))
            Label(self.dlg, text="请输入密码解锁", bg=C_BG_MAIN, fg=C_TEXT_MUTED,
                  font=("Microsoft YaHei", 9)).pack(pady=(0, 14))
            Label(self.dlg, text="密码", bg=C_BG_MAIN, fg=C_TEXT_DARK,
                  font=("Microsoft YaHei", 10), anchor="w").pack(fill=tk.X, **pad)
            self.entry_pwd = tk.Entry(self.dlg, width=40, font=("Consolas", 10),
                                      show="•", relief=tk.FLAT, bg=C_BG_INPUT,
                                      fg=C_TEXT_DARK, insertbackground=C_PRIMARY)
            self.entry_pwd.pack(padx=24, pady=(0, 14), ipady=6)

        btn_row = Frame(self.dlg, bg=C_BG_MAIN)
        btn_row.pack(pady=(6, 22))

        def on_ok():
            if self.first_time:
                api_key = self.entry_key.get().strip()
                pwd = self.entry_pwd.get(); pwd2 = self.entry_pwd2.get()
                if not api_key:
                    messagebox.showwarning("提示", "请填写 API Key", parent=self.dlg); return
                if len(pwd) < 4:
                    messagebox.showwarning("提示", "密码至少 4 位", parent=self.dlg); return
                if pwd != pwd2:
                    messagebox.showwarning("提示", "两次密码不一致", parent=self.dlg); return
                idx = self.model_box.current()
                model_id = self._choices[idx]["id"] if idx >= 0 else DEFAULT_MODEL_ID
                self.result = ("new", model_id, api_key, pwd); self.dlg.destroy()
            else:
                pwd = self.entry_pwd.get()
                if not pwd:
                    messagebox.showwarning("提示", "请输入密码", parent=self.dlg); return
                self.result = ("unlock", pwd); self.dlg.destroy()

        def on_cancel():
            self.result = None; self.dlg.destroy()

        tk.Button(btn_row, text="确定", command=on_ok, width=12,
                  font=("Microsoft YaHei", 10, "bold"), bg=C_PRIMARY, fg="white",
                  activebackground=C_PRIMARY_HOVER, relief=tk.FLAT, bd=0,
                  cursor="hand2").pack(side=tk.LEFT, padx=6, ipady=6)
        tk.Button(btn_row, text="取消", command=on_cancel, width=12,
                  font=("Microsoft YaHei", 10), bg=C_BG_INPUT, fg=C_TEXT_DARK,
                  activebackground=C_BORDER, relief=tk.FLAT, bd=0,
                  cursor="hand2").pack(side=tk.LEFT, padx=6, ipady=6)
        self.dlg.bind("<Return>", lambda e: on_ok())
        self.dlg.bind("<Escape>", lambda e: on_cancel())

    def _center(self):
        self.dlg.update_idletasks()
        w = self.dlg.winfo_reqwidth(); h = self.dlg.winfo_reqheight()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - w) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - h) // 2
        self.dlg.geometry(f"+{x}+{y}")

    def show(self):
        self.dlg.wait_window()
        return self.result

def build_dialog_text(messages, max_chars=TITLE_MAX_CHARS, per_msg=PER_MSG_CHARS):
    lines = []
    for m in messages:
        role = m.get("role")
        if role == "system": continue
        content = clean_text(m.get("content", ""))
        if not content: continue
        if len(content) > per_msg:
            content = content[:per_msg] + "…"
        tag = "用户" if role == "user" else "助手"
        lines.append(f"{tag}：{content}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        head = text[: max_chars // 2]; tail = text[-max_chars // 2:]
        text = head + "\n……\n" + tail
    return text

def _extract_title(raw):
    if not raw: return None
    s = clean_text(raw)
    for prefix in ("标题：","标题:","摘要：","摘要:","主题：","主题:"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    s = s.strip("「」『』\"'“”‘’。，,.、!?！？：:；; \n")
    if not s: return None
    s = s.splitlines()[0].strip()
    if not s: return None
    s = s.strip("「」『』\"'“”‘’。，,.、!?！？：:；; \n")
    if len(s) > TITLE_MAX:
        s = s[:TITLE_MAX] + "…"
    return s or None

def conversation_to_text(conv):
    """把单个对话格式化为可读的 TXT 文本。"""
    lines = ["=" * 62]
    lines.append(f"标题：{conv.get('title', '未命名对话')}")
    lines.append(f"时间：{conv.get('time', '')}")
    mid = conv.get("model_id")
    if mid in MODELS_BY_ID:
        lines.append(f"模型：{model_title(MODELS_BY_ID[mid])}")
    lines.append("=" * 62)
    lines.append("")
    for m in conv.get("messages", []):
        role = m.get("role")
        if role == "system":
            continue
        content = (m.get("content") or "").strip()
        if not content:
            continue
        lines.append("【用户】" if role == "user" else "【助手】")
        te = m.get("think_elapsed")
        if role == "assistant" and te is not None:
            lines.append(f"（思考用时 {float(te):.1f} 秒）")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


# ---------- 悬浮回底按钮 ----------
class FloatingRoundButton(tk.Canvas):
    BODY_PAD = 5
    RING_PAD = 1

    def __init__(self, parent, command, size=42, bg="#ffffff",
                 fg=C_PRIMARY, hover_bg=C_PRIMARY_SOFT, hover_fg=C_PRIMARY_HOVER,
                 **kwargs):
        super().__init__(parent, width=size, height=size,
                         highlightthickness=0, bd=0, bg=parent["bg"], **kwargs)
        self.command = command
        self.size = size
        self.bg = bg; self.fg = fg
        self.hover_bg = hover_bg; self.hover_fg = hover_fg
        self._hover = False
        self._spinning = False
        self._spin_angle = 0
        self._spin_after_id = None
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: self.command())

    def set_spinning(self, spinning):
        if spinning == self._spinning: return
        self._spinning = spinning
        if spinning: self._start_spin()
        else: self._stop_spin(); self._draw()

    def _start_spin(self):
        if self._spin_after_id is None:
            self._spin_tick()

    def _spin_tick(self):
        if not self._spinning:
            self._spin_after_id = None
            return
        self._spin_angle = (self._spin_angle + 15) % 360
        self._draw()
        try:
            self._spin_after_id = self.after(SPIN_INTERVAL_MS, self._spin_tick)
        except tk.TclError:
            self._spin_after_id = None

    def _stop_spin(self):
        if self._spin_after_id is not None:
            try: self.after_cancel(self._spin_after_id)
            except Exception: pass
            self._spin_after_id = None

    def _on_enter(self, _e):
        self._hover = True; self._draw()

    def _on_leave(self, _e):
        self._hover = False; self._draw()

    def _draw(self):
        self.delete("all")
        s = self.size
        if self._spinning:
            rp = self.RING_PAD
            self.create_arc(rp, rp, s - rp, s - rp, start=self._spin_angle,
                           extent=80, style=tk.ARC, outline=C_PRIMARY, width=2)
            self.create_arc(rp, rp, s - rp, s - rp,
                           start=(self._spin_angle + 80) % 360, extent=25,
                           style=tk.ARC, outline=C_PRIMARY_LIGHT, width=2)
        pad = self.BODY_PAD
        fill = self.hover_bg if self._hover else self.bg
        outline = C_PRIMARY if self._hover else C_BORDER
        self.create_oval(pad, pad, s - pad, s - pad,
                         fill=fill, outline=outline, width=1)
        cx = s / 2; cy = s / 2
        color = self.hover_fg if self._hover else self.fg
        arrow = (s - pad * 2) * 0.24
        self.create_line(cx, cy - arrow, cx, cy + arrow,
                         fill=color, width=2, capstyle=tk.ROUND)
        self.create_line(cx - arrow * 0.7, cy + arrow * 0.2, cx, cy + arrow,
                         fill=color, width=2, capstyle=tk.ROUND)
        self.create_line(cx + arrow * 0.7, cy + arrow * 0.2, cx, cy + arrow,
                         fill=color, width=2, capstyle=tk.ROUND)

# ---------- 圆角按钮 ----------
def make_rounded_button(parent, text, command, bg, fg="white",
                        hover_bg=None, width=None, font=None,
                        radius_pad=32, height_pad=16):
    hover_bg = hover_bg or bg
    font = font or ("Microsoft YaHei", 10)
    btn = tk.Canvas(parent, highlightthickness=0, bd=0, bg=parent["bg"])
    tmp = tk.Label(btn, text=text, font=font)
    tmp.update_idletasks()
    tw = tmp.winfo_reqwidth(); th = tmp.winfo_reqheight()
    w = width or (tw + radius_pad); h = th + height_pad
    btn.config(width=w, height=h)
    state = {"enabled": True, "current_bg": bg, "text": text}

    def draw(color):
        btn.delete("all")
        r = h // 2
        btn.create_oval(0, 0, h, h, fill=color, outline=color)
        btn.create_oval(w - h, 0, w, h, fill=color, outline=color)
        btn.create_rectangle(r, 0, w - r, h, fill=color, outline=color)
        btn.create_text(w // 2, h // 2, text=state["text"], fill=fg, font=font)

    draw(bg)

    def on_enter(_e):
        if state["enabled"]: draw(hover_bg)
    def on_leave(_e):
        if state["enabled"]: draw(state["current_bg"])
    def on_click(_e):
        if state["enabled"]: command()

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    btn.bind("<Button-1>", on_click)

    def set_enabled(enabled, text_override=None):
        state["enabled"] = enabled
        if text_override is not None:
            state["text"] = text_override
        if enabled:
            state["current_bg"] = bg; draw(bg)
        else:
            state["current_bg"] = C_DISABLED; draw(C_DISABLED)

    btn.set_enabled = set_enabled
    return btn

# ---------- 圆形图标按钮 ----------
def make_icon_button(parent, text, command, size=30,
                     bg=C_BG_INPUT, fg=C_PRIMARY,
                     hover_bg=C_PRIMARY_SOFT, hover_fg=C_PRIMARY_HOVER,
                     font=None):
    font = font or ("Microsoft YaHei", 12, "bold")
    btn = tk.Canvas(parent, width=size, height=size, highlightthickness=0,
                    bd=0, bg=parent["bg"], cursor="hand2")
    state = {"hover": False}

    def draw():
        btn.delete("all")
        if state["hover"]:
            fill = hover_bg; fgc = hover_fg
            outline = C_PRIMARY
        else:
            fill = bg; fgc = fg
            outline = C_BORDER
        btn.create_oval(1, 1, size - 1, size - 1,
                        fill=fill, outline=outline, width=1)
        btn.create_text(size / 2, size / 2, text=text, fill=fgc, font=font)

    draw()
    btn.bind("<Enter>", lambda e: (state.__setitem__("hover", True), draw()))
    btn.bind("<Leave>", lambda e: (state.__setitem__("hover", False), draw()))
    btn.bind("<Button-1>", lambda e: command())
    return btn

# ============ 欢迎页（介绍页） ============
# 欢迎 / 关于页的功能分类表（只列主要功能，基础能力不再罗列）
FEATURE_GROUPS = [
    ("界面与交互", [
        ("汉堡菜单", "设置 / 模型 / 导出 三个入口"),
        ("模型选择", "品牌徽标 + 型号，按首字母排序；已导入的置顶"),
        ("分模型历史", "侧栏只显示当前模型的对话；查看其他模型时为只读"),
        ("深度思考", "按模型能力出现，可先推理再作答"),
        ("智能搜索", "联网检索后把结果注入上下文"),
        ("图片输入", "视觉模型可直接读图，失败自动跳过"),
        ("消息操作", "复制 / 重新生成 / 暂停 / 停止生成"),
        ("使用教程", "右上角 ? 打开简明图文教程"),
        ("用量统计", "输入区上方显示本对话 tokens 与折算费用"),
        ("上下文进度", "只统计本对话，接近上限自动压缩并提示"),
    ]),
    ("模型与账户", [
        ("多模型接入", "内置 37 个模型 / 32 个品牌，兼容 OpenAI 接口均可接"),
        ("推理强度", "支持的模型在输入栏下方可调"),
        ("独立 API Key", "每个模型单独保存密钥，界面只显示脱敏串"),
        ("启动密码", "可在设置里关闭，关闭后启动直接进入"),
        ("余额查询", "在对话里问「余额」即可查询 DeepSeek 账户"),
        ("加密存储", "PBKDF2-HMAC-SHA256（20 万次）+ HMAC 认证流"),
    ]),
    ("对话与推理", [
        ("推理可视化", "「▼ 已深度思考（用时 X 秒）」点击展开"),
        ("对话导出", "勾选一个或多个对话导出为 TXT"),
        ("智能标题", "首轮回答后自动生成 ≤16 字标题，只请求一次"),
    ]),
    ("渲染", [
        ("公式渲染", "行内 / 独立公式与化学式，自动选择排版图或 Unicode"),
        ("实时渲染", "生成中按行渲染 Markdown，未完成行在换行后出现"),
        ("品牌图标", "37 个模型图标，未导入时自动灰度"),
    ]),
]

KNOWN_ISSUES = [
        ("单文件版", "受限环境可能解包失败，请使用目录版"),
        ("复杂公式", "矩阵 / cases / 含中文结构会降级为 Unicode 文本"),
        ("实时渲染", "未完成的最后一行需等换行才显示"),
        ("用量与费用", "服务商不返回 usage 时为估算，费用仅供参考"),
        ("价格表", "内置单价为固定快照，官方调价后需手动更新"),
        ("余额查询", "仅 DeepSeek 提供公开余额接口"),
        ("智能搜索", "依赖 DuckDuckGo，可能被限流或取不到结果"),
        ("推理显示", "需服务商返回 reasoning_content 才有内容"),
        ("关闭启动密码", "Key 仍加密且不显示明文，但本机可直接调用"),
        ("密码找回", "无找回机制，只能删除 config.enc 重录"),
        ("模型切换", "生成回答期间不能切换模型"),
        ("多开写入", "同一目录多开会互相覆盖对话记录"),
        ("平台支持", "仅在 Windows 10/11 验证，未测 Linux/macOS"),
        ("上下文压缩", "超过 20 轮自动摘要，早期细节可能丢失"),
        ("图片输入", "仅 7 个视觉模型支持，超过 4MB 的图片会被跳过"),
        ("推理强度", "仅 Qwen 系列可调，其他模型固定为默认"),
        ("停止生成", "已生成内容会保留，可重新生成或编辑提问"),
        ("网络代理", "不支持程序内代理设置，需系统级代理"),
]


class WelcomeView(tk.Frame):
    """深色介绍页，可滚动；show_enter=True 时包含进入按钮和不再显示勾选"""
    def __init__(self, parent, on_enter=None, show_enter=True):
        super().__init__(parent, bg=C_WELCOME_BG)
        self.on_enter = on_enter
        self.show_enter = show_enter
        self.skip_var = None
        self._build()

    def _build(self):
        # 顶部固定区
        header = Frame(self, bg=C_WELCOME_BG)
        header.pack(fill=tk.X, padx=40, pady=(36, 12))
        if self.show_enter:
            title = f"欢迎使用{APP_NAME} {APP_VERSION_PUBLIC}"
            subtitle = f"Welcome to the {APP_NAME_EN}"
        else:
            title = APP_NAME
            subtitle = APP_NAME_EN
        Label(header, text=title,
              bg=C_WELCOME_BG, fg="#ffffff",
              font=(FONT_UI, 20, "bold"),
              wraplength=920, justify=tk.LEFT, anchor="w").pack(fill=tk.X)
        Label(header, text=subtitle, bg=C_WELCOME_BG, fg=C_WELCOME_BLUE,
              font=(FONT_UI, 9)).pack(anchor="w", pady=(6, 0))

        # 中间滚动区
        body = Frame(self, bg=C_WELCOME_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=(40, 20), pady=(8, 8))

        canvas = tk.Canvas(body, bg=C_WELCOME_BG, highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview,
                          width=8, bd=0, relief=tk.FLAT)
        sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        canvas.configure(yscrollcommand=sb.set)

        inner = Frame(canvas, bg=C_WELCOME_BG)
        canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner")

        def on_inner_configure(_e=None):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except tk.TclError:
                pass

        inner.bind("<Configure>", on_inner_configure)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig("inner", width=e.width))

        # ----- 简介 -----
        Label(inner, text="✦  简介", bg=C_WELCOME_BG, fg=C_WELCOME_BLUE,
              font=(FONT_UI, 14, "bold"), anchor="w").pack(fill=tk.X, pady=(4, 6))
        Label(inner,
              text="本程序是本地运行的桌面 AI 对话客户端，兼容 OpenAI 接口的模型都能接入。"
                   "所有聊天记录与 API Key 都加密保存在你自己的电脑上，"
                   "除了调用你所选模型的 API 之外，不会向任何第三方上传数据。"
                   "主要能力：多模型独立密钥、深度思考与推理可视化、智能搜索、"
                   "对话导出、用量计费、API 余额查询与 LaTeX 公式渲染。\n"
               "已知问题的完整清单见下方「已知问题」一栏。",
              bg=C_WELCOME_BG, fg=C_WELCOME_TEXT,
              font=(FONT_UI, 11),
              wraplength=800, justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(0, 18))

        # ----- 功能列表（分类表格） -----
        Label(inner, text="✦  已支持功能", bg=C_WELCOME_BG, fg=C_WELCOME_BLUE,
              font=(FONT_UI, 14, "bold"), anchor="w").pack(fill=tk.X, pady=(4, 6))
        self._feature_table(inner)

        Label(inner, text="⚠  已知问题", bg=C_WELCOME_BG, fg="#f0b27a",
              font=(FONT_UI, 14, "bold"), anchor="w").pack(fill=tk.X, pady=(14, 6))
        self._issues_table(inner)

        Label(inner, text="", bg=C_WELCOME_BG).pack(pady=8)

        # ----- 底部固定区 -----
        if self.show_enter:
            footer = Frame(self, bg=C_WELCOME_BG)
            footer.pack(fill=tk.X, padx=40, pady=(4, 22))

            row = Frame(footer, bg=C_WELCOME_BG)
            row.pack(fill=tk.X)

            enter_btn = make_rounded_button(
                row, "进入主程序", self._on_click_enter,
                bg=C_PRIMARY, hover_bg=C_PRIMARY_HOVER, fg="white",
                font=("Microsoft YaHei", 12, "bold"),
                radius_pad=80, height_pad=24
            )
            enter_btn.pack(side=tk.LEFT)

            self.skip_var = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(
                row, text="以后不再显示此页面",
                variable=self.skip_var,
                bg=C_WELCOME_PANEL, fg=C_WELCOME_MUTED,
                selectcolor=C_PRIMARY,
                activebackground=C_WELCOME_PANEL,
                activeforeground="#ffffff",
                indicatoron=0,
                font=("Microsoft YaHei", 10),
                bd=0, highlightthickness=0, cursor="hand2",
                padx=14, pady=6
            )
            cb.pack(side=tk.LEFT, padx=(18, 0))

        # 让整页（含表格、说明块）都能用鼠标滚轮滚动
        bind_wheel_all(inner, canvas)

    def _feature_table(self, parent, groups=None):
        """分类表格：分类列纵向跨行，功能 / 说明两列逐行展开。"""
        groups = groups if groups is not None else FEATURE_GROUPS
        border = C_WELCOME_PANEL
        table = Frame(parent, bg=border)
        table.pack(fill=tk.X, pady=(2, 8))
        table.columnconfigure(0, minsize=100)
        table.columnconfigure(1, minsize=158)
        table.columnconfigure(2, weight=1)

        def cell(r, c, text, fg, font, bg=C_WELCOME_BG, wrap=None,
                 rowspan=1, anchor="nw"):
            holder = Frame(table, bg=bg)
            holder.grid(row=r, column=c, rowspan=rowspan, sticky="nsew",
                        padx=(1, 0), pady=(1, 0))
            Label(holder, text=text, bg=bg, fg=fg, font=font, anchor=anchor,
                  justify=tk.LEFT, wraplength=wrap or 0).pack(
                fill=tk.BOTH, expand=True, padx=10, pady=7)

        head_bg = "#111a2b"
        cell(0, 0, "分类", C_WELCOME_MUTED, (FONT_UI, 8, "bold"), bg=head_bg)
        cell(0, 1, "功能", C_WELCOME_MUTED, (FONT_UI, 8, "bold"), bg=head_bg)
        cell(0, 2, "说明", C_WELCOME_MUTED, (FONT_UI, 8, "bold"), bg=head_bg)

        r = 1
        for cat, items in groups:
            start = r
            for name, desc in items:
                cell(r, 1, name, C_WELCOME_BLUE, (FONT_UI, 9, "bold"))
                cell(r, 2, desc, C_WELCOME_TEXT, (FONT_UI, 9), wrap=500)
                r += 1
            cell(start, 0, cat, C_WELCOME_BLUE_SOFT, (FONT_UI, 9, "bold"),
                 bg="#0e1626", rowspan=r - start)
        Frame(table, bg=border, height=1).grid(
            row=r, column=0, columnspan=3, sticky="ew")

    def _issues_table(self, parent):
        """已知问题：独立的两列表格。"""
        border = C_WELCOME_PANEL
        table = Frame(parent, bg=border)
        table.pack(fill=tk.X, pady=(2, 8))
        table.columnconfigure(0, minsize=158)
        table.columnconfigure(1, weight=1)
        head_bg = "#2a1c12"
        cell_specs = [(0, 0, "问题", 120), (0, 1, "说明", None)]
        for r_, c_, text, _w in cell_specs:
            holder = Frame(table, bg=head_bg)
            holder.grid(row=r_, column=c_, sticky="nsew", padx=(1, 0), pady=(1, 0))
            Label(holder, text=text, bg=head_bg, fg="#f0b27a",
                  font=(FONT_UI, 8, "bold"), anchor="nw").pack(
                fill=tk.BOTH, expand=True, padx=10, pady=7)
        r = 1
        for name, desc in KNOWN_ISSUES:
            for c_, text, fg, bold in ((0, name, "#f0b27a", True),
                                       (1, desc, "#d9c3ac", False)):
                holder = Frame(table, bg=C_WELCOME_BG)
                holder.grid(row=r, column=c_, sticky="nsew",
                            padx=(1, 0), pady=(1, 0))
                Label(holder, text=text, bg=C_WELCOME_BG, fg=fg,
                      font=(FONT_UI, 9, "bold" if bold else "normal"),
                      anchor="nw", justify=tk.LEFT,
                      wraplength=520 if c_ == 1 else 0).pack(
                    fill=tk.BOTH, expand=True, padx=10, pady=7)
            r += 1
        Frame(table, bg=border, height=1).grid(
            row=r, column=0, columnspan=2, sticky="ew")

    def _on_click_enter(self):
        skip = False
        if self.skip_var is not None:
            try:
                skip = bool(self.skip_var.get())
            except Exception:
                skip = False
        if self.on_enter:
            self.on_enter(skip)

class WelcomeWindow:
    """从 About 打开的欢迎页（Toplevel，无进入按钮）"""
    def __init__(self, parent):
        self.dlg = Toplevel(parent)
        self.dlg.title(AI_DISPLAY_NAME + " - 关于")
        self.dlg.configure(bg=C_WELCOME_BG)
        self.dlg.transient(parent)
        w, h = 940, 740
        sw = self.dlg.winfo_screenwidth(); sh = self.dlg.winfo_screenheight()
        x = (sw - w) // 2; y = (sh - h) // 2
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        view = WelcomeView(self.dlg, on_enter=None, show_enter=False)
        view.pack(fill=tk.BOTH, expand=True)


# ============ 使用教程 ============
HELP_SECTIONS = [
    ("① 快速开始", [
        ("填 Key", "菜单 → 模型 → 选模型 → 粘贴 Key"),
        ("选模型", "点侧栏顶部卡片切换"),
        ("开始聊", "Enter 发送 · Shift+Enter 换行"),
    ]),
    ("② 界面", [
        ("☰ 左上", "设置 / 模型 / 导出"),
        ("? 右上", "本教程"),
        ("i 右上", "关于、版本号、项目主页"),
    ]),
    ("③ 输入与推理", [
        ("◈ 深度思考", "开启后才显示并保留推理过程"),
        ("🌐 智能搜索", "先联网检索再回答"),
        ("📄 附件", "文本并入提问；图片需模型支持"),
        ("⏸ 暂停 / 停止", "生成中可暂停显示或直接停止"),
    ]),
    ("④ 常见问题", [
        ("公式变文字", "超出渲染能力，自动转 Unicode"),
        ("上下文变红", "接近上限，会自动压缩历史"),
        ("查余额", "仅 DeepSeek 支持"),
    ]),
]

class HelpWindow:
    """使用教程页：与关于页同款深色排版，按功能分区列出用法。"""

    def __init__(self, parent):
        self.dlg = Toplevel(parent)
        self.dlg.title(APP_NAME + " - 使用教程")
        self.dlg.configure(bg=C_WELCOME_BG)
        self.dlg.transient(parent)
        w, h = 960, 760
        sw = self.dlg.winfo_screenwidth()
        sh = self.dlg.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        self.dlg.resizable(False, False)
        self._build()

    def _build(self):
        header = Frame(self.dlg, bg=C_WELCOME_BG)
        header.pack(fill=tk.X, padx=40, pady=(28, 8))
        Label(header, text="使用教程", bg=C_WELCOME_BG, fg="#ffffff",
              font=(FONT_UI, 20, "bold"), anchor="w").pack(fill=tk.X)
        Label(header, text="User Guide · 所有功能入口与操作方式",
              bg=C_WELCOME_BG, fg=C_WELCOME_BLUE,
              font=(FONT_UI, 9), anchor="w").pack(fill=tk.X, pady=(6, 0))

        body = Frame(self.dlg, bg=C_WELCOME_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=(40, 22), pady=(6, 8))
        canvas = tk.Canvas(body, bg=C_WELCOME_BG, highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview,
                          width=8, bd=0, relief=tk.FLAT)
        sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        canvas.configure(yscrollcommand=sb.set)

        inner = Frame(canvas, bg=C_WELCOME_BG)
        canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig("inner", width=e.width))

        for title, rows in HELP_SECTIONS:
            self._section(inner, title, rows)

        foot = Frame(self.dlg, bg=C_WELCOME_BG)
        foot.pack(fill=tk.X, padx=40, pady=(4, 18))
        make_rounded_button(foot, "关闭", self.dlg.destroy, bg=C_PRIMARY,
                            hover_bg=C_PRIMARY_HOVER, fg="white",
                            font=(FONT_UI, 10, "bold"), width=120).pack(
            side=tk.RIGHT)
        bind_wheel_all(inner, canvas)
        self.dlg.bind("<Escape>", lambda e: self.dlg.destroy())

    def _section(self, parent, title, rows):
        """圆角卡片式小节。"""
        wrap = Frame(parent, bg=C_WELCOME_BG)
        wrap.pack(fill=tk.X, pady=(0, 10))
        cv = tk.Canvas(wrap, bg=C_WELCOME_BG, highlightthickness=0, bd=0,
                       height=10)
        cv.pack(fill=tk.X)
        inner = Frame(cv, bg=C_WELCOME_PANEL)
        win = cv.create_window(18, 12, window=inner, anchor="nw")
        Label(inner, text=title, bg=C_WELCOME_PANEL, fg=C_WELCOME_BLUE,
              font=(FONT_UI, 11, "bold"), anchor="w").pack(
            fill=tk.X, pady=(0, 6))
        for name, desc in rows:
            row = Frame(inner, bg=C_WELCOME_PANEL)
            row.pack(fill=tk.X, pady=2)
            Label(row, text=name, bg=C_WELCOME_PANEL, fg="#ffffff",
                  font=(FONT_UI, 9, "bold"), width=12, anchor="nw",
                  justify=tk.LEFT).pack(side=tk.LEFT, anchor="n")
            Label(row, text=desc, bg=C_WELCOME_PANEL, fg=C_WELCOME_TEXT,
                  font=(FONT_UI, 9), anchor="w", justify=tk.LEFT,
                  wraplength=620).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def redraw(_e=None):
            inner.update_idletasks()
            w = max(2, cv.winfo_width())
            h = inner.winfo_reqheight() + 24
            cv.configure(height=h)
            cv.coords(win, 18, 12)
            cv.itemconfigure(win, width=max(120, w - 36))
            cv.delete("card")
            item = draw_round_rect(cv, 1, 1, w - 2, h - 2, 14,
                                   C_WELCOME_PANEL, "#1f2b3d", 1)
            cv.addtag_withtag("card", item)
            cv.tag_lower("card")
        cv.bind("<Configure>", redraw)
        cv.after(30, redraw)


class AboutDialog:
    """信息键 → 小窗：应用名称 + 版本号，两个按钮竖排居中。"""
    def __init__(self, parent, app=None):
        self.parent = parent
        self.app = app
        self.dlg = Toplevel(parent)
        self.dlg.title("关于 " + APP_NAME)
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(parent)
        self.dlg.grab_set()
        self.dlg.update_idletasks()
        w, h = 460, 424
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        self._build()

    def _build(self):
        header = Frame(self.dlg, bg=C_BG_SIDEBAR, height=124)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        head_box = Frame(header, bg=C_BG_SIDEBAR)
        head_box.pack(expand=True)
        Label(head_box, text=APP_NAME, bg=C_BG_SIDEBAR, fg="#ffffff",
              font=(FONT_UI, 17, "bold"), wraplength=380,
              justify=tk.CENTER).pack(padx=20)
        Label(head_box, text=APP_NAME_EN, bg=C_BG_SIDEBAR, fg=C_WELCOME_BLUE,
              font=(FONT_UI, 9)).pack(pady=(5, 0))

        body = Frame(self.dlg, bg=C_BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True, padx=30, pady=(22, 0))

        for key, value in (("版本号", APP_VERSION_PUBLIC),):
            row = Frame(body, bg=C_BG_MAIN)
            row.pack(fill=tk.X, pady=2)
            Label(row, text=key, bg=C_BG_MAIN, fg=C_TEXT_MUTED,
                  font=(FONT_UI, 10), width=8, anchor="w").pack(side=tk.LEFT)
            Label(row, text=value, bg=C_BG_MAIN, fg=C_TEXT_DARK,
                  font=(FONT_UI, 10, "bold"), anchor="w").pack(side=tk.LEFT)
        link_row = Frame(body, bg=C_BG_MAIN)
        link_row.pack(fill=tk.X, pady=(10, 0))
        Label(link_row, text="项目主页", bg=C_BG_MAIN, fg=C_TEXT_MUTED,
              font=(FONT_UI, 10), width=8, anchor="w").pack(side=tk.LEFT)
        link = Label(link_row, text=GITHUB_URL, bg=C_BG_MAIN, fg="#2563eb",
                     font=(FONT_UI, 9, "underline"), anchor="w",
                     cursor="hand2")
        link.pack(side=tk.LEFT, fill=tk.X, expand=True)
        link.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))

        tk.Frame(body, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(14, 0))

        btn_col = Frame(body, bg=C_BG_MAIN)
        btn_col.pack(pady=(26, 0))
        make_rounded_button(
            btn_col, "关于", self._show_welcome,
            bg=C_PRIMARY, hover_bg=C_PRIMARY_HOVER, fg="white",
            font=(FONT_UI, 11, "bold"),
            radius_pad=60, height_pad=18, width=200
        ).pack(pady=(0, 10))
        make_rounded_button(
            btn_col, "关闭", self.close,
            bg=C_BG_INPUT, fg=C_TEXT_DARK, hover_bg=C_BORDER,
            font=(FONT_UI, 11),
            radius_pad=60, height_pad=18, width=200
        ).pack()

        Label(self.dlg, text=APP_VERSION, bg=C_BG_MAIN, fg="#b9c3d1",
              font=(FONT_UI, 8)).place(x=18, rely=1.0, y=-12, anchor="sw")
        self.dlg.bind("<Escape>", lambda e: self.close())

    def close(self):
        try:
            self.dlg.grab_release()
        except Exception:
            pass
        try:
            self.dlg.destroy()
        except Exception:
            pass

    def _show_welcome(self):
        try:
            self.dlg.grab_release()
        except Exception:
            pass
        self.dlg.destroy()
        WelcomeWindow(self.parent)

# ============ αpiv0002：状态层（模型 / API Key） ============
FONT_UI = "Microsoft YaHei"
FONT_MONO = "Consolas"

C_MENU_BG = "#dbeafe"          # 菜单浮层：浅蓝色背景
C_MENU_HOVER = "#bfdbfe"
C_MENU_BORDER = "#93c5fd"
C_ROW_BG = "#ffffff"
C_ROW_HOVER = "#f1f7ff"
C_ROW_SELECTED = "#eff6ff"
C_ROW_DISABLED = "#eef2f7"
C_ROW_DISABLED_TEXT = "#a8b3c4"
C_CODE_BG = "#f1f5f9"
C_CODE_KW = "#7c3aed"
C_CODE_STR = "#0f766e"
C_CODE_COM = "#94a3b8"
C_CODE_NUM = "#b45309"

KEY_MASK = "sk-****...****"


def mask_key(key):
    if not key:
        return ""
    prefix = key[:3] if key.lower().startswith("sk-") else key[:2]
    return f"{prefix}****...****"


class ModelStore:
    """模型列表 + 每个模型独立 API Key 的单一状态源。

    界面只读取 ``configured(mid)`` 决定是否置灰；写入 Key 后统一走
    ``save()`` 落盘，保证「列表状态」与「配置文件」永远一致。
    """

    def __init__(self, password, payload=None):
        payload = payload or {}
        self.password = password
        self.keys = dict(payload.get("keys") or {})
        self.current = payload.get("current") or ""
        self._clients = {}
        self.ensure_current()

    # ---- 查询 ----
    def configured(self, mid):
        return bool((self.keys.get(mid) or "").strip())

    def get_key(self, mid):
        return self.keys.get(mid) or ""

    def cfg(self, mid=None):
        mid = mid or self.current
        return MODELS_BY_ID.get(mid, MODELS_BY_ID[DEFAULT_MODEL_ID])

    def current_cfg(self):
        return self.cfg(self.current)

    def enabled_count(self):
        return sum(1 for m in MODEL_REGISTRY if self.configured(m["id"]))

    # ---- 变更 ----
    def ensure_current(self):
        if self.current in MODELS_BY_ID and self.configured(self.current):
            return
        for m in MODEL_REGISTRY:
            if self.configured(m["id"]):
                self.current = m["id"]
                return
        self.current = DEFAULT_MODEL_ID

    def set_key(self, mid, key):
        key = (key or "").strip()
        if key:
            self.keys[mid] = key
        else:
            self.keys.pop(mid, None)
        self._clients.pop(mid, None)
        self.ensure_current()

    def clear_key(self, mid):
        self.keys.pop(mid, None)
        self._clients.pop(mid, None)
        if self.current == mid:
            self.current = ""
        self.ensure_current()

    def set_current(self, mid):
        if not self.configured(mid):
            return False
        self.current = mid
        self.save()
        return True

    def save(self):
        save_key_store(self.password, self.keys, self.current)

    def change_password(self, new_password):
        """重写密钥库口令（用于关闭/开启启动密码）。"""
        self.password = new_password
        self.save()

    # ---- 客户端 ----
    def client(self, mid=None):
        mid = mid or self.current
        if not self.configured(mid):
            return None
        if mid not in self._clients:
            cfg = self.cfg(mid)
            self._clients[mid] = OpenAI(api_key=self.keys[mid],
                                        base_url=cfg["base_url"],
                                        timeout=API_TIMEOUT_SECONDS)
        return self._clients[mid]


# ============ 通用绘制 ============
def draw_round_rect(cv, x1, y1, x2, y2, r, fill, outline=None, width=1):
    r = max(1, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, splinesteps=24,
                             fill=fill, outline=outline or fill, width=width)


def make_pill_group(parent, options, holder, on_change, bg=C_BG_MAIN,
                    font_size=8, height=24):
    """一组圆角胶囊，holder[0] 为当前值；点击切换并回调。"""
    f = tkfont.Font(family=FONT_UI, size=font_size)
    spans = []
    x = 0
    for text in options:
        w = f.measure(text) + 18
        spans.append((x, x + w, text))
        x += w + 5
    cv = tk.Canvas(parent, width=max(40, x - 5), height=height, bg=bg,
                   highlightthickness=0, bd=0)

    def draw():
        cv.delete("all")
        for x1, x2, text in spans:
            on = (holder[0] == text)
            draw_round_rect(cv, x1, 2, x2, height - 2, (height - 4) // 2,
                            C_PRIMARY if on else C_BG_INPUT,
                            C_PRIMARY if on else C_BORDER, 1)
            cv.create_text((x1 + x2) / 2, height / 2, text=text,
                           fill="#ffffff" if on else C_TEXT_DARK,
                           font=(FONT_UI, font_size))

    def click(e):
        for x1, x2, text in spans:
            if x1 <= e.x <= x2:
                holder[0] = text
                draw()
                on_change(text)
                return
    cv.bind("<Button-1>", click)
    draw()
    cv._redraw = draw
    return cv


def bind_wheel_all(widget, canvas, step=3):
    """让 widget 及其所有子控件上的滚轮事件都滚动 canvas。

    Tk 的 <MouseWheel> 不会冒泡：只有鼠标正下方的控件收到事件。
    可滚动区域里塞满 Label/Frame/Canvas 时，滚轮就会「失灵」。
    """
    def on_wheel(event):
        delta = getattr(event, "delta", 0)
        if delta:
            amount = int(-delta / 120)
            if amount == 0:
                amount = -1 if delta > 0 else 1
        else:
            amount = step
        try:
            canvas.yview_scroll(amount, "units")
        except tk.TclError:
            pass
        return "break"

    def on_up(_e):
        try:
            canvas.yview_scroll(-step, "units")
        except tk.TclError:
            pass
        return "break"

    def on_down(_e):
        try:
            canvas.yview_scroll(step, "units")
        except tk.TclError:
            pass
        return "break"

    def walk(w):
        # 同一个控件只绑一次：重复 bind 会让一次滚轮滚动多倍
        if getattr(w, "_wheel_canvas", None) is not canvas:
            try:
                w._wheel_canvas = canvas
                w.bind("<MouseWheel>", on_wheel, add="+")
                w.bind("<Button-4>", on_up, add="+")
                w.bind("<Button-5>", on_down, add="+")
            except Exception:
                pass
        for child in w.winfo_children():
            walk(child)

    walk(widget)


# ============ 组件：圆形菜单按钮 ============
class CircleMenuButton(tk.Canvas):
    """浅蓝浮层里的圆形按钮：齿轮（设置）/「AI」（模型）。"""

    def __init__(self, parent, kind="gear", label="", size=54, command=None,
                 bg=C_MENU_BG, accent=C_PRIMARY):
        super().__init__(parent, width=size, height=size + 22,
                         highlightthickness=0, bd=0, bg=bg, cursor="hand2")
        self.size = size
        self.kind = kind
        self.label = label
        self.command = command
        self.bg = bg
        self.accent = accent
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: command() if command else None)

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.size
        c = s / 2
        fill = self.accent if self._hover else "#ffffff"
        icon = "#ffffff" if self._hover else self.accent
        self.create_oval(1, 1, s - 1, s - 1, fill=fill,
                         outline=C_MENU_BORDER, width=1)
        if self.kind == "gear":
            self._draw_gear(c, icon)
        elif self.kind == "export":
            self._draw_export(c, icon)
        else:
            self.create_text(c, c, text="AI", fill=icon,
                             font=(FONT_UI, max(11, int(s * 0.34)), "bold"))
        self.create_text(c, s + 10, text=self.label, fill=C_TEXT_DARK,
                         font=(FONT_UI, 8))

    def _draw_export(self, c, color):
        w = max(2, int(self.size * 0.07))
        self.create_line(c - 8, c + 6, c - 8, c + 10, c + 8, c + 10, c + 8, c + 6,
                         fill=color, width=w, capstyle=tk.ROUND,
                         joinstyle=tk.ROUND)
        self.create_line(c, c - 11, c, c + 3, fill=color, width=w,
                         capstyle=tk.ROUND)
        self.create_line(c - 5, c - 2, c, c + 3, fill=color, width=w,
                         capstyle=tk.ROUND)
        self.create_line(c + 5, c - 2, c, c + 3, fill=color, width=w,
                         capstyle=tk.ROUND)

    def _draw_gear(self, c, color):
        r = self.size * 0.17
        w = max(3, int(self.size * 0.085))
        for i in range(8):
            a = math.radians(i * 45)
            self.create_line(c + math.cos(a) * r * 1.05,
                             c + math.sin(a) * r * 1.05,
                             c + math.cos(a) * r * 1.55,
                             c + math.sin(a) * r * 1.55,
                             fill=color, width=w, capstyle=tk.ROUND)
        self.create_oval(c - r, c - r, c + r, c + r, outline=color, width=w)
        self.create_oval(c - r * 0.32, c - r * 0.32, c + r * 0.32, c + r * 0.32,
                         outline="", fill=color)


# ============ 组件：汉堡菜单（浅蓝 Popover） ============
class HamburgerMenu(tk.Toplevel):
    """点击左上角汉堡键后，向右弹出的浅蓝浮层：设置 / 模型 / 导出。"""

    W = 232
    H = 104

    def __init__(self, master, anchor, on_settings, on_models, on_export):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=C_MENU_BG)
        self.attributes("-topmost", True)
        self._closed = False
        self._watch_id = None

        card = tk.Frame(self, bg=C_MENU_BG, highlightthickness=1,
                        highlightbackground=C_MENU_BORDER, bd=0)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        row = tk.Frame(card, bg=C_MENU_BG)
        row.pack(expand=True, padx=8, pady=(10, 2))
        CircleMenuButton(row, kind="gear", label="设置", size=52,
                         command=lambda: self._pick(on_settings)).pack(side=tk.LEFT, padx=5)
        CircleMenuButton(row, kind="ai", label="模型", size=52,
                         command=lambda: self._pick(on_models)).pack(side=tk.LEFT, padx=5)
        CircleMenuButton(row, kind="export", label="导出", size=52,
                         command=lambda: self._pick(on_export)).pack(side=tk.LEFT, padx=5)

        self.update_idletasks()
        try:
            ax = anchor.winfo_rootx()
            ay = anchor.winfo_rooty()
            ah = anchor.winfo_height()
        except tk.TclError:
            ax, ay, ah = 0, 0, 0
        x = ax + anchor.winfo_width() - 6
        y = ay + ah + 6
        sw = self.winfo_screenwidth()
        if x + self.W > sw - 8:
            x = sw - self.W - 8
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

        self.bind("<Escape>", lambda e: self.close())
        self.after(30, self._grab_focus)
        self._watch_id = self.after(260, self._watch_focus)

    def _grab_focus(self):
        try:
            self.focus_force()
        except Exception:
            pass

    def _watch_focus(self):
        if self._closed or not self.winfo_exists():
            return
        try:
            fg = self.focus_get()
        except Exception:
            fg = None
        if fg is not None:
            try:
                inside = str(fg).startswith(str(self))
            except Exception:
                inside = False
            if not inside:
                self.close()
                return
        self._watch_id = self.after(260, self._watch_focus)

    def _pick(self, callback):
        self.close()
        if callback:
            try:
                callback()
            except Exception:
                log_exc("菜单回调失败")

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._watch_id is not None:
            try:
                self.after_cancel(self._watch_id)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass


# ============ 组件：汉堡键 / 模型胶囊 ============
class HamburgerButton(tk.Canvas):
    def __init__(self, parent, command, size=34):
        super().__init__(parent, width=size, height=size, bg=C_BG_MAIN,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.size = size
        self.command = command
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: command())

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.size
        if self._hover:
            self.create_oval(1, 1, s - 1, s - 1, fill=C_PRIMARY_SOFT, outline="")
        color = C_PRIMARY if self._hover else C_TEXT_MUTED
        half = s * 0.22
        for dy in (-half * 0.9, 0, half * 0.9):
            self.create_line(s / 2 - half, s / 2 + dy, s / 2 + half, s / 2 + dy,
                             fill=color, width=2, capstyle=tk.ROUND)


class SidebarModelCard(tk.Canvas):
    """侧栏「当前模型」卡片：只负责选择，点击打开「变更模型/版本」。"""

    def __init__(self, parent, command):
        super().__init__(parent, height=64, bg=C_BG_SIDEBAR,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self._name = "未选择模型"
        self._sub = ""
        self._note = ""
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: self.command())

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def set_model(self, name, sub="", note=""):
        self._name = name or "未选择模型"
        self._sub = sub or ""
        self._note = note or ""
        self._draw()

    def _draw(self):
        self.delete("all")
        try:
            w = self.winfo_width()
        except tk.TclError:
            return
        if w < 20:
            return
        h = 64
        bg = "#243449" if self._hover else C_ITEM
        outline = C_PRIMARY if self._hover else "#334155"
        draw_round_rect(self, 1, 1, w - 2, h - 2, 13, bg, outline, 1)

        name = self._name
        font = tkfont.Font(family=FONT_UI, size=9, weight="bold")
        while name and font.measure(name) > (w - 46):
            name = name[:-1]
        if name != self._name:
            name = name[:-1] + "…"
        self.create_text(13, 23, anchor="w", text=name, fill="#ffffff", font=font)
        sub = self._sub
        if self._note:
            sub = (sub + "  ·  " + self._note) if sub else self._note
        self.create_text(14, 45, anchor="w", text=sub, fill=C_TEXT_DIM,
                         font=(FONT_UI, 8))
        self.create_text(w - 16, 32, anchor="e", text="▾",
                         fill=C_PRIMARY_LIGHT, font=(FONT_UI, 10))


class InfoIconButton(tk.Canvas):
    """右上角圆形图标键：中间是 Georgia 字形（i / ?）。"""

    def __init__(self, parent, command, size=32, glyph="i", font=None):
        super().__init__(parent, width=size, height=size, bg=C_BG_MAIN,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.size = size
        self.command = command
        self.glyph = glyph
        self.font = font or ("Georgia", 13, "bold italic")
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: command())

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.size
        c = s / 2
        if self._hover:
            self.create_oval(1, 1, s - 1, s - 1, fill=C_PRIMARY,
                             outline=C_PRIMARY, width=1)
            fg = "#ffffff"
        else:
            self.create_oval(1, 1, s - 1, s - 1, fill=C_BG_INPUT,
                             outline=C_BORDER, width=1)
            fg = C_PRIMARY
        if self.glyph == "?":
            self.create_text(c, c - 1, text="?", fill=fg,
                             font=("Segoe UI", 15, "bold"))
        else:
            self.create_text(c, c + 1, text=self.glyph, fill=fg, font=self.font)


# ============ 组件：顶部导航栏 ============
class NavigationBar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C_BG_MAIN, height=52)
        self.app = app
        self.pack_propagate(False)
        self._menu = None

        left = tk.Frame(self, bg=C_BG_MAIN)
        left.pack(side=tk.LEFT, padx=(16, 0), pady=9)
        self.hamburger = HamburgerButton(left, self.toggle_menu)
        self.hamburger.pack(side=tk.LEFT)

        right = tk.Frame(self, bg=C_BG_MAIN)
        right.pack(side=tk.RIGHT, padx=16)
        self.about_icon = InfoIconButton(
            right, self.app._open_about, size=32, glyph="i",
            font=("Georgia", 13, "bold italic"))
        self.about_icon.pack(side=tk.RIGHT)
        self.help_icon = InfoIconButton(
            right, self.app.open_help, size=32, glyph="?",
            font=("Georgia", 13, "bold"))
        self.help_icon.pack(side=tk.RIGHT, padx=(0, 8))

        tk.Frame(self, bg=C_BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)

    def refresh(self):
        """模型信息已移到侧栏卡片，这里只保留调用占位。"""
        return

    def toggle_menu(self):
        if self._menu is not None and not self._menu._closed:
            self._menu.close()
            self._menu = None
            return
        self._menu = HamburgerMenu(self, self.hamburger,
                                   on_settings=self.app.open_settings,
                                   on_models=self.app.open_api_manager,
                                   on_export=self.app.open_export)
        self.after(400, self._forget_menu)

    def _forget_menu(self):
        if self._menu is not None and self._menu._closed:
            self._menu = None


# ============ 品牌徽标 ============
BRAND_STYLE = {
    "DeepSeek": ("#4D6BFE", "D"),
    "Alibaba": ("#615CED", "Q"),
    "Moonshot": ("#111827", "K"),
    "Zhipu": ("#3B6EF6", "G"),
    "OpenAI": ("#10A37F", "O"),
    "Google": ("#4285F4", "G"),
    "ByteDance": ("#325AB4", "D"),
    "xAI": ("#111111", "X"),
    "Mistral": ("#FF7000", "M"),
    "Groq": ("#F55036", "G"),
    "SiliconFlow": ("#6E56CF", "S"),
    "MiniMax": ("#E8434A", "M"),
    "Tencent": ("#0052D9", "T"),
    "iFlytek": ("#0066FF", "i"),
    "OpenRouter": ("#6B7280", "O"),
    "Anthropic": ("#D97757", "C"),
    "Baidu": ("#2932E1", "E"),
    "01.AI": ("#16A34A", "Y"),
    "Baichuan": ("#2563EB", "B"),
    "StepFun": ("#7C3AED", "S"),
    "SenseTime": ("#0057FF", "S"),
    "Perplexity": ("#20808D", "P"),
    "Cohere": ("#39594D", "C"),
    "AI21": ("#E11D48", "J"),
    "NVIDIA": ("#76B900", "N"),
    "Together": ("#0F6FFF", "T"),
    "Fireworks": ("#FF5D22", "F"),
    "Cerebras": ("#F26522", "C"),
    "DeepInfra": ("#4F46E5", "D"),
    "HuggingFace": ("#F59E0B", "H"),
    "Ollama": ("#111827", "O"),
    "LM Studio": ("#6B7280", "L"),
}
_LOGO_CACHE = {}


def brand_logo(model_id, dim=False):
    """assets/logos/<id>.png 存在则返回商标图；dim=True 优先用灰度版。"""
    key = (model_id, dim)
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    base = os.path.join(BASE_DIR, "assets", "logos", model_id)
    path = base + ("_dim.png" if dim else ".png")
    if dim and not os.path.exists(path):
        path = base + ".png"
    photo = None
    if os.path.exists(path):
        try:
            photo = tk.PhotoImage(file=path)
        except Exception:
            photo = None
    _LOGO_CACHE[key] = photo
    return photo


# ============ 组件：模型列表行 ============
class ModelRowButton(tk.Canvas):
    H = 68

    def __init__(self, parent, cfg, configured, selected, on_select, on_api=None):
        super().__init__(parent, height=self.H, bg=C_ROW_BG,
                         highlightthickness=0, bd=0,
                         cursor="hand2" if configured else "arrow")
        self.cfg = cfg
        self.configured = configured
        self.selected = selected
        self.on_select = on_select
        self.on_api = on_api
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw_brand(self, x, y):
        logo = brand_logo(self.cfg["id"], dim=not self.configured)
        if logo is not None:
            self.create_image(x + 17, y + 17, image=logo)
            return
        color, letter = BRAND_STYLE.get(self.cfg.get("vendor", ""), ("#64748b", "?"))
        if not self.configured:
            color = "#c3ccd9"
        draw_round_rect(self, x, y, x + 34, y + 34, 9, color, color, 1)
        self.create_text(x + 17, y + 17, text=letter, fill="#ffffff",
                         font=(FONT_UI, 12, "bold"))

    def _on_enter(self, _e):
        if self.configured:
            self._hover = True
            self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def _on_click(self, event):
        try:
            w = self.winfo_width()
        except tk.TclError:
            return
        if self.on_api is not None and event.x > w - 110:
            self.on_api(self.cfg)
        elif self.configured:
            self.on_select(self.cfg)

    def _draw(self):
        self.delete("all")
        try:
            w = self.winfo_width()
        except tk.TclError:
            return
        if w < 20:
            return
        h = self.H
        if not self.configured:
            bg = C_ROW_DISABLED
            border = "#e2e8f0"
            name_fg = C_ROW_DISABLED_TEXT
            sub_fg = C_ROW_DISABLED_TEXT
        elif self.selected:
            bg = C_ROW_SELECTED
            border = C_PRIMARY
            name_fg = C_TEXT_DARK
            sub_fg = C_TEXT_MUTED
        else:
            bg = C_ROW_HOVER if self._hover else C_ROW_BG
            border = C_BORDER
            name_fg = C_TEXT_DARK
            sub_fg = C_TEXT_MUTED

        draw_round_rect(self, 2, 2, w - 3, h - 3, 14, bg, border, 1)

        # 品牌徽标 + 型号
        self._draw_brand(12, 17)
        self.create_text(58, 25, anchor="w", text=self.cfg["name"],
                         fill=name_fg, font=(FONT_UI, 11, "bold"))
        mark = self.cfg.get("mark") or ""
        if mark:
            name_w = tkfont.Font(family=FONT_UI, size=11, weight="bold").measure(
                self.cfg["name"])
            self.create_text(58 + name_w + 4, 20, anchor="w", text=mark,
                             fill=sub_fg, font=(FONT_UI, 8))

        sub = self.cfg.get("vendor", "")
        self.create_text(58, 46, anchor="w", text=sub,
                         fill=sub_fg, font=(FONT_UI, 8))

        if self.configured:
            badge = "✓ 已配置" if not self.selected else "✓ 当前使用"
            self.create_text(w - 22, 25, anchor="e", text=badge,
                             fill=C_PRIMARY, font=(FONT_UI, 8, "bold"))
            if self.on_api is not None:
                self.create_text(w - 22, 46, anchor="e", text="修改 API",
                                 fill=C_TEXT_MUTED, font=(FONT_UI, 8))
        else:
            self.create_text(w - 22, 25, anchor="e", text="未导入 API",
                             fill=C_ROW_DISABLED_TEXT, font=(FONT_UI, 8, "bold"))
            hint = "导入 ›" if self.on_api is not None else "菜单 → 模型"
            self.create_text(w - 22, 46, anchor="e", text=hint,
                             fill=C_PRIMARY if self.on_api is not None else C_ROW_DISABLED_TEXT,
                             font=(FONT_UI, 8))


# ============ 组件：模型列表弹窗「变更模型/版本」 ============
class ModelPickerDialog:
    def __init__(self, app):
        self.app = app
        self.dlg = tk.Toplevel(app.root)
        self.dlg.title("变更模型/版本")
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(app.root)
        self.dlg.grab_set()
        w, h = 620, 600
        sw = self.dlg.winfo_screenwidth()
        sh = self.dlg.winfo_screenheight()
        x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
        y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        x = max(20, min(x, sw - w - 20))
        y = max(20, min(y, sh - h - 40))
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        self._build()
        self.dlg.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        head = tk.Frame(self.dlg, bg=C_BG_MAIN)
        head.pack(fill=tk.X, padx=24, pady=(20, 6))
        Label(head, text="变更模型/版本", bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=(FONT_UI, 18, "bold"), anchor="w").pack(fill=tk.X)
        Label(head, text="选择要使用的模型。未导入 API Key 的模型为禁用状态"
                         "（导入请用菜单 → 模型）。",
              bg=C_BG_MAIN, fg=C_TEXT_MUTED,
              font=(FONT_UI, 9), anchor="w").pack(fill=tk.X, pady=(4, 0))

        body = tk.Frame(self.dlg, bg=C_BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True, padx=(20, 12), pady=(10, 6))
        self.canvas = tk.Canvas(body, bg=C_BG_MAIN, highlightthickness=0, bd=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=self.canvas.yview,
                          width=8, bd=0, relief=tk.FLAT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set)

        self.inner = tk.Frame(self.canvas, bg=C_BG_MAIN)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw",
                                  tags="inner")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig("inner", width=e.width))

        foot = tk.Frame(self.dlg, bg=C_BG_MAIN)
        foot.pack(fill=tk.X, padx=24, pady=(4, 20))
        make_rounded_button(foot, "关闭", self.close, bg=C_BG_INPUT,
                            fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=(FONT_UI, 10), width=100).pack(side=tk.RIGHT)
        self._rebuild()

    def _rebuild(self):
        for w in self.inner.winfo_children():
            w.destroy()
        store = self.app.store
        group = None
        for cfg in ordered_models(store):
            configured = store.configured(cfg["id"])
            if configured != group:
                group = configured
                Label(self.inner,
                      text="已导入 API" if configured else "未导入 API",
                      bg=C_BG_MAIN, fg=C_TEXT_MUTED,
                      font=(FONT_UI, 8, "bold"), anchor="w").pack(
                    fill=tk.X, padx=6, pady=(8, 2))
            row = ModelRowButton(
                self.inner, cfg,
                configured=configured,
                selected=(cfg["id"] == store.current),
                on_select=self._select,
                on_api=None)
            row.pack(fill=tk.X, padx=2, pady=4)
        tk.Frame(self.inner, bg=C_BG_MAIN, height=8).pack(fill=tk.X)
        self.canvas.update_idletasks()
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except tk.TclError:
            pass
        bind_wheel_all(self.inner, self.canvas)

    def _select(self, cfg):
        if self.app.switch_model(cfg["id"]):
            self._rebuild()

    def close(self):
        try:
            self.dlg.grab_release()
        except Exception:
            pass
        try:
            self.dlg.destroy()
        except Exception:
            pass


# ============ 组件：API 管理弹窗（菜单 →「模型」） ============
class ApiManagerDialog:
    """集中管理各模型的 API Key：导入 / 修改 / 清除都在这里。"""

    def __init__(self, app):
        self.app = app
        self.dlg = tk.Toplevel(app.root)
        self.dlg.title("修改/导入API")
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(app.root)
        self.dlg.grab_set()
        w, h = 620, 600
        sw = self.dlg.winfo_screenwidth()
        sh = self.dlg.winfo_screenheight()
        x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
        y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        x = max(20, min(x, sw - w - 20))
        y = max(20, min(y, sh - h - 40))
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        self._build()
        self.dlg.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        head = tk.Frame(self.dlg, bg=C_BG_MAIN)
        head.pack(fill=tk.X, padx=24, pady=(20, 6))
        Label(head, text="修改/导入API", bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=(FONT_UI, 18, "bold"), anchor="w").pack(fill=tk.X)
        Label(head, text="每个模型单独保存密钥。已保存的 Key 只会显示脱敏串，不会明文回显。",
              bg=C_BG_MAIN, fg=C_TEXT_MUTED,
              font=(FONT_UI, 9), anchor="w").pack(fill=tk.X, pady=(4, 0))

        body = tk.Frame(self.dlg, bg=C_BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True, padx=(20, 12), pady=(10, 6))
        self.canvas = tk.Canvas(body, bg=C_BG_MAIN, highlightthickness=0, bd=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=self.canvas.yview,
                          width=8, bd=0, relief=tk.FLAT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set)

        self.inner = tk.Frame(self.canvas, bg=C_BG_MAIN)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw",
                                  tags="inner")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig("inner", width=e.width))

        foot = tk.Frame(self.dlg, bg=C_BG_MAIN)
        foot.pack(fill=tk.X, padx=24, pady=(4, 20))
        make_rounded_button(foot, "关闭", self.close, bg=C_BG_INPUT,
                            fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=(FONT_UI, 10), width=100).pack(side=tk.RIGHT)
        self._rebuild()

    def _rebuild(self):
        for w in self.inner.winfo_children():
            w.destroy()
        store = self.app.store
        group = None
        for cfg in ordered_models(store):
            configured = store.configured(cfg["id"])
            if configured != group:
                group = configured
                Label(self.inner,
                      text="已导入 API" if configured else "未导入 API",
                      bg=C_BG_MAIN, fg=C_TEXT_MUTED,
                      font=(FONT_UI, 8, "bold"), anchor="w").pack(
                    fill=tk.X, padx=6, pady=(8, 2))
            row = ModelRowButton(
                self.inner, cfg,
                configured=configured,
                selected=(cfg["id"] == store.current),
                on_select=self._edit,
                on_api=self._edit)
            row.pack(fill=tk.X, padx=2, pady=4)
        tk.Frame(self.inner, bg=C_BG_MAIN, height=8).pack(fill=tk.X)
        self.canvas.update_idletasks()
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except tk.TclError:
            pass
        bind_wheel_all(self.inner, self.canvas)

    def _edit(self, cfg):
        ApiKeyDialog(self.app, cfg["id"], on_done=self._rebuild)

    def close(self):
        try:
            self.dlg.grab_release()
        except Exception:
            pass
        try:
            self.dlg.destroy()
        except Exception:
            pass


# ============ 组件：API 配置弹窗「修改/导入API」 ============
class ApiKeyDialog:
    """已保存的 Key 任何情况下都不以明文显示：输入框默认是脱敏占位串。"""

    def __init__(self, app, model_id, on_done=None):
        self.app = app
        self.model_id = model_id
        self.cfg = app.store.cfg(model_id)
        self.on_done = on_done
        self._masked = False

        self.dlg = tk.Toplevel(app.root)
        self.dlg.title("修改/导入API")
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(app.root)
        self.dlg.grab_set()
        w, h = 560, 366
        x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
        y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        self._build()
        self.dlg.protocol("WM_DELETE_WINDOW", self.close)
        self.dlg.bind("<Escape>", lambda e: self.close())

    def _build(self):
        head = tk.Frame(self.dlg, bg=C_BG_MAIN)
        head.pack(fill=tk.X, padx=26, pady=(20, 4))
        Label(head, text="修改/导入API", bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=(FONT_UI, 18, "bold"), anchor="w").pack(fill=tk.X)

        status = "已配置（密钥已加密保存）" if self.app.store.configured(
            self.model_id) else "未配置"
        Label(head, text=f"{model_title(self.cfg)} · {self.cfg['base_url']}",
              bg=C_BG_MAIN, fg=C_TEXT_MUTED, font=(FONT_UI, 9),
              anchor="w").pack(fill=tk.X, pady=(4, 0))
        Label(head, text=f"当前状态：{status}", bg=C_BG_MAIN, fg=C_PRIMARY,
              font=(FONT_UI, 9, "bold"), anchor="w").pack(fill=tk.X, pady=(2, 0))

        body = tk.Frame(self.dlg, bg=C_BG_MAIN)
        body.pack(fill=tk.X, padx=26, pady=(16, 0))
        Label(body, text="API Key", bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=(FONT_UI, 10), anchor="w").pack(fill=tk.X, pady=(0, 6))
        self.entry = tk.Entry(body, font=(FONT_MONO, 10), relief=tk.FLAT,
                              bg=C_BG_INPUT, fg=C_TEXT_DARK,
                              insertbackground=C_PRIMARY)
        self.entry.pack(fill=tk.X, ipady=8, padx=1)
        if self.app.store.configured(self.model_id):
            self.entry.configure(fg=C_TEXT_MUTED)
            self.entry.insert(0, KEY_MASK)
            self._masked = True
        self.entry.bind("<FocusIn>", self._clear_mask)
        self.entry.bind("<Key>", self._clear_mask)

        Label(body, text="为防止泄露，已保存的 Key 不会以明文回显；直接输入新 Key 即可覆盖。",
              bg=C_BG_MAIN, fg=C_TEXT_MUTED, font=(FONT_UI, 8),
              anchor="w", justify=tk.LEFT, wraplength=490
              ).pack(fill=tk.X, pady=(8, 0))

        foot = tk.Frame(self.dlg, bg=C_BG_MAIN)
        foot.pack(fill=tk.X, padx=26, pady=(22, 20))
        make_rounded_button(foot, "保存并启用", self._save, bg=C_PRIMARY,
                            hover_bg=C_PRIMARY_HOVER, fg="white",
                            font=(FONT_UI, 10, "bold"), width=130
                            ).pack(side=tk.LEFT)
        if self.app.store.configured(self.model_id):
            make_rounded_button(foot, "清除密钥", self._clear, bg=C_BG_INPUT,
                                fg=C_DELETE, hover_bg="#fee2e2",
                                font=(FONT_UI, 10), width=100
                                ).pack(side=tk.LEFT, padx=(10, 0))
        make_rounded_button(foot, "取消", self.close, bg=C_BG_INPUT,
                            fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=(FONT_UI, 10), width=90).pack(side=tk.RIGHT)

    def _clear_mask(self, _e=None):
        if self._masked:
            self._masked = False
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=C_TEXT_DARK, show="•")

    def _save(self):
        value = self.entry.get().strip()
        if self._masked or not value:
            if self.app.store.configured(self.model_id):
                self.close()
                return
            messagebox.showwarning("提示", "请输入该模型的 API Key", parent=self.dlg)
            return
        if len(value) < 8:
            messagebox.showwarning("提示", "API Key 长度不足，请检查", parent=self.dlg)
            return
        self.app.store.set_key(self.model_id, value)
        try:
            self.app.store.save()
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self.dlg)
            return
        self.app.on_model_config_changed()
        if self.on_done:
            self.on_done()
        self.close()

    def _clear(self):
        if not messagebox.askyesno("清除密钥",
                                   f"确定删除 {model_title(self.cfg)} 的 API Key？",
                                   parent=self.dlg):
            return
        self.app.store.clear_key(self.model_id)
        try:
            self.app.store.save()
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self.dlg)
            return
        self.app.on_model_config_changed()
        if self.on_done:
            self.on_done()
        self.close()

    def close(self):
        try:
            self.dlg.grab_release()
        except Exception:
            pass
        try:
            self.dlg.destroy()
        except Exception:
            pass


# ============ 组件：设置面板 ============
class SettingsDialog:
    def __init__(self, app):
        self.app = app
        self.dlg = tk.Toplevel(app.root)
        self.dlg.title("设置")
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(app.root)
        self.dlg.grab_set()
        w, h = 480, 500
        x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
        y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        self._build()

    def _build(self):
        Label(self.dlg, text="设置", bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=(FONT_UI, 18, "bold"), anchor="w").pack(
            fill=tk.X, padx=26, pady=(20, 2))
        Label(self.dlg, text=f"{APP_NAME} · {APP_VERSION_PUBLIC}", bg=C_BG_MAIN,
              fg=C_TEXT_MUTED, font=(FONT_UI, 9), anchor="w").pack(
            fill=tk.X, padx=26, pady=(0, 12))
        tk.Frame(self.dlg, bg=C_BORDER, height=1).pack(fill=tk.X, padx=26)

        body = tk.Frame(self.dlg, bg=C_BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True, padx=26, pady=(14, 0))

        self.font_var = tk.IntVar(value=self.app.chat_font_size)
        self._segment(body, "对话字号", self.font_var,
                      [("小", 10), ("标准", 11), ("大", 13)], self._on_font)

        cur_speed = self.app.type_interval_ms
        speed_val = 25 if cur_speed == 25 else (10 if 0 < cur_speed < 25 else
                                                (50 if cur_speed > 25 else 0))
        self.speed_var = tk.IntVar(value=speed_val)
        self._segment(body, "打字机速度", self.speed_var,
                      [("快", 10), ("标准", 25), ("慢", 50), ("关闭", 0)],
                      self._on_speed)

        self.send_var = tk.IntVar(value=1 if self.app.send_with_ctrl else 0)
        self._segment(body, "发送方式", self.send_var,
                      [("Enter 发送", 0), ("Ctrl+Enter 发送", 1)], self._on_send)

        self.reason_var = tk.IntVar(value=1 if self.app.show_reasoning else 0)
        self._segment(body, "推理过程", self.reason_var,
                      [("关闭", 0), ("显示", 1)], self._on_reasoning)

        self.pwd_var = tk.IntVar(value=1 if self.app.password_required else 0)
        self._segment(body, "启动密码", self.pwd_var,
                      [("需要", 1), ("不需要", 0)], self._on_password)

        tk.Frame(body, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(8, 12))
        make_rounded_button(body, "打开数据文件夹", self._open_data_dir,
                            bg=C_BG_INPUT, fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=(FONT_UI, 9), width=150).pack(anchor="w")

        make_rounded_button(self.dlg, "关闭", self.dlg.destroy, bg=C_PRIMARY,
                            fg="white", hover_bg=C_PRIMARY_HOVER,
                            font=(FONT_UI, 10, "bold"), width=110).pack(
            side=tk.BOTTOM, pady=16)

    def _segment(self, parent, label, var, options, command, note=""):
        """圆角胶囊分段控件（替代原生 Radiobutton）。"""
        row = tk.Frame(parent, bg=C_BG_MAIN)
        row.pack(fill=tk.X, pady=(0, 12))
        Label(row, text=label, bg=C_BG_MAIN, fg=C_TEXT_MUTED,
              font=(FONT_UI, 9), width=9, anchor="w").pack(side=tk.LEFT)

        f = tkfont.Font(family=FONT_UI, size=9)
        spans = []
        x = 0
        for text, _v in options:
            w = f.measure(text) + 26
            spans.append((x, x + w, text, _v))
            x += w + 6
        total = max(60, x - 6)

        cv = tk.Canvas(row, width=total, height=30, bg=C_BG_MAIN,
                       highlightthickness=0, bd=0)
        cv.pack(side=tk.LEFT)

        def draw():
            cv.delete("all")
            for i, (x1, x2, text, value) in enumerate(spans):
                on = (var.get() == value)
                draw_round_rect(cv, x1, 3, x2, 27, 12,
                                C_PRIMARY if on else C_BG_INPUT,
                                C_PRIMARY if on else C_BORDER, 1)
                cv.create_text((x1 + x2) / 2, 15, text=text,
                               fill="#ffffff" if on else C_TEXT_DARK,
                               font=(FONT_UI, 9))

        def on_click(e):
            for _x1, _x2, _text, value in spans:
                if _x1 <= e.x <= _x2:
                    var.set(value)
                    draw()
                    command()
                    return

        cv.bind("<Button-1>", on_click)
        cv.bind("<Configure>", lambda e: draw())
        draw()
        if note:
            Label(row, text=note, bg=C_BG_MAIN, fg="#b45309",
                  font=(FONT_UI, 8)).pack(side=tk.LEFT, padx=(8, 0))

    # ---------- 设置项回调 ----------
    def _on_font(self):
        self.app.apply_chat_font(self.font_var.get())

    def _on_speed(self):
        self.app.type_interval_ms = int(self.speed_var.get())
        self.app.save_setting("type_speed", self.app.type_interval_ms)

    def _on_send(self):
        ctrl = bool(self.send_var.get())
        self.app.send_with_ctrl = ctrl
        self.app.composer.set_send_mode(ctrl)
        self.app.save_setting("send_with_ctrl", ctrl)

    def _on_password(self):
        want = bool(self.pwd_var.get())
        if want == self.app.password_required:
            return
        store = self.app.store
        if want:
            pwd = AskPasswordDialog(self.dlg, "设置启动密码",
                                    "下次启动需要输入这个密码").show()
            if not pwd:
                self.pwd_var.set(0)
                return
            try:
                store.change_password(pwd)
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=self.dlg)
                self.pwd_var.set(0)
                return
            self.app.password_required = True
            self.app.save_setting("password_required", True)
            messagebox.showinfo("已启用", "下次启动需要输入密码。", parent=self.dlg)
        else:
            if not messagebox.askyesno(
                    "关闭启动密码",
                    "关闭后启动不再要求密码，但密钥仍然加密保存，"
                    "任何界面都不会显示 Key 的明文。\n\n"
                    "区别只是：本机使用者无需密码即可直接调用已保存的 Key。\n"
                    "确定关闭？", parent=self.dlg):
                self.pwd_var.set(1)
                return
            try:
                store.change_password(NO_PASSWORD)
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=self.dlg)
                self.pwd_var.set(1)
                return
            self.app.password_required = False
            self.app.save_setting("password_required", False)
            messagebox.showinfo("已关闭", "下次启动将直接进入。", parent=self.dlg)

    def _on_reasoning(self):
        show = bool(self.reason_var.get())
        self.app.show_reasoning = show
        self.app.save_setting("show_reasoning", show)
        try:
            self.app.load_conversation(self.app.data["current_id"])
        except Exception:
            pass

    def _open_data_dir(self):
        try:
            os.startfile(BASE_DIR)
        except Exception:
            log_exc("打开数据文件夹失败")


# ============ 组件：导出对话 ============
class ExportDialog:
    def __init__(self, app):
        self.app = app
        self.vars = {}
        self.dlg = tk.Toplevel(app.root)
        self.dlg.title("导出对话")
        self.dlg.configure(bg=C_BG_MAIN)
        self.dlg.resizable(False, False)
        self.dlg.transient(app.root)
        self.dlg.grab_set()
        w, h = 560, 600
        sw = self.dlg.winfo_screenwidth()
        sh = self.dlg.winfo_screenheight()
        x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
        y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        x = max(20, min(x, sw - w - 20))
        y = max(20, min(y, sh - h - 40))
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")
        self._build()
        self.dlg.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        head = tk.Frame(self.dlg, bg=C_BG_MAIN)
        head.pack(fill=tk.X, padx=24, pady=(20, 4))
        Label(head, text="导出对话", bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=(FONT_UI, 18, "bold"), anchor="w").pack(fill=tk.X)
        Label(head, text="勾选一个或多个对话，导出为 TXT 文本。",
              bg=C_BG_MAIN, fg=C_TEXT_MUTED, font=(FONT_UI, 9),
              anchor="w").pack(fill=tk.X, pady=(4, 0))

        tools = tk.Frame(self.dlg, bg=C_BG_MAIN)
        tools.pack(fill=tk.X, padx=24, pady=(10, 4))
        make_rounded_button(tools, "全选", self._select_all, bg=C_BG_INPUT,
                            fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=(FONT_UI, 9), width=70).pack(side=tk.LEFT)
        make_rounded_button(tools, "清空", self._clear_all, bg=C_BG_INPUT,
                            fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=(FONT_UI, 9), width=70).pack(side=tk.LEFT,
                                                               padx=(8, 0))

        body = tk.Frame(self.dlg, bg=C_BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True, padx=(18, 10), pady=(6, 4))
        self.canvas = tk.Canvas(body, bg=C_BG_MAIN, highlightthickness=0, bd=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=self.canvas.yview,
                          width=8, bd=0, relief=tk.FLAT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set)
        self.inner = tk.Frame(self.canvas, bg=C_BG_MAIN)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw",
                                  tags="inner")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig("inner", width=e.width))

        foot = tk.Frame(self.dlg, bg=C_BG_MAIN)
        foot.pack(fill=tk.X, padx=24, pady=(4, 20))
        make_rounded_button(foot, "取消", self.close, bg=C_BG_INPUT,
                            fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=(FONT_UI, 10), width=90).pack(side=tk.RIGHT)
        make_rounded_button(foot, "导出 TXT", self._export, bg=C_PRIMARY,
                            fg="white", hover_bg=C_PRIMARY_HOVER,
                            font=(FONT_UI, 10, "bold"), width=110).pack(
            side=tk.RIGHT, padx=(0, 10))
        self._rebuild()

    def _rebuild(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.vars.clear()
        items = sorted(self.app.data["conversations"].items(),
                       key=lambda kv: kv[1].get("time", ""), reverse=True)
        for cid, conv in items:
            title = conv.get("title", "未命名对话")
            when = conv.get("time", "")
            count = max(0, len(conv.get("messages", [])) - 1)
            var = tk.BooleanVar(value=False)
            self.vars[cid] = var
            cb = tk.Checkbutton(
                self.inner, text=f"{title}    {when}    · {count} 条消息",
                variable=var, anchor="w", justify=tk.LEFT,
                bg=C_ROW_BG, fg=C_TEXT_DARK, activebackground=C_ROW_HOVER,
                selectcolor=C_BG_MAIN, font=(FONT_UI, 9), bd=0,
                highlightthickness=0, padx=10, pady=6, cursor="hand2")
            cb.pack(fill=tk.X, padx=2, pady=2)
        if not items:
            Label(self.inner, text="还没有对话可以导出。", bg=C_BG_MAIN,
                  fg=C_TEXT_MUTED, font=(FONT_UI, 9)).pack(pady=20)
        self.canvas.update_idletasks()
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except tk.TclError:
            pass
        bind_wheel_all(self.inner, self.canvas)

    def _select_all(self):
        for v in self.vars.values():
            v.set(True)

    def _clear_all(self):
        for v in self.vars.values():
            v.set(False)

    def _export(self):
        chosen = [cid for cid, v in self.vars.items() if v.get()]
        if not chosen:
            messagebox.showinfo("提示", "请至少勾选一个对话", parent=self.dlg)
            return
        default = f"对话导出_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        path = filedialog.asksaveasfilename(
            parent=self.dlg, title="导出为 TXT", defaultextension=".txt",
            initialfile=default, filetypes=[("文本文件", "*.txt")])
        if not path:
            return
        convs = [(cid, self.app.data["conversations"][cid])
                 for cid in chosen if cid in self.app.data["conversations"]]
        convs.sort(key=lambda kv: kv[1].get("time", ""))
        parts = [f"{APP_NAME} {APP_VERSION_PUBLIC} 对话导出\n"
                 f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                 f"对话数量：{len(convs)}\n"]
        for _, conv in convs:
            parts.append(conversation_to_text(conv))
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("\n\n".join(parts))
        except Exception as e:
            messagebox.showerror("导出失败", str(e), parent=self.dlg)
            return
        messagebox.showinfo("导出完成", f"已导出 {len(convs)} 个对话：\n{path}",
                            parent=self.dlg)
        self.close()

    def close(self):
        try:
            self.dlg.grab_release()
        except Exception:
            pass
        try:
            self.dlg.destroy()
        except Exception:
            pass


# ============ 组件：Markdown + 代码高亮 + 公式渲染 ============
class MessageRenderer:
    """把一条回答渲染进 Text：Markdown 结构、代码高亮、公式图片、消息操作条。"""

    _FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
    _BLOCK_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.DOTALL)
    _INLINE_RE = re.compile(
        r"(?P<code>`[^`\n]+`)"
        r"|(?P<bold>\*\*[^*\n]+\*\*|__[^_\n]+__)"
        r"|(?P<italic>(?<!\*)\*[^*\n]+\*(?!\*))"
        r"|(?P<link>\[[^\]\n]+\]\([^)\n]+\))"
        r"|(?P<ph>[\ue000-\ue0ff])")
    _CODE_RE = re.compile(
        r"(#.*$|//.*$)"
        r"|(\"[^\"\n]*\"|'[^'\n]*')"
        r"|(\b[A-Za-z_]\w*\b)"
        r"|(\d+\.?\d*)")
    _KEYWORDS = {
        "def", "class", "return", "if", "else", "elif", "for", "while", "import",
        "from", "as", "try", "except", "finally", "with", "lambda", "yield",
        "async", "await", "pass", "break", "continue", "in", "is", "not", "and",
        "or", "None", "True", "False", "self", "print", "function", "const",
        "let", "var", "new", "this", "public", "private", "void", "int", "float",
        "string", "bool", "struct", "namespace", "using", "template", "select",
        "where", "insert", "update", "delete", "create", "table",
    }

    def __init__(self, app):
        self.app = app

    # ---------- 入口 ----------
    def render_assistant(self, widget, content, cid=None, msg_index=None,
                         reasoning="", expanded=False, think_elapsed=None):
        if think_elapsed is not None:
            try:
                self._render_think_header(widget, think_elapsed, reasoning,
                                          cid, msg_index, expanded)
            except Exception:
                log_exc("思考头渲染失败")
        if not content:
            return
        try:
            self._render_content(widget, content)
        except Exception:
            log_exc("Markdown 渲染失败，回退纯文本")
            try:
                widget.insert(tk.END, content, "content")
            except Exception:
                pass
        if cid is not None and msg_index is not None:
            try:
                self._insert_actions(widget, cid, msg_index, content)
            except Exception:
                log_exc("操作条插入失败")

    def _render_think_header(self, widget, elapsed, reasoning, cid, idx, expanded):
        """DeepSeek 风格：一行「已深度思考（用时 X 秒）」，可展开看推理。"""
        has_reason = (bool((reasoning or "").strip())
                      and getattr(self.app, "show_reasoning", False)
                      and cid is not None and idx is not None)
        arrow = ("▼ " if expanded else "▶ ") if has_reason else ""
        head = f"{arrow}已深度思考（用时 {float(elapsed):.1f} 秒）\n"
        line_no = int(widget.index("end").split(".")[0])
        widget.insert(tk.END, head, "think_head")
        if has_reason:
            try:
                self.app._think_lines[(cid, idx)] = line_no
            except Exception:
                pass
        widget.insert(tk.END, "\n", "content")
        if has_reason and expanded:
            widget.insert(tk.END, (reasoning or "").strip() + "\n\n", "reason_body")

    def render_user(self, widget, content):
        widget.insert(tk.END, content, "content_user")

    # ---------- 块级 ----------
    def _render_content(self, widget, text):
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        pos = 0
        for m in self._FENCE_RE.finditer(text):
            if m.start() > pos:
                block = text[pos:m.start()].strip("\n")
                if block:
                    self._render_text(widget, block)
            self._ensure_newline(widget)
            if widget.index("end-1c") != "1.0":
                widget.insert(tk.END, "\n", "content")
            self._render_code(widget, m.group(2), m.group(1).strip())
            pos = m.end()
        tail = text[pos:].strip("\n")
        if tail:
            self._render_text(widget, tail)
        self._ensure_newline(widget)

    def _ensure_newline(self, widget):
        if widget.index("end-1c") == "1.0":
            return
        if widget.get("end-2c", "end-1c") != "\n":
            widget.insert(tk.END, "\n", "content")

    def _render_text(self, widget, text):
        # 先处理跨行的独立公式块（$$...$$ / \[...\]），否则逐行解析会把它们拆散
        pos = 0
        for m in self._BLOCK_MATH_RE.finditer(text):
            if m.start() > pos:
                self._render_text_lines(widget, text[pos:m.start()])
            latex = m.group(1) if m.group(1) is not None else m.group(2)
            self._render_block_formula(widget, latex)
            pos = m.end()
        if pos < len(text):
            self._render_text_lines(widget, text[pos:])

    def _render_block_formula(self, widget, latex):
        """独立公式：优先排版图并居中，其次 Unicode，最后保留原文。"""
        latex = (latex or "").strip()
        if not latex:
            return
        self._ensure_newline(widget)
        photo = None
        try:
            photo = self.app._get_formula_photo(latex)
        except Exception:
            photo = None
        if photo is not None:
            try:
                # 两侧各放一个带居中标签的空格，保证这一行被判定为居中段落
                widget.insert(tk.END, " ", "formula_block")
                widget.image_create(tk.END, image=photo, align="center",
                                    padx=2, pady=3)
                widget.insert(tk.END, " \n", "formula_block")
                return
            except tk.TclError:
                pass
        uni = _math_to_unicode(latex)
        if uni and uni.strip():
            widget.insert(tk.END, uni + "\n", "formula_block_text")
        else:
            widget.insert(tk.END, latex + "\n", "formula_src")

    def _render_text_lines(self, widget, text):
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                widget.insert(tk.END, "\n", "content")
                continue
            if re.match(r"^#{1,6}\s+", stripped):
                level = len(stripped) - len(stripped.lstrip("#"))
                body = stripped[level:].strip()
                widget.insert(tk.END, body + "\n",
                              "md_h1" if level <= 2 else "md_h3")
                continue
            if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
                widget.insert(tk.END, "─" * 28 + "\n", "md_hr")
                continue
            m_quote = re.match(r"^>\s?(.*)$", stripped)
            if m_quote:
                widget.insert(tk.END, "▍ ", "md_quote_bar")
                self._render_inline(widget, m_quote.group(1), "md_quote")
                widget.insert(tk.END, "\n", "md_quote")
                continue
            m_bullet = re.match(r"^[-*+]\s+(.*)$", stripped)
            if m_bullet:
                widget.insert(tk.END, "  • ", "content")
                self._render_inline(widget, m_bullet.group(1))
                widget.insert(tk.END, "\n", "content")
                continue
            m_num = re.match(r"^(\d+[.)])\s+(.*)$", stripped)
            if m_num:
                widget.insert(tk.END, f"  {m_num.group(1)} ", "content")
                self._render_inline(widget, m_num.group(2))
                widget.insert(tk.END, "\n", "content")
                continue
            self._render_inline(widget, stripped)
            widget.insert(tk.END, "\n", "content")

    def _render_code(self, widget, code, lang):
        widget.insert(tk.END, f"  {lang or 'code'}\n", "code_lang")
        for line in code.splitlines():
            self._render_code_line(widget, line + "\n")
        widget.insert(tk.END, "\n", "content")

    def _render_code_line(self, widget, line):
        pos = 0
        for m in self._CODE_RE.finditer(line):
            if m.start() > pos:
                widget.insert(tk.END, line[pos:m.start()], "code_block")
            tok = m.group(0)
            if m.group(1):
                tag = "code_com"
            elif m.group(2):
                tag = "code_str"
            elif m.group(3) and tok in self._KEYWORDS:
                tag = "code_kw"
            elif m.group(4):
                tag = "code_num"
            else:
                tag = "code_block"
            widget.insert(tk.END, tok, tag)
            pos = m.end()
        if pos < len(line):
            widget.insert(tk.END, line[pos:], "code_block")

    # ---------- 行内 ----------
    def _render_inline(self, widget, text, base_tag="content"):
        text, mapping = self._mask_formulas(text)
        pos = 0
        for m in self._INLINE_RE.finditer(text):
            if m.start() > pos:
                widget.insert(tk.END, text[pos:m.start()], base_tag)
            tok = m.group(0)
            if m.group("code"):
                widget.insert(tk.END, tok[1:-1], "md_code")
            elif m.group("bold"):
                widget.insert(tk.END, tok[2:-2], "md_bold")
            elif m.group("italic"):
                widget.insert(tk.END, tok[1:-1], "md_italic")
            elif m.group("link"):
                label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", tok).groups()
                start = widget.index(tk.END)
                widget.insert(tk.END, label, "md_link")
                self._bind_link(widget, start, url)
            elif m.group("ph"):
                raw = mapping.get(tok)
                if raw:
                    self.app.insert_formula(widget, raw)
                else:
                    widget.insert(tk.END, tok, base_tag)
            pos = m.end()
        if pos < len(text):
            widget.insert(tk.END, text[pos:], base_tag)

    def _mask_formulas(self, text):
        try:
            segments = find_latex_segments(text)
        except Exception:
            return text, {}
        if not segments:
            return text, {}
        out = []
        mapping = {}
        pos = 0
        for start, end, raw in segments:
            out.append(text[pos:start])
            ph = chr(0xE000 + len(mapping))
            mapping[ph] = raw
            out.append(ph)
            pos = end
        out.append(text[pos:])
        return "".join(out), mapping

    def _bind_link(self, widget, start, url):
        tag = f"link_{id(url)}_{widget.index(start).replace('.', '_')}"
        widget.tag_add(tag, start, "end-1c")
        widget.tag_config(tag, foreground=C_PRIMARY, underline=True)

        def open_url(_e, u=url):
            try:
                import webbrowser
                webbrowser.open(u)
            except Exception:
                log_exc("打开链接失败")

        widget.tag_bind(tag, "<Button-1>", open_url)
        widget.tag_bind(tag, "<Enter>", lambda e: widget.config(cursor="hand2"))
        widget.tag_bind(tag, "<Leave>", lambda e: widget.config(cursor=""))

    # ---------- 操作条 ----------
    def _insert_actions(self, widget, cid, idx, content):
        self._ensure_newline(widget)
        bar = tk.Frame(widget, bg=C_BG_CHAT)
        actions = (("复制", lambda c=content: self.app.copy_text(c)),
                   ("重新生成", lambda: self.app.regenerate(cid, idx)))
        for text, cmd in actions:
            lbl = tk.Label(bar, text=text, bg=C_BG_CHAT, fg=C_TEXT_MUTED,
                           font=(FONT_UI, 8), cursor="hand2", padx=8, pady=2)
            lbl.pack(side=tk.LEFT, padx=(0, 8))
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=C_PRIMARY))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=C_TEXT_MUTED))
            lbl.bind("<Button-1>", lambda e, f=cmd: f())
        widget.window_create(tk.END, window=bar, padx=2, pady=6)
        # 操作条嵌在 Text 里，让滚轮穿透给聊天区
        bind_wheel_all(bar, self.app.chat_area)
        widget.mark_set(tk.INSERT, tk.END)


# ============ 组件：底部输入区 ============
class MarkdownStream:
    """流式 Markdown 渲染：完整行增量输出，未完成的最后一行局部重绘。"""

    def __init__(self, renderer, widget):
        self.r = renderer
        self.w = widget
        self.buf = ""
        self.in_code = False
        self.in_formula = False
        self.formula_buf = []
        self.tail_start = None

    # ---- 对外 ----
    def feed(self, text):
        """只渲染已经完整的行；未完成的最后一行留到换行或 finish 时再渲染。

        这样是纯追加写入，不需要回删，天然不会重复。
        """
        if not text:
            return
        self.buf += text
        if "\n" not in self.buf:
            return
        parts = self.buf.split("\n")
        self.buf = parts.pop()
        for line in parts:
            self._render_line(line)

    def finish(self):
        if self.buf:
            self._clear_tail()
            self._render_line(self.buf)
            self.buf = ""

    # ---- 内部 ----
    def _clear_tail(self):
        if self.tail_start:
            try:
                self.w.delete(self.tail_start, tk.END)
            except tk.TclError:
                pass
            self.tail_start = None

    def _tail_anchor(self):
        """插入点：结尾是换行时在 end-1c，否则在 end。"""
        try:
            last = self.w.get("end-2c", "end-1c")
        except tk.TclError:
            last = ""
        return self.w.index("end-1c" if last == "\n" else "end")

    def _render_tail(self):
        if not self.buf:
            return
        try:
            self.tail_start = self._tail_anchor()
            self.r._render_inline(self.w, self.buf)
        except tk.TclError:
            self.tail_start = None

    def _render_line(self, line):
        stripped = line.strip()
        try:
            if self.in_formula:
                self.formula_buf.append(line)
                if stripped.endswith("$$"):
                    body = "\n".join(self.formula_buf)
                    self._emit_block_formula(body)
                    self.in_formula = False
                    self.formula_buf = []
                return
            if stripped.startswith("$$"):
                if stripped.endswith("$$") and len(stripped) > 4:
                    self.r._render_block_formula(self.w, stripped[2:-2])
                else:
                    self.in_formula = True
                    self.formula_buf = [stripped[2:]]
                return
            if stripped.startswith("```"):
                if self.in_code:
                    self.in_code = False
                    self.w.insert(tk.END, "\n", "content")
                else:
                    self.in_code = True
                    self.w.insert(tk.END, f"  {stripped[3:].strip() or 'code'}\n",
                                  "code_lang")
                return
            if self.in_code:
                self.r._render_code_line(self.w, line + "\n")
                return
            self.r._render_text_lines(self.w, line)
        except tk.TclError:
            pass

    def _emit_block_formula(self, body):
        latex = body.strip()
        if latex.endswith("$$"):
            latex = latex[:-2]
        if latex.startswith("$$"):
            latex = latex[2:]
        self.r._render_block_formula(self.w, latex)
class AttachButton(tk.Canvas):
    """圆角方形「回形针」附件键。"""

    def __init__(self, parent, command, size=34):
        super().__init__(parent, width=size, height=size, bg=C_BG_MAIN,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.size = size
        self.command = command
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: command())

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.size
        bg = C_PRIMARY_SOFT if self._hover else C_BG_MAIN
        fg = C_PRIMARY if self._hover else C_TEXT_MUTED
        draw_round_rect(self, 1, 1, s - 1, s - 1, 9, bg,
                        C_PRIMARY if self._hover else C_BORDER, 1)
        # 文件 + 加号：明确的「添加附件」语义
        draw_round_rect(self, 8, 8, 20, 26, 3, "", fg, 2)
        self.create_line(11, 13, 17, 13, fill=fg, width=1)
        self.create_line(11, 17, 17, 17, fill=fg, width=1)
        self.create_line(25, 20, 25, 27, fill=fg, width=2,
                         capstyle=tk.ROUND)
        self.create_line(21.5, 23.5, 28.5, 23.5, fill=fg, width=2,
                         capstyle=tk.ROUND)


class Composer(tk.Frame):
    """多行输入 + 发送 + 附件 + 深度思考 / 智能搜索开关。"""

    MAX_FILES = 5
    MAX_TEXT_BYTES = 200_000

    def __init__(self, parent, app):
        super().__init__(parent, bg=C_BG_MAIN)
        self.app = app
        self.attachments = []
        self.web_search = tk.BooleanVar(value=False)
        self.deep_think = tk.BooleanVar(value=False)
        self._placeholder_on = True
        self._ctrl_send = False
        self._placeholder_text = "输入消息，Enter 发送，Shift+Enter 换行…"
        self._enabled = True
        self._build()

    # ---------- UI ----------
    def _build(self):
        self.chips = tk.Frame(self, bg=C_BG_MAIN)
        self.chips.pack(fill=tk.X, padx=20, pady=(0, 4))

        wrap = tk.Frame(self, bg=C_BG_INPUT)
        wrap.pack(fill=tk.X, padx=20)
        self.text = tk.Text(wrap, height=3, wrap=tk.WORD, bd=0,
                            relief=tk.FLAT, font=(FONT_UI, 11),
                            bg=C_BG_INPUT, fg=C_TEXT_MUTED,
                            insertbackground=C_PRIMARY, padx=14, pady=10,
                            spacing1=1, spacing3=2)
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.insert("1.0", self._placeholder_text)
        self.text.bind("<FocusIn>", self._on_focus_in)
        self.text.bind("<FocusOut>", self._on_focus_out)
        self.text.bind("<Return>", self._on_return)
        self.text.bind("<Shift-Return>", self._on_newline)
        self.text.bind("<Control-Return>", self._on_ctrl_return)

        bar = tk.Frame(self, bg=C_BG_MAIN)
        bar.pack(fill=tk.X, padx=20, pady=(8, 14))

        self.attach_btn = AttachButton(bar, self.pick_files)
        self.attach_btn.pack(side=tk.LEFT)

        self.think_pill = PillToggle(bar, "深度思考", "think", self._toggle_think)
        self.search_pill = PillToggle(bar, "智能搜索", "globe", self._toggle_search)
        self.think_pill.pack(side=tk.LEFT, padx=(8, 0))
        self.search_pill.pack(side=tk.LEFT, padx=(8, 0))

        self.hint = tk.Label(bar, text="Enter 发送 · Shift+Enter 换行",
                             bg=C_BG_MAIN, fg=C_TEXT_MUTED,
                             font=(FONT_UI, 8))
        self.hint.pack(side=tk.LEFT, padx=(12, 0))

        self.gen_box = tk.Frame(bar, bg=C_BG_MAIN)
        self.stop_btn = make_rounded_button(
            self.gen_box, "停止生成", self.app.stop_generation, bg=C_BG_INPUT,
            fg=C_DELETE, hover_bg="#fee2e2", font=(FONT_UI, 9), width=88)
        self.stop_btn.pack(side=tk.LEFT)

        self.send_btn = make_rounded_button(
            bar, "发送", self.app.send_message, bg=C_PRIMARY,
            hover_bg=C_PRIMARY_HOVER, font=(FONT_UI, 10, "bold"))
        self.send_btn.pack(side=tk.RIGHT)

        # 推理强度：仅在模型支持时显示在输入栏下方
        self.reason_row = tk.Frame(self, bg=C_BG_MAIN)
        self._reason_holder = [getattr(self.app, "reasoning_level", "默认")]
        self._reason_group = None
        self._sync_reason_row()

    def _sync_reason_row(self):
        cfg = self.app.store.current_cfg()
        conf = REASONING_CONFIG.get(cfg.get("id"))
        for w in self.reason_row.winfo_children():
            w.destroy()
        self._reason_group = None
        if not conf:
            self.reason_row.pack_forget()
            return
        levels = conf["levels"]
        if self._reason_holder[0] not in levels:
            self._reason_holder[0] = levels[0]
        Label(self.reason_row, text="推理强度", bg=C_BG_MAIN, fg=C_TEXT_MUTED,
              font=(FONT_UI, 8)).pack(side=tk.LEFT)
        self._reason_group = make_pill_group(
            self.reason_row, levels, self._reason_holder, self._on_reason_change)
        self._reason_group.pack(side=tk.LEFT, padx=(8, 0))
        self.reason_row.pack(fill=tk.X, padx=20, pady=(0, 6))

    def _on_reason_change(self, level):
        self.app.reasoning_level = level
        self.app.save_setting("reasoning_level", level)

    def set_generating(self, on):
        try:
            if on:
                self.gen_box.pack(side=tk.RIGHT, padx=(0, 8))
            else:
                self.gen_box.pack_forget()
        except Exception:
            pass

    def _icon_action(self, parent, glyph, command, tooltip=""):
        cv = tk.Canvas(parent, width=34, height=34, bg=C_BG_MAIN,
                       highlightthickness=0, bd=0, cursor="hand2")
        state = {"hover": False}

        def draw():
            cv.delete("all")
            if state["hover"]:
                cv.create_oval(1, 1, 33, 33, fill=C_PRIMARY_SOFT, outline="")
            cv.create_text(17, 17, text=glyph, fill=C_TEXT_MUTED,
                           font=(FONT_UI, 11))

        draw()
        cv.bind("<Enter>", lambda e: (state.__setitem__("hover", True), draw()))
        cv.bind("<Leave>", lambda e: (state.__setitem__("hover", False), draw()))
        cv.bind("<Button-1>", lambda e: command())
        return cv

    # ---------- 文本 ----------
    def _on_focus_in(self, _e):
        if self._placeholder_on:
            self._placeholder_on = False
            self.text.delete("1.0", tk.END)
            self.text.configure(fg=C_TEXT_DARK)

    def _on_focus_out(self, _e):
        if not self.text.get("1.0", "end-1c").strip():
            self._show_placeholder()

    def _show_placeholder(self):
        self._placeholder_on = True
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", self._placeholder_text)
        self.text.configure(fg=C_TEXT_MUTED)

    def _on_return(self, _e):
        if getattr(self, "_ctrl_send", False):
            self.text.insert(tk.INSERT, "\n")
            return "break"
        self.app.send_message()
        return "break"

    def _on_ctrl_return(self, _e):
        self.app.send_message()
        return "break"

    def _on_newline(self, _e):
        self.text.insert(tk.INSERT, "\n")
        return "break"

    def set_send_mode(self, ctrl_enter):
        """ctrl_enter=True：Ctrl+Enter 发送，Enter 换行。"""
        self._ctrl_send = bool(ctrl_enter)
        if ctrl_enter:
            self.hint.config(text="Ctrl+Enter 发送 · Enter 换行")
            self._set_placeholder("输入消息，Ctrl+Enter 发送，Enter 换行…")
        else:
            self.hint.config(text="Enter 发送 · Shift+Enter 换行")
            self._set_placeholder("输入消息，Enter 发送，Shift+Enter 换行…")

    def _set_placeholder(self, text):
        self._placeholder_text = text
        if self._placeholder_on:
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", text)

    def get_text(self):
        if self._placeholder_on:
            return ""
        return self.text.get("1.0", "end-1c").strip()

    def clear_text(self):
        self.text.delete("1.0", tk.END)
        self._show_placeholder()

    def set_text(self, text):
        """把已有内容放回输入框（编辑上一条提问用）。"""
        self._placeholder_on = False
        self.text.configure(fg=C_TEXT_DARK)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)
        self.text.mark_set("insert", "end-1c")
        try:
            self.text.see("end")
        except tk.TclError:
            pass

    def set_enabled(self, enabled):
        if getattr(self, "read_only", False):
            return
        self._enabled = enabled
        self.send_btn.set_enabled(enabled, "发送" if enabled else "生成中")

    def set_readonly(self, on, model_name=""):
        """查看其他模型的对话时，输入区变为只读。"""
        self.read_only = bool(on)
        try:
            if on:
                self.text.configure(state=tk.NORMAL)
                self.text.delete("1.0", tk.END)
                self.text.insert(
                    "1.0", f"只读查看：{model_name} 的对话（切换到该模型后可继续）")
                self.text.configure(state=tk.DISABLED, fg=C_TEXT_MUTED)
                self._placeholder_on = True
                self.send_btn.set_enabled(False, "只读")
                self.gen_box.pack_forget()
            else:
                self.text.configure(state=tk.NORMAL)
                self.text.configure(fg=C_TEXT_MUTED)
                self._placeholder_on = True
                self._show_placeholder()
                self._enabled = True
                self.send_btn.set_enabled(True, "发送")
        except Exception as exc:
            log_exc(f"set_readonly 失败: {exc}")

    def focus_input(self):
        self.text.focus_set()

    # ---------- 附件 ----------
    def pick_files(self):
        paths = filedialog.askopenfilenames(
            parent=self,
            title="选择要添加的文件",
            filetypes=[("文本 / 代码", "*.txt *.md *.py *.json *.csv *.log"),
                       ("图片", "*.png *.jpg *.jpeg *.webp *.gif"),
                       ("所有文件", "*.*")])
        for p in paths or ():
            if len(self.attachments) >= self.MAX_FILES:
                messagebox.showinfo("提示", f"一次最多添加 {self.MAX_FILES} 个文件",
                                    parent=self)
                break
            if any(a["path"] == p for a in self.attachments):
                continue
            self.attachments.append({"path": p,
                                     "name": os.path.basename(p)})
        self._render_chips()

    def _render_chips(self):
        for w in self.chips.winfo_children():
            w.destroy()
        for idx, att in enumerate(self.attachments):
            chip = tk.Frame(self.chips, bg=C_PRIMARY_SOFT, cursor="hand2")
            chip.pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(chip, text=f"📎 {att['name'][:28]}", bg=C_PRIMARY_SOFT,
                     fg=C_PRIMARY, font=(FONT_UI, 8)).pack(side=tk.LEFT,
                                                          padx=(8, 4), pady=3)
            close = tk.Label(chip, text="✕", bg=C_PRIMARY_SOFT, fg=C_TEXT_MUTED,
                             font=(FONT_UI, 8), cursor="hand2")
            close.pack(side=tk.LEFT, padx=(0, 6))
            close.bind("<Button-1>", lambda e, i=idx: self.remove_attachment(i))

    def remove_attachment(self, idx):
        if 0 <= idx < len(self.attachments):
            del self.attachments[idx]
            self._render_chips()

    def take_attachments(self):
        items = list(self.attachments)
        self.attachments = []
        self._render_chips()
        return items

    def attachment_block(self, att):
        """把附件转成随消息发送的文本块（图片仅作本地引用）。"""
        path = att["path"]
        name = att["name"]
        ext = os.path.splitext(name)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            return f"[图片附件: {name}]（本地文件，当前模型不支持图片输入）"
        try:
            size = os.path.getsize(path)
            if size > self.MAX_TEXT_BYTES:
                return f"[附件: {name}]（文件过大，未读取内容）"
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                body = f.read(60_000)
            return f"[附件: {name}]\n```text\n{body}\n```"
        except Exception:
            return f"[附件: {name}]（读取失败）"

    # ---------- 开关：深度思考 / 智能搜索 ----------
    def _toggle_search(self):
        self.web_search.set(not self.web_search.get())
        self.search_pill.set_on(self.web_search.get())

    def _toggle_think(self):
        if not self.app.store.current_cfg().get("thinking"):
            return
        self.deep_think.set(not self.deep_think.get())
        self.think_pill.set_on(self.deep_think.get())

    def is_web_search_on(self):
        return bool(self.web_search.get())

    def is_deep_think_on(self):
        return bool(self.deep_think.get())

    def update_capabilities(self):
        """按当前模型决定是否显示「深度思考」开关。"""
        try:
            supported = bool(self.app.store.current_cfg().get("thinking"))
        except Exception:
            supported = False
        if supported:
            if not self.think_pill.winfo_ismapped():
                self.think_pill.pack(side=tk.LEFT, padx=(8, 0),
                                     before=self.search_pill)
        else:
            if self.think_pill.winfo_ismapped():
                self.think_pill.pack_forget()
            self.deep_think.set(False)
            self.think_pill.set_on(False)
        try:
            self._sync_reason_row()
        except Exception:
            pass


class PillToggle(tk.Canvas):
    """输入区开关胶囊：图标 + 文案，开启时蓝色描边（参考图样式）。"""

    def __init__(self, parent, text, icon, command, bg=C_BG_MAIN):
        super().__init__(parent, height=32, bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        self.text = text
        self.icon = icon
        self.command = command
        self.on = False
        self._hover = False
        self._pill_w = max(104, tkfont.Font(family=FONT_UI, size=9).measure(text) + 52)
        self.configure(width=self._pill_w)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: command())

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def set_on(self, on):
        self.on = bool(on)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 20:
            return
        h = 32
        if self.on:
            bg, border, fg = C_PRIMARY_SOFT, C_PRIMARY, C_PRIMARY
        elif self._hover:
            bg, border, fg = C_BG_INPUT, C_BORDER, C_TEXT_DARK
        else:
            bg, border, fg = C_BG_MAIN, C_BORDER, C_TEXT_MUTED
        draw_round_rect(self, 1, 1, w - 2, h - 2, (h - 4) // 2, bg, border, 1)
        self._draw_icon(17, h / 2, fg)
        self.create_text(30, h / 2, anchor="w", text=self.text, fill=fg,
                         font=(FONT_UI, 9, "bold" if self.on else "normal"))

    def _draw_icon(self, cx, cy, color):
        if self.icon == "globe":
            r = 6
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline=color, width=1.3)
            self.create_line(cx - r, cy, cx + r, cy, fill=color, width=1.2)
            self.create_oval(cx - 2.6, cy - r, cx + 2.6, cy + r,
                             outline=color, width=1.2)
            self.create_line(cx, cy - r, cx, cy + r, fill=color, width=1.2)
        else:  # think：原子状图标
            self.create_oval(cx - 3.2, cy - 3.2, cx + 3.2, cy + 3.2,
                             outline=color, width=1.4)
            self.create_oval(cx - 6.6, cy - 2.6, cx + 6.6, cy + 2.6,
                             outline=color, width=1.1)
            self.create_oval(cx - 2.6, cy - 6.6, cx + 2.6, cy + 6.6,
                             outline=color, width=1.1)


# ============ 余额查询（仅 DeepSeek 提供公开接口） ============
BALANCE_ENDPOINTS = {
    "deepseek-flash": "https://api.deepseek.com/user/balance",
    "deepseek-chat": "https://api.deepseek.com/user/balance",
    "deepseek-reasoner": "https://api.deepseek.com/user/balance",
}
BALANCE_RE = re.compile(r"(余额|额度|balance|还剩|剩余)", re.I)


def query_balance(cfg, api_key, timeout=8):
    """查询服务商账户余额；未提供公开接口的厂商返回说明。"""
    url = BALANCE_ENDPOINTS.get(cfg.get("id"))
    if not url:
        return {"ok": False,
                "msg": f"{cfg.get('vendor', '该服务商')} 目前没有提供公开的余额查询接口。"}
    if not api_key:
        return {"ok": False, "msg": "当前模型还没有导入 API Key。"}
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {api_key}",
                      "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "msg": f"余额查询失败：{e}"}
    infos = data.get("balance_infos") or []
    if not infos:
        return {"ok": False, "msg": "接口没有返回余额信息。"}
    lines = [f"可用状态：{'正常' if data.get('is_available') else '不可用'}"]
    for info in infos:
        cur = info.get("currency", "")
        sym = {"CNY": "¥", "USD": "$"}.get(cur, f"{cur} ")
        lines.append(f"总余额：{sym}{info.get('total_balance', '0')}")
        lines.append(f"　赠送余额：{sym}{info.get('granted_balance', '0')}")
        lines.append(f"　充值余额：{sym}{info.get('topped_up_balance', '0')}")
    return {"ok": True, "text": "\n".join(lines)}


# ============ 联网搜索（可选，失败静默降级） ============
class WebSearch:
    """轻量搜索：无第三方依赖，4 秒超时，失败返回空列表，不影响主流程。"""

    @staticmethod
    def search(query, timeout=4.0, limit=5):
        query = (query or "").strip()
        if not query:
            return []
        try:
            req = urllib.request.Request(
                "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query),
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            log_info(f"[搜索] 请求失败: {e}")
            return []
        results = []
        try:
            for m in re.finditer(
                    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                    html, re.DOTALL):
                url = m.group(1)
                title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                if url.startswith("//duckduckgo.com/l/?uddg="):
                    url = urllib.parse.unquote(
                        urllib.parse.parse_qs(urllib.parse.urlparse("https:" + url).query)
                        .get("uddg", [url])[0])
                results.append({"title": title, "url": url, "snippet": ""})
                if len(results) >= limit:
                    break
        except Exception:
            return []
        return results


# ============ 主窗口 ============
class ChatApp:
    def __init__(self, root, store):
        self.root = root
        self.store = store
        self.root.title(f"{APP_NAME} {APP_VERSION_PUBLIC}")
        self.root.minsize(900, 640)
        self.root.configure(bg=C_BG_MAIN)
        self._apply_window_limits()

        self.data = load_data()
        if not self.data["conversations"]:
            cid = str(uuid.uuid4())
            self.data["conversations"][cid] = make_new_conversation_dict(
                self.store.current)
            self.data["current_id"] = cid
        if (not self.data.get("current_id")
                or self.data["current_id"] not in self.data["conversations"]):
            self.data["current_id"] = next(iter(self.data["conversations"]))

        self.sidebar_widgets = {}
        self._last_scrollregion = None
        self._pending = {}
        self._generating_cid = None
        self._autoscroll_enabled = True
        self._scroll_positions = {}
        self._last_file_mtime = self._get_file_mtime()
        self._suppress_scroll_save = False
        self._warmup_cid = None
        self._latex_image_refs = []
        self._photo_cache = {}

        # 设置项（落盘 settings.json）
        self.settings = load_settings()
        # 兼容旧数据：缺失 model_id 的对话统一归到默认模型，避免跟着当前模型漂移
        try:
            changed = False
            for _c in self.data.get("conversations", {}).values():
                if not _c.get("model_id"):
                    _c["model_id"] = DEFAULT_MODEL_ID
                    changed = True
            if changed:
                self._save_data()
        except Exception:
            pass
        try:
            self.chat_font_size = max(9, min(18, int(self.settings.get("font_size", 11))))
        except Exception:
            self.chat_font_size = 11
        try:
            self.type_interval_ms = max(0, int(self.settings.get(
                "type_speed", TYPE_INTERVAL_MS)))
        except Exception:
            self.type_interval_ms = TYPE_INTERVAL_MS
        self.send_with_ctrl = bool(self.settings.get("send_with_ctrl", False))
        self.show_reasoning = bool(self.settings.get("show_reasoning", False))
        self.password_required = bool(self.settings.get("password_required", True))
        self.reasoning_level = self.settings.get("reasoning_level", "默认")
        self._expanded_reasoning = set()
        self._think_lines = {}
        self._regen_lines = {}
        self._edit_lines = {}
        self._stop_flags = set()

        self.renderer = MessageRenderer(self)
        self.build_ui()
        self.composer.set_send_mode(self.send_with_ctrl)
        self._bind_scroll_watch()
        self.refresh_sidebar(full=True)
        self.load_conversation(self.data["current_id"])

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._schedule_file_check()

    # ---------- 窗口 ----------
    def _apply_window_limits(self):
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.root.maxsize(sw, sh)
            w = min(1180, sw - 60)
            h = min(800, sh - 80)
            x = (sw - w) // 2
            y = (sh - h) // 2
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    # ---------- 模型 / API ----------
    def open_model_picker(self):
        try:
            ModelPickerDialog(self)
        except Exception:
            log_exc("打开模型列表失败")

    def open_api_dialog(self, mid=None):
        try:
            ApiKeyDialog(self, mid or self.store.current,
                         on_done=self.on_model_config_changed)
        except Exception:
            log_exc("打开 API 窗口失败")

    def open_api_manager(self):
        """菜单 →「模型」：集中修改 / 导入各模型的 API Key。"""
        try:
            ApiManagerDialog(self)
        except Exception:
            log_exc("打开 API 管理窗口失败")

    def open_help(self):
        try:
            HelpWindow(self.root)
        except Exception:
            log_exc("打开使用教程失败")

    def open_settings(self):
        try:
            SettingsDialog(self)
        except Exception:
            log_exc("打开设置失败")

    def open_export(self):
        try:
            ExportDialog(self)
        except Exception:
            log_exc("打开导出窗口失败")

    def save_setting(self, key, value):
        self.settings[key] = value
        try:
            save_settings(self.settings)
        except Exception:
            log_exc("保存设置失败")

    def _on_chat_click(self, event):
        """点击「已深度思考」那一行时展开 / 收起推理。"""
        try:
            line = int(self.chat_area.index(f"@{event.x},{event.y}").split(".")[0])
        except Exception:
            return
        cid = self.data.get("current_id")
        for (c, i), ln in list(self._edit_lines.items()):
            if c == cid and ln == line:
                self.edit_last_question(c)
                return "break"
        for (c, i), ln in list(self._regen_lines.items()):
            if c == cid and ln == line:
                if i < 0:
                    self.regenerate_last(c)
                else:
                    self.regenerate(c, i)
                return "break"
        for (c, i), ln in list(self._think_lines.items()):
            if c == cid and ln == line:
                self.toggle_reasoning(c, i)
                return "break"

    def toggle_reasoning(self, cid, idx):
        key = (cid, idx)
        if key in self._expanded_reasoning:
            self._expanded_reasoning.discard(key)
        else:
            self._expanded_reasoning.add(key)
        try:
            self.load_conversation(cid)
        except Exception:
            log_exc("切换推理过程失败")

    def apply_chat_font(self, size):
        try:
            size = max(9, min(18, int(size)))
        except Exception:
            return
        self.chat_font_size = size
        self.save_setting("font_size", size)
        try:
            self._configure_chat_tags()
            self.load_conversation(self.data["current_id"])
        except Exception:
            log_exc("应用字号失败")

    def switch_model(self, mid):
        if self._generating_cid is not None:
            messagebox.showinfo("提示", "正在生成回答，请稍后再切换模型", parent=self.root)
            return False
        if not self.store.configured(mid):
            return False
        if mid == self.store.current:
            return True
        if not self.store.set_current(mid):
            return False
        self.on_model_config_changed()
        try:
            conv = self.current_conv()
            conv["model_id"] = mid
            self._save_data()
        except Exception:
            log_exc("切换模型后记录失败")
        log_info(f"切换模型 -> {self.store.current_cfg()['name']}")
        return True

    def on_model_config_changed(self):
        try:
            self.nav.refresh()
        except Exception:
            pass
        try:
            cfg = self.store.current_cfg()
            sub = f"{cfg.get('vendor', '')} · {cfg.get('version', '')}".strip(" ·")
            note = "" if self.store.configured(cfg["id"]) else "未配置"
            self.model_card.set_model(model_title(cfg), sub, note)
        except Exception:
            pass
        try:
            self.history_scope = "current"
            self.refresh_sidebar(full=True)
        except Exception:
            pass
        try:
            self._sync_conversation_to_model()
        except Exception:
            log_exc("切换模型后同步对话失败")
        try:
            self.update_usage_bar()
            self.update_context_chip()
        except Exception:
            pass
        try:
            self.composer.update_capabilities()
        except Exception:
            pass
        self.root.title(f"{APP_NAME} {APP_VERSION_PUBLIC}")

    def _open_about(self):
        try:
            AboutDialog(self.root, self)
        except Exception:
            log_exc("打开关于窗口失败")

    def _get_file_mtime(self):
        try:
            return os.path.getmtime(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else 0
        except Exception:
            return 0

    def _save_data(self):
        try:
            save_data(self.data)
            try:
                self._last_file_mtime = os.path.getmtime(HISTORY_FILE)
            except Exception:
                self._last_file_mtime = 0
        except Exception:
            log_exc("save_data failed")

    def _schedule_file_check(self):
        try: self._check_file_changed()
        except Exception: pass
        try: self.root.after(FILE_CHECK_INTERVAL_MS, self._schedule_file_check)
        except tk.TclError: pass

    def _check_file_changed(self):
        if self._generating_cid is not None:
            return
        mtime = self._get_file_mtime()
        if mtime == self._last_file_mtime:
            return
        try:
            new_data = load_data(strict=True)
        except Exception:
            return
        if not isinstance(new_data, dict) or "conversations" not in new_data:
            return
        self._last_file_mtime = mtime
        self.data = new_data
        self._scroll_positions.clear()
        if (not self.data.get("current_id")
                or self.data["current_id"] not in self.data["conversations"]):
            if self.data["conversations"]:
                self.data["current_id"] = next(iter(self.data["conversations"]))
            else:
                cid = str(uuid.uuid4())
                self.data["conversations"][cid] = make_new_conversation_dict(self.store.current)
                self.data["current_id"] = cid
        for cid, state in list(self._pending.items()):
            for key in ("timer", "think_timer", "safety_timer", "reason_timer"):
                t = state.get(key)
                if t is not None:
                    try: self.root.after_cancel(t)
                    except Exception: pass
        self._pending.clear()
        self._generating_cid = None
        self._set_send_enabled(True)
        self.refresh_sidebar(full=True)
        self.load_conversation(self.data["current_id"])
        self._update_floating_visibility()

    def ai_full_summary(self, messages, limit=TITLE_MAX):
        client = self.store.client()
        if client is None:
            return None
        dialog = build_dialog_text(messages)
        if not dialog: return None
        prompt = ("用不超过15个字的中文短语概括下面这段对话的主题。"
                  "只输出概括本身，不要标点、不要引号、不要解释。\n\n"
                  f"{dialog}\n\n概括：")
        for attempt in range(TITLE_RETRY + 1):
            try:
                resp = client.chat.completions.create(
                    model=self.store.current_cfg()["api_model"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3, max_tokens=200, timeout=30)
                raw = resp.choices[0].message.content
                title = _extract_title(raw)
                if title: return title
            except Exception as e:
                log_exc(f"[标题] 第{attempt+1}次异常: {e}")
        return None

    def build_ui(self):
        sidebar_w = 250
        self.sidebar = Frame(self.root, width=sidebar_w, bg=C_BG_SIDEBAR)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        header = Frame(self.sidebar, bg=C_BG_SIDEBAR)
        header.pack(fill=tk.X, padx=16, pady=(18, 12))
        Label(header, text="当前模型", bg=C_BG_SIDEBAR, fg=C_TEXT_MUTED,
              font=(FONT_UI, 8), anchor="w").pack(fill=tk.X)
        self.model_card = SidebarModelCard(header, self.open_model_picker)
        self.model_card.pack(fill=tk.X, pady=(6, 0))

        new_btn = make_rounded_button(
            self.sidebar, "＋   新对话", self.new_conversation,
            bg=C_PRIMARY, hover_bg=C_PRIMARY_HOVER,
            font=(FONT_UI, 10, "bold"))
        new_btn.pack(fill=tk.X, padx=16, pady=(0, 16))

        list_wrap = Frame(self.sidebar, bg=C_BG_SIDEBAR)
        list_wrap.pack(fill=tk.BOTH, expand=True, padx=(10, 6), pady=(0, 12))

        self.history_canvas = tk.Canvas(list_wrap, bg=C_BG_SIDEBAR,
                                        highlightthickness=0, bd=0)
        self.history_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(list_wrap, orient=tk.VERTICAL,
                          command=self.history_canvas.yview,
                          width=6, bd=0, relief=tk.FLAT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_canvas.configure(yscrollcommand=sb.set)

        self.history_frame = Frame(self.history_canvas, bg=C_BG_SIDEBAR)
        self.history_canvas.create_window((0, 0), window=self.history_frame,
                                          anchor="nw", tags="inner")

        def on_inner(_e=None):
            bbox = self.history_canvas.bbox("all")
            if bbox and bbox != self._last_scrollregion:
                self.history_canvas.configure(scrollregion=bbox)
                self._last_scrollregion = bbox

        self.history_frame.bind("<Configure>", on_inner)
        self.history_canvas.bind("<Configure>",
                                 lambda e: self.history_canvas.itemconfig("inner", width=e.width))
        bind_wheel_all(self.history_frame, self.history_canvas)

        self.more_bar = tk.Canvas(self.sidebar, height=34, bg=C_BG_SIDEBAR,
                                  highlightthickness=0, bd=0, cursor="hand2")
        self.more_bar.bind("<Button-1>", lambda e: self.toggle_history_scope())
        self.more_bar.bind("<Configure>", lambda e: self._update_more_bar())
        self._more_visible = False
        self.history_scope = "current"

        right = Frame(self.root, bg=C_BG_MAIN)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_pane = right

        # ① 顶部导航栏（汉堡键 + 模型选择区 + 关于）
        self.nav = NavigationBar(right, self)
        self.nav.pack(side=tk.TOP, fill=tk.X)

        # ⑤ 底部输入区
        self.composer = Composer(right, self)
        self.composer.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 6))

        # 用量栏（贴在输入区上方）
        meta_row = Frame(right, bg=C_BG_MAIN)
        meta_row.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=(0, 2))
        self.ctx_chip = Label(meta_row, text="", bg=C_BG_INPUT, fg=C_TEXT_MUTED,
                              font=(FONT_UI, 8), padx=8, pady=1)
        self.ctx_chip.pack(side=tk.LEFT)
        self.usage_bar = Label(meta_row, text="", bg=C_BG_MAIN, fg=C_TEXT_MUTED,
                               font=(FONT_UI, 8), anchor="e")
        self.usage_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # ③ 主对话区
        base_size = self.chat_font_size
        chat_wrap = Frame(right, bg=C_BG_CHAT)
        chat_wrap.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                       padx=20, pady=(12, 10))
        self.chat_wrap = chat_wrap

        self.chat_area = scrolledtext.ScrolledText(
            chat_wrap, wrap=tk.WORD, state=tk.DISABLED,
            font=(FONT_UI, base_size), bg=C_BG_CHAT,
            bd=0, relief=tk.FLAT, padx=24, pady=20,
            insertbackground=C_PRIMARY, spacing1=3, spacing3=8)
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.bind("<Button-1>", self._on_chat_click, add="+")
        self._configure_chat_tags()

        self.floating_down = FloatingRoundButton(
            chat_wrap, self._scroll_to_bottom, size=42)
        self._floating_visible = False
        chat_wrap.bind("<Configure>", self._place_floating_button)
        self.on_model_config_changed()
        self.composer.focus_input()

    def _think_label(self, frame, elapsed=None):
        try:
            thinking = self.composer.is_deep_think_on()
        except Exception:
            thinking = False
        prefix = "正在深度思考" if thinking else "正在思考"
        if elapsed is None:
            return f"{prefix} {frame}"
        return f"{prefix} · {elapsed:.1f}s {frame}"

    def _configure_chat_tags(self):
        """按当前字号配置聊天区全部标签（字号设置会重新调用它）。"""
        base_size = int(self.chat_font_size)
        name_size = max(9, base_size - 1)
        ca = self.chat_area
        ca.configure(font=(FONT_UI, base_size))

        ca.tag_config("name_user", foreground=C_USER,
                      font=(FONT_UI, name_size, "bold"), justify="right")
        ca.tag_config("content_user", foreground=C_TEXT_DARK,
                      font=(FONT_UI, base_size),
                      justify="right", lmargin1=60, lmargin2=60,
                      rmargin=6, spacing1=4, spacing3=4)
        ca.tag_config("name_ai", foreground=C_AI,
                      font=(FONT_UI, name_size, "bold"))
        ca.tag_config("content", foreground=C_TEXT_DARK,
                      font=(FONT_UI, base_size),
                      lmargin1=6, lmargin2=6, rmargin=60,
                      spacing1=4, spacing3=4)
        ca.tag_config("thinking_name", foreground=C_AI,
                      font=(FONT_UI, name_size, "bold"))
        ca.tag_config("thinking_text", foreground=C_THINKING,
                      font=(FONT_UI, name_size, "italic"))
        ca.tag_config("think_done", foreground=C_THINK_DONE,
                      font=(FONT_UI, max(8, base_size - 2), "italic"),
                      spacing1=0, spacing3=0, lmargin1=6, lmargin2=6)
        ca.tag_config("regen_link", foreground="#b45309",
                      font=(FONT_UI, max(8, base_size - 2), "underline"),
                      lmargin1=6, lmargin2=6, spacing1=2, spacing3=6)
        ca.tag_config("think_head", foreground=C_THINK_DONE,
                      font=(FONT_UI, max(8, base_size - 2)),
                      spacing1=4, spacing3=2, lmargin1=6, lmargin2=6)
        ca.tag_config("formula_src", foreground=C_TEXT_DARK,
                      font=(FONT_MONO, max(9, base_size - 1)),
                      lmargin1=6, lmargin2=6)

        ca.tag_config("md_h1", foreground=C_TEXT_DARK,
                      font=(FONT_UI, base_size + 5, "bold"),
                      spacing1=10, spacing3=4)
        ca.tag_config("md_h3", foreground=C_TEXT_DARK,
                      font=(FONT_UI, base_size + 2, "bold"),
                      spacing1=8, spacing3=3)
        ca.tag_config("md_bold", foreground=C_TEXT_DARK,
                      font=(FONT_UI, base_size, "bold"))
        ca.tag_config("md_italic", foreground=C_TEXT_DARK,
                      font=(FONT_UI, base_size, "italic"))
        ca.tag_config("md_code", foreground="#be185d", background=C_CODE_BG,
                      font=(FONT_MONO, max(9, base_size - 1)))
        ca.tag_config("md_link", foreground=C_PRIMARY, underline=True)
        ca.tag_config("md_quote", foreground=C_TEXT_MUTED,
                      font=(FONT_UI, base_size, "italic"),
                      lmargin1=22, lmargin2=22)
        ca.tag_config("md_quote_bar", foreground=C_PRIMARY_LIGHT,
                      font=(FONT_UI, base_size))
        ca.tag_config("md_hr", foreground=C_BORDER)
        ca.tag_config("code_lang", foreground=C_TEXT_MUTED, background=C_CODE_BG,
                      font=(FONT_MONO, 8),
                      lmargin1=10, lmargin2=10, spacing1=6)
        ca.tag_config("code_block", foreground=C_TEXT_DARK, background=C_CODE_BG,
                      font=(FONT_MONO, max(9, base_size - 1)),
                      lmargin1=10, lmargin2=10, spacing1=0, spacing3=0)
        ca.tag_config("code_kw", foreground=C_CODE_KW, background=C_CODE_BG,
                      font=(FONT_MONO, max(9, base_size - 1), "bold"))
        ca.tag_config("code_str", foreground=C_CODE_STR, background=C_CODE_BG,
                      font=(FONT_MONO, max(9, base_size - 1)))
        ca.tag_config("code_com", foreground=C_CODE_COM, background=C_CODE_BG,
                      font=(FONT_MONO, max(9, base_size - 1), "italic"))
        ca.tag_config("code_num", foreground=C_CODE_NUM, background=C_CODE_BG,
                      font=(FONT_MONO, max(9, base_size - 1)))

        # 独立公式块（居中）
        ca.tag_config("formula_block", justify="center", spacing1=8, spacing3=8)
        ca.tag_config("formula_block_text", justify="center",
                      foreground=C_TEXT_DARK, font=(FONT_UI, base_size),
                      lmargin1=40, lmargin2=40, rmargin=40,
                      spacing1=6, spacing3=6)

        # 推理可视化
        ca.tag_config("reasoning_live", foreground="#8a94a6",
                      font=(FONT_UI, max(8, base_size - 2), "italic"),
                      lmargin1=16, lmargin2=16)
        ca.tag_config("reason_head", foreground=C_TEXT_MUTED,
                      font=(FONT_UI, 9, "bold"), spacing1=6)
        ca.tag_config("reason_body", foreground="#7b8494",
                      font=(FONT_UI, max(8, base_size - 2), "italic"),
                      lmargin1=18, lmargin2=18, spacing1=2, spacing3=2)

    def _place_floating_button(self, _e=None):
        try:
            w = self.chat_wrap.winfo_width(); h = self.chat_wrap.winfo_height()
        except tk.TclError:
            return
        if w <= 1 or h <= 1: return
        size = self.floating_down.size
        self.floating_down.place(x=w - size - 24, y=h - size - 16)

    def _scroll_to_bottom(self):
        try:
            self.chat_area.yview_moveto(1.0)
            self._autoscroll_enabled = True
            cid = self.data.get("current_id")
            if cid is not None:
                self._save_scroll_position(cid)
            self._update_floating_visibility()
        except tk.TclError:
            pass

    def _update_floating_visibility(self):
        try:
            first, last = self.chat_area.yview()
            first = float(first); last = float(last)
        except tk.TclError:
            return
        scrollable = (1.0 - first) > 0.001 and (last - first) < 0.999
        at_bottom = last >= 0.999
        generating_here = (self._generating_cid is not None
                           and self._generating_cid == self.data.get("current_id"))
        other_generating = (self._generating_cid is not None and not generating_here)
        if generating_here:
            want_show = True; want_spin = True
        elif other_generating:
            want_spin = False
            want_show = scrollable and not at_bottom
        else:
            want_spin = False
            want_show = scrollable and not at_bottom
        if want_show != self._floating_visible:
            self._floating_visible = want_show
            if want_show:
                self._place_floating_button()
                try: self.floating_down.lift()
                except Exception: pass
            else:
                try: self.floating_down.place_forget()
                except tk.TclError: pass
        try: self.floating_down.set_spinning(want_show and want_spin)
        except Exception: pass

    def _save_scroll_position(self, cid):
        if cid is None or self._suppress_scroll_save:
            return
        try:
            if self._autoscroll_enabled:
                self._scroll_positions[cid] = {"top_index": None, "at_bottom": True}
                return
            self._scroll_positions[cid] = {
                "top_index": self.chat_area.index("@0,0"),
                "at_bottom": False,
            }
        except tk.TclError:
            pass

    def _restore_scroll_position(self, cid):
        saved = self._scroll_positions.get(cid)
        if saved is None or saved.get("at_bottom"):
            try: self.chat_area.yview_moveto(1.0)
            except tk.TclError: pass
            self._autoscroll_enabled = True
            return
        top_idx = saved.get("top_index")
        if not top_idx:
            try: self.chat_area.yview_moveto(1.0)
            except tk.TclError: pass
            self._autoscroll_enabled = True
            return
        try:
            self.chat_area.update_idletasks()
            self.chat_area.index(top_idx)
            self.chat_area.yview(top_idx)
            self._autoscroll_enabled = False
        except tk.TclError:
            try: self.chat_area.yview_moveto(1.0)
            except tk.TclError: pass
            self._autoscroll_enabled = True

    def _force_bottom(self, cid):
        if self.data.get("current_id") != cid: return
        try:
            self.chat_area.yview_moveto(1.0)
            self._autoscroll_enabled = True
            self._update_floating_visibility()
        except tk.TclError:
            pass

    def _force_index(self, cid, top_idx):
        if self.data.get("current_id") != cid: return
        try:
            self.chat_area.index(top_idx)
            self.chat_area.yview(top_idx)
            self._autoscroll_enabled = False
            self._update_floating_visibility()
        except tk.TclError:
            pass

    def _bind_scroll_watch(self):
        orig = self.chat_area.cget("yscrollcommand")

        def combined(first, last):
            if orig:
                try: self.root.tk.call(orig, first, last)
                except Exception: pass
            try:
                self._autoscroll_enabled = (float(last) >= 0.999)
                cid = self.data.get("current_id")
                if cid is not None:
                    self._save_scroll_position(cid)
            except Exception:
                pass
            self._update_floating_visibility()

        self.chat_area.configure(yscrollcommand=combined)
        self.chat_area.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.chat_area.bind("<Button-4>", self._on_mousewheel, add="+")
        self.chat_area.bind("<Button-5>", self._on_mousewheel, add="+")

    def _on_mousewheel(self, event):
        def check():
            try:
                _f, last = self.chat_area.yview()
                self._autoscroll_enabled = (float(last) >= 0.999)
                cid = self.data.get("current_id")
                if cid is not None:
                    self._save_scroll_position(cid)
            except tk.TclError:
                pass
            self._update_floating_visibility()
        self.root.after(30, check)

    def _auto_see_end(self):
        if not self._autoscroll_enabled: return
        try: self.chat_area.yview_moveto(1.0)
        except tk.TclError: pass

    def _ensure_block_start(self):
        """保证新的消息块从新的一行开始（Text 末尾有隐式换行，不能直接 append）。"""
        try:
            last = self.chat_area.get("end-2c", "end-1c")
        except tk.TclError:
            return
        if last != "\n":
            try:
                self.chat_area.insert(tk.END, "\n")
            except tk.TclError:
                pass

    def _insert_user_message(self, content):
        self.chat_area.config(state=tk.NORMAL)
        try:
            self._clear_thinking_tags()
            try: self.chat_area.mark_unset("think_block_start")
            except tk.TclError: pass
            self.chat_area.insert(tk.END, "\n")
            self.chat_area.insert(tk.END, "您\n", "name_user")
            self.chat_area.insert(tk.END, content + "\n\n", "content_user")
        finally:
            try: self.chat_area.config(state=tk.DISABLED)
            except tk.TclError: pass
        self._auto_see_end()

    # ============ 消息操作 ============
    def copy_text(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text or "")
        except Exception:
            log_exc("复制失败")

    def insert_formula(self, widget, raw):
        """供 MessageRenderer 调用的公式插入入口。"""
        self._insert_formula_at_end(widget, raw)

    def edit_last_question(self, cid):
        """把最后一条提问放回输入框，并移除未被采纳的回答。"""
        if getattr(self, "read_only", False):
            return
        if self._generating_cid is not None:
            return
        conv = self.data["conversations"].get(cid)
        if not conv:
            return
        msgs = conv["messages"]
        idx = None
        for i in range(len(msgs) - 1, -1, -1):
            if msgs[i].get("role") == "user":
                idx = i
                break
        if idx is None:
            return
        text = msgs[idx].get("content", "")
        del msgs[idx:]
        conv.pop("summary", None)
        self._save_data()
        self.data["current_id"] = cid
        self.load_conversation(cid)
        self.composer.set_text(text)
        self.composer.focus_input()

    def regenerate_last(self, cid):
        """重新请求最后一条回答；若最后一条是提问（无回答），直接重发。"""
        if self._generating_cid is not None:
            return
        conv = self.data["conversations"].get(cid)
        if not conv:
            return
        msgs = conv["messages"]
        if not msgs:
            return
        if msgs[-1].get("role") == "assistant":
            self.regenerate(cid, len(msgs) - 1)
            return
        if msgs[-1].get("role") != "user":
            return
        self._generating_cid = cid
        self._set_send_enabled(False)
        self._update_floating_visibility()
        self._start_thinking_for(cid)
        threading.Thread(target=self.call_api, args=(cid,), daemon=True).start()

    def regenerate(self, cid, idx):
        if getattr(self, "read_only", False):
            return
        if self._generating_cid is not None:
            messagebox.showinfo("提示", "正在生成回答，请稍候", parent=self.root)
            return
        conv = self.data["conversations"].get(cid)
        if not conv:
            return
        msgs = conv["messages"]
        if not (0 <= idx < len(msgs)) or msgs[idx].get("role") != "assistant":
            return
        if idx < len(msgs) - 1:
            rest = len(msgs) - idx - 1
            if not messagebox.askyesno(
                    "重新生成",
                    f"该回答之后还有 {rest} 条消息，重新生成将一并删除。继续？",
                    parent=self.root):
                return
        del msgs[idx:]
        conv["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._save_data()
        self.data["current_id"] = cid
        self._rebuild_sidebar_active_state()
        self.load_conversation(cid)
        self._generating_cid = cid
        self._set_send_enabled(False)
        self._update_floating_visibility()
        self._start_thinking_for(cid)
        threading.Thread(target=self.call_api, args=(cid,), daemon=True).start()

    # ============ LaTeX 渲染 ============
    def _get_formula_photo(self, latex):
        photo = self._photo_cache.get(latex)
        if photo is not None:
            return photo
        png = render_formula_png(latex)
        if not png: return None
        try:
            import tempfile
            fd, path = tempfile.mkstemp(suffix='.png')
            try:
                os.write(fd, png); os.close(fd); fd = -1
                photo = tk.PhotoImage(file=path)
            finally:
                if fd >= 0:
                    try: os.close(fd)
                    except Exception: pass
                try: os.unlink(path)
                except Exception: pass
        except Exception as e:
            log_info(f"[渲染] PhotoImage失败: {e}")
            return None
        try:
            w, h = photo.width(), photo.height()
        except Exception:
            return None
        if w <= 1 or h <= 1:
            log_info(f"[渲染] 尺寸异常 {w}x{h}: {latex[:40]!r}")
            return None
        self._latex_image_refs.append(photo)
        self._photo_cache[latex] = photo
        return photo

    def _insert_formula_at_end(self, widget, raw):
        try:
            if raw.startswith('\\ce{') and raw.endswith('}'):
                inner = raw[4:-1]
                chem = _chem_to_unicode(inner)
                if chem is not None and chem.strip():
                    widget.insert(tk.END, chem, "content")
                    return
                uni = _math_to_unicode(inner)
                if uni and uni.strip():
                    widget.insert(tk.END, uni, "content")
                    return
                widget.insert(tk.END, raw, "formula_src")
                return

            latex, is_block = _parse_latex_segment(raw)
            if latex is None or not latex.strip():
                widget.insert(tk.END, raw, "content")
                return

            photo = self._get_formula_photo(latex)
            if photo is not None:
                try:
                    widget.image_create(tk.END, image=photo,
                                        align="center", padx=1, pady=1)
                    return
                except tk.TclError as e:
                    log_info(f"[渲染] image_create失败: {e}")

            uni = _math_to_unicode(latex)
            if uni and uni.strip():
                widget.insert(tk.END, uni, "content")
                return

            widget.insert(tk.END, raw, "formula_src")
        except Exception as e:
            log_exc(f"_insert_formula_at_end 异常: {e}")
            try: widget.insert(tk.END, raw, "content")
            except Exception: pass

    def _render_message_at_end(self, widget, content, cid=None, msg_idx=None,
                               reasoning="", expanded=False, think_elapsed=None):
        """统一渲染入口：思考头 + 推理过程 + Markdown + 代码高亮 + 公式 + 操作条。"""
        if not content and not reasoning and think_elapsed is None:
            return
        try:
            self.renderer.render_assistant(widget, content, cid, msg_idx,
                                           reasoning, expanded, think_elapsed)
        except Exception as e:
            log_exc(f"渲染异常，回退原文: {e}")
            try:
                widget.insert(tk.END, content, "content")
            except Exception:
                pass

    def _prepare_latex_images(self, text):
        if not _mpl_ready: return
        try:
            segments = find_latex_segments(text)
        except Exception:
            return
        for _, _, raw in segments:
            if raw.startswith('\\ce{'): continue
            latex, _ = _parse_latex_segment(raw)
            if latex: render_formula_png(latex)

    def _wait_mpl_ready(self, max_seconds=30):
        deadline = time.time() + max_seconds
        while time.time() < deadline:
            if _mpl_ready: return True
            time.sleep(0.2)
        return _mpl_ready

    def _schedule_render_after_warmup(self, cid):
        if self._warmup_cid == cid: return
        self._warmup_cid = cid
        conv = self.data["conversations"].get(cid)
        texts = []
        if conv:
            for m in list(conv["messages"]):
                if m.get("role") == "assistant" and m.get("content"):
                    texts.append(m["content"])

        def worker():
            if not self._wait_mpl_ready(30):
                try: self.root.after(0, lambda: self._on_warmup_failed(cid))
                except tk.TclError: pass
                return
            for t in texts:
                try: self._prepare_latex_images(t)
                except Exception: pass
            try: self.root.after(0, lambda: self._do_reload_after_warmup(cid))
            except tk.TclError: pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_warmup_failed(self, cid):
        if self._warmup_cid == cid:
            self._warmup_cid = None

    def _do_reload_after_warmup(self, cid):
        if self._warmup_cid != cid: return
        self._warmup_cid = None
        if not _mpl_ready: return
        if cid == self.data.get("current_id") and cid not in self._pending:
            self.load_conversation(cid)

    # ============ 思考动画 ============
    def _clear_thinking_tags(self):
        try: self.chat_area.tag_remove("thinking_name", "1.0", "end")
        except tk.TclError: pass
        try: self.chat_area.tag_remove("thinking_text", "1.0", "end")
        except tk.TclError: pass

    def _start_thinking_for(self, cid):
        state = self._ensure_pending(cid)
        state["phase"] = "thinking"
        state["think_frame"] = 0
        state["think_start"] = time.time()
        state["think_elapsed"] = 0.0
        state["queue"] = []
        state["rendered"] = ""
        state["stream_done"] = False
        state["saved"] = False
        state["content_start"] = None
        state["reasoning"] = ""
        state["think_start_idx"] = None
        state["think_line_start"] = None
        state["think_line_end"] = None
        state["think_mode"] = bool(self.composer.is_deep_think_on())
        state["paused"] = False
        state["interrupted"] = False
        state["reason_buf"] = ""
        state["reason_timer"] = None

        if cid == self.data["current_id"]:
            try:
                self.chat_area.config(state=tk.NORMAL)
                try:
                    self._clear_thinking_tags()
                    try:
                        self.chat_area.mark_set("think_block_start", "end")
                        self.chat_area.mark_gravity("think_block_start", tk.LEFT)
                    except tk.TclError: pass
                    state["think_start_idx"] = self.chat_area.index("end")
                    self._ensure_block_start()
                    self.chat_area.insert(tk.END, AI_DISPLAY_NAME + "\n", "thinking_name")
                    line_start = self.chat_area.index("end-1c")
                    state["think_line_start"] = line_start
                    placeholder = self._think_label(THINKING_FRAMES[0], 0.0)
                    self.chat_area.insert(tk.END, placeholder, "thinking_text")
                    line_end = self.chat_area.index("end-1c")
                    state["think_line_end"] = line_end
                    self.chat_area.insert(tk.END, "\n\n", "thinking_text")
                finally:
                    try: self.chat_area.config(state=tk.DISABLED)
                    except tk.TclError: pass
                self._auto_see_end()
            except Exception:
                log_exc("_start_thinking_for 插入失败")

        try:
            state["think_timer"] = self.root.after(
                THINKING_INTERVAL, lambda c=cid: self._tick_thinking_for(c))
        except tk.TclError:
            state["think_timer"] = None
        try:
            state["safety_timer"] = self.root.after(
                SAFETY_TIMEOUT_MS, lambda c=cid: self._on_safety_timeout(c))
        except tk.TclError:
            state["safety_timer"] = None

    def _tick_thinking_for(self, cid):
        state = self._pending.get(cid)
        if state is None or state["phase"] != "thinking": return
        state["think_frame"] = (state["think_frame"] + 1) % len(THINKING_FRAMES)
        if cid == self.data["current_id"]:
            text = self._think_label(THINKING_FRAMES[state["think_frame"]],
                                      time.time() - state["think_start"])
            try:
                was_at_bottom = self._is_at_bottom()
                self.chat_area.config(state=tk.NORMAL)
                try:
                    line_start = state.get("think_line_start")
                    line_end = state.get("think_line_end")
                    if line_start and line_end:
                        self.chat_area.delete(line_start, line_end)
                        self.chat_area.insert(line_start, text, "thinking_text")
                        new_end = self.chat_area.index(f"{line_start} + {len(text)} chars")
                        state["think_line_end"] = new_end
                        self.chat_area.tag_remove("thinking_text", line_start, new_end)
                        self.chat_area.tag_add("thinking_text", line_start, new_end)
                finally:
                    try: self.chat_area.config(state=tk.DISABLED)
                    except tk.TclError: pass
                if was_at_bottom:
                    self.chat_area.yview_moveto(1.0)
            except tk.TclError:
                pass
        try:
            state["think_timer"] = self.root.after(
                THINKING_INTERVAL, lambda c=cid: self._tick_thinking_for(c))
        except tk.TclError:
            state["think_timer"] = None

    def _is_at_bottom(self):
        try:
            _f, last = self.chat_area.yview()
            return float(last) >= 0.999
        except tk.TclError:
            return True

    def _stop_thinking_for(self, cid, show_done=True):
        state = self._pending.get(cid)
        if state is None: return
        if state.get("think_timer") is not None:
            try: self.root.after_cancel(state["think_timer"])
            except Exception: pass
            state["think_timer"] = None

        if state["phase"] == "thinking":
            state["think_elapsed"] = time.time() - state["think_start"]
            state["phase"] = "typing"

            if cid == self.data["current_id"] and show_done:
                was_at_bottom = self._is_at_bottom()
                try: self.chat_area.config(state=tk.NORMAL)
                except tk.TclError: pass

                try:
                    try: self.chat_area.delete("think_block_start", tk.END)
                    except tk.TclError: pass
                    for tag in ("thinking_name", "thinking_text"):
                        try:
                            ranges = self.chat_area.tag_ranges(tag)
                            if ranges:
                                self.chat_area.delete(ranges[0], tk.END)
                        except tk.TclError: pass
                except Exception:
                    log_exc("_stop_thinking_for 删除失败")

                inserted = False
                try:
                    self._ensure_block_start()
                    self.chat_area.insert(tk.END, AI_DISPLAY_NAME + "\n", "name_ai")
                    if state.get("think_mode"):
                        head_text = (f"已深度思考（用时 {state['think_elapsed']:.1f} 秒）\n\n")
                        self.chat_area.insert(tk.END, head_text, "think_done")
                    # 标题以换行结尾，答案从下一行的行首开始（行号法，避免 end-1c 偏移）
                    head_line = int(self.chat_area.index("end-1c").split(".")[0])
                    state["content_start"] = self.chat_area.index("end")
                    state["stream"] = MarkdownStream(self.renderer, self.chat_area)
                    inserted = True
                except Exception:
                    log_exc("_stop_thinking_for 插入失败")

                try: self.chat_area.config(state=tk.DISABLED)
                except tk.TclError: pass

                if was_at_bottom:
                    try: self.chat_area.yview_moveto(1.0)
                    except tk.TclError: pass

                if not inserted:
                    try: self.load_conversation(cid)
                    except Exception: pass

            if state["queue"] and state["timer"] is None:
                try:
                    state["timer"] = self.root.after(
                        max(1, self.type_interval_ms), lambda c=cid: self._type_next_for(c))
                except tk.TclError:
                    state["timer"] = None

            if state.get("safety_timer") is not None:
                try: self.root.after_cancel(state["safety_timer"])
                except Exception: pass
            try:
                state["safety_timer"] = self.root.after(
                    SAFETY_TIMEOUT_MS, lambda c=cid: self._on_safety_timeout(c))
            except tk.TclError:
                state["safety_timer"] = None

    # ============ 打字机 ============
    def _ensure_pending(self, cid):
        if cid not in self._pending:
            self._pending[cid] = {
                "phase": "thinking", "queue": [], "full": "", "rendered": "",
                "stream_done": False, "timer": None, "think_timer": None,
                "think_frame": 0, "think_start": 0.0, "think_elapsed": 0.0,
                "saved": False, "content_start": None, "think_start_idx": None,
                "think_line_start": None, "think_line_end": None,
                "safety_timer": None, "reasoning": "", "stream": None,
                "think_mode": False, "paused": False, "interrupted": False,
                "reason_buf": "", "reason_timer": None, "summary_pending": False,
            }
        return self._pending[cid]

    def _feed_reasoning_for(self, cid, text):
        """接收模型流式返回的推理内容并实时展示（仅思考阶段）。"""
        state = self._pending.get(cid)
        if state is None or not text:
            return
        state["reasoning"] = (state.get("reasoning") or "") + text
        if not state.get("think_mode"):
            return                            # 没开深度思考就不显示推理内容
        if cid != self.data["current_id"]:
            return
        if state.get("phase") != "thinking":
            return
        state["reason_buf"] = (state.get("reason_buf") or "") + text
        if state.get("reason_timer") is None:
            try:
                state["reason_timer"] = self.root.after(
                    90, lambda c=cid: self._flush_reasoning_for(c))
            except tk.TclError:
                state["reason_timer"] = None

    def _flush_reasoning_for(self, cid):
        """把累积的推理文本一次性写入，降低 Text 重排次数。"""
        state = self._pending.get(cid)
        if state is None:
            return
        state["reason_timer"] = None
        buf = state.get("reason_buf") or ""
        state["reason_buf"] = ""
        if not buf or cid != self.data.get("current_id"):
            return
        if state.get("phase") != "thinking":
            return
        try:
            was_bottom = self._is_at_bottom()
            self.chat_area.config(state=tk.NORMAL)
            try:
                self.chat_area.insert(tk.END, buf, "reasoning_live")
            finally:
                try: self.chat_area.config(state=tk.DISABLED)
                except tk.TclError: pass
            if was_bottom:
                self.chat_area.yview_moveto(1.0)
        except tk.TclError:
            pass

    def _feed_typing_for(self, cid, text):
        state = self._pending.get(cid)
        if state is None or not text: return
        state["full"] += text
        state["queue"].extend(list(text))
        if state.get("safety_timer") is not None:
            try: self.root.after_cancel(state["safety_timer"])
            except Exception: pass
        try:
            state["safety_timer"] = self.root.after(
                SAFETY_TIMEOUT_MS, lambda c=cid: self._on_safety_timeout(c))
        except tk.TclError:
            state["safety_timer"] = None

        if state["phase"] == "typing" and state["timer"] is None:
            try:
                state["timer"] = self.root.after(
                    max(1, self.type_interval_ms), lambda c=cid: self._type_next_for(c))
            except tk.TclError:
                state["timer"] = None

    def _type_next_for(self, cid):
        state = self._pending.get(cid)
        if state is None: return
        state["timer"] = None
        if state["phase"] != "typing": return
        if state.get("paused"):
            return                            # 暂停：不消费队列，也不排下一帧
        qlen = len(state["queue"])
        if self.type_interval_ms <= 0:
            n = qlen                          # 关闭打字机：一次显示完
        else:
            # 队列越长一次吐越多，避免积压后“跳字”和掉帧
            n = min(qlen, max(TYPE_CHARS_PER_TICK, min(48, qlen // 10 + 1)))
        if n > 0:
            chars = "".join(state["queue"][:n])
            del state["queue"][:n]
            state["rendered"] += chars
            if cid == self.data["current_id"]:
                try:
                    was_at_bottom = self._is_at_bottom()
                    self.chat_area.config(state=tk.NORMAL)
                    try:
                        stream = state.get("stream")
                        if stream is None:
                            stream = MarkdownStream(self.renderer, self.chat_area)
                            state["stream"] = stream
                        stream.feed(chars)
                    finally:
                        try: self.chat_area.config(state=tk.DISABLED)
                        except tk.TclError: pass
                    if was_at_bottom:
                        self.chat_area.yview_moveto(1.0)
                except tk.TclError:
                    pass

        if state["queue"]:
            try:
                state["timer"] = self.root.after(
                    max(1, self.type_interval_ms), lambda c=cid: self._type_next_for(c))
            except tk.TclError:
                state["timer"] = None
        else:
            if state["stream_done"]:
                self._finish_typing_for(cid)

    def _mark_stream_done_for(self, cid):
        state = self._pending.get(cid)
        if state is None: return
        state["stream_done"] = True
        if state["phase"] == "thinking":
            self._handle_empty_response(cid)
            return
        if state.get("full") and _mpl_ready:
            try:
                threading.Thread(target=self._prepare_latex_images,
                                 args=(state["full"],), daemon=True).start()
            except Exception:
                pass
        if state["phase"] == "typing" and not state["queue"] \
                and state["timer"] is None:
            self._finish_typing_for(cid)

    def _handle_empty_response(self, cid, hint="（AI 未返回内容，请检查网络或 API 配置后重试）"):
        state = self._pending.pop(cid, None)
        if state is None:
            if self._generating_cid == cid:
                self._generating_cid = None
                self._set_send_enabled(True)
                self._update_floating_visibility()
            return
        for key in ("timer", "think_timer", "safety_timer", "reason_timer"):
            t = state.get(key)
            if t is not None:
                try: self.root.after_cancel(t)
                except Exception: pass
                state[key] = None

        if cid == self.data["current_id"]:
            try:
                was_at_bottom = self._is_at_bottom()
                self.chat_area.config(state=tk.NORMAL)
            except tk.TclError:
                was_at_bottom = True
            try:
                try: self.chat_area.delete("think_block_start", tk.END)
                except tk.TclError: pass
                for tag in ("thinking_name", "thinking_text"):
                    try:
                        ranges = self.chat_area.tag_ranges(tag)
                        if ranges:
                            self.chat_area.delete(ranges[0], tk.END)
                    except tk.TclError: pass
            except Exception:
                pass
            try:
                self._ensure_block_start()
                self.chat_area.insert(tk.END, AI_DISPLAY_NAME + "\n", "name_ai")
                self.chat_area.insert(tk.END, hint + "\n", "content")
                line_no = int(self.chat_area.index("end").split(".")[0])
                self.chat_area.insert(tk.END, "⚠ 点击这里重新生成\n\n", "regen_link")
                self._regen_lines[(cid, -1)] = line_no
            except Exception:
                pass
            try: self.chat_area.config(state=tk.DISABLED)
            except tk.TclError: pass
            if was_at_bottom:
                try: self.chat_area.yview_moveto(1.0)
                except tk.TclError: pass

        if self._generating_cid == cid:
            self._generating_cid = None
            self._set_send_enabled(True)
            self._update_floating_visibility()

    def _on_safety_timeout(self, cid):
        state = self._pending.get(cid)
        if state is None: return
        if state["phase"] == "thinking":
            self._handle_empty_response(
                cid, hint="（响应超时，请检查网络或 API 配置后重试）")
        else:
            state["interrupted"] = True
            self._finish_typing_for(cid)

    def _finish_typing_for(self, cid):
        state = self._pending.get(cid)
        if state is None: return
        for key in ("timer", "think_timer", "safety_timer", "reason_timer"):
            t = state.get(key)
            if t is not None:
                try: self.root.after_cancel(t)
                except Exception: pass
                state[key] = None

        was_at_bottom = True
        if cid == self.data["current_id"]:
            was_at_bottom = self._is_at_bottom()

        # 先落库，再整段重建：避免「打字机预览 + 渲染结果」两份文本并存
        if not state["saved"]:
            conv = self.data["conversations"].get(cid)
            if conv is not None and state["full"]:
                msg = {
                    "role": "assistant",
                    "content": state["full"],
                }
                if state.get("think_mode"):
                    msg["think_elapsed"] = round(state.get("think_elapsed", 0.0), 1)
                    msg["reasoning"] = (state.get("reasoning") or "")
                if state.get("interrupted"):
                    msg["interrupted"] = True
                conv["messages"].append(msg)
                conv["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self._save_data()
                state["saved"] = True

        state["phase"] = "done"
        self._stop_flags.discard(cid)
        self._pending.pop(cid, None)
        if self._generating_cid == cid:
            self._generating_cid = None
            self._set_send_enabled(True)
            self._update_floating_visibility()

        if cid == self.data["current_id"]:
            try:
                self._autoscroll_enabled = was_at_bottom
                self.load_conversation(cid)
                if was_at_bottom:
                    self.chat_area.yview_moveto(1.0)
                    self._update_floating_visibility()
            except Exception:
                log_exc("生成完成后重建对话失败")

    def stop_generation(self):
        """中断当前生成，保留已生成的部分。"""
        cid = self._generating_cid
        if cid is None:
            return
        self._stop_flags.add(cid)
        state = self._pending.get(cid)
        if state is not None:
            state["interrupted"] = True
            state["queue"] = []
            state["stream_done"] = True
            # 不等网络线程收尾，立即把已生成的内容落库
            try:
                self.root.after(60, lambda c=cid: self._finish_typing_for(c)
                                if c in self._pending else None)
            except tk.TclError:
                pass
        if state is not None:
            stream = state.get("stream_obj")
            if stream is not None:
                try:
                    stream.close()          # 立即断开 HTTP 流
                except Exception:
                    pass
        try:
            self.composer.set_generating(False)
        except Exception:
            pass

    def _set_send_enabled(self, enabled):
        try:
            self.composer.set_enabled(enabled)
            self.composer.set_generating(not enabled)
        except Exception:
            pass

    def _clean_messages_for_api(self, messages):
        cleaned = []
        for m in messages:
            if not isinstance(m, dict): continue
            role = m.get("role")
            content = m.get("content", "")
            if role is None: continue
            cleaned.append({"role": role, "content": content})
        return cleaned

    def _conv_context_tokens(self, conv):
        """粗略估算当前对话发出去会占用多少 tokens。"""
        try:
            total = 0
            for m in conv.get("messages") or []:
                c = m.get("content")
                if isinstance(c, str):
                    total += estimate_tokens(c) + 4
            return total
        except Exception:
            return 0

    def update_context_chip(self, compressed=False):
        try:
            conv = self.data["conversations"].get(self.data.get("current_id"))
            if conv is None or not hasattr(self, "ctx_chip"):
                return
            cfg = self.store.current_cfg()
            window = CONTEXT_WINDOWS.get(cfg["id"], DEFAULT_CONTEXT_WINDOW)
            used = self._conv_context_tokens(conv)
            ratio = min(0.999, used / window) if window else 0
            pct = int(round(ratio * 100))
            if compressed:
                text, fg, bg = f"已自动压缩 · 本对话 {pct}%", "#92400e", "#fef3c7"
            elif ratio >= 0.75:
                text, fg, bg = f"本对话 {pct}%（即将压缩）", "#b91c1c", "#fee2e2"
            elif ratio >= 0.5:
                text, fg, bg = f"本对话 {pct}%", "#92400e", "#fef3c7"
            else:
                text, fg, bg = f"本对话 {pct}%", C_TEXT_MUTED, C_BG_INPUT
            self.ctx_chip.configure(text=text, fg=fg, bg=bg)
            if compressed:
                self.root.after(6000, lambda: self.update_context_chip(False))
        except Exception:
            pass

    def update_usage_bar(self):
        """显示当前对话累计 tokens 与折算费用。"""
        try:
            conv = self.data["conversations"].get(self.data.get("current_id"))
            if conv is None or not hasattr(self, "usage_bar"):
                return
            u = conv.get("usage") or {}
            p_tok = int(u.get("prompt", 0))
            c_tok = int(u.get("completion", 0))
            total = p_tok + c_tok
            cost, cur = usage_cost(self.store.current_cfg()["id"], p_tok, c_tok)
            title = model_title(self.store.current_cfg())
            self.usage_bar.configure(
                text=f"{title} · 本次对话 {fmt_usage(total)} tokens"
                     f"（输入 {fmt_usage(p_tok)} / 输出 {fmt_usage(c_tok)}）"
                     f" · 已消耗 {cur}{cost:.2f}~")
        except Exception:
            pass

    def _record_usage(self, cid, prompt_tokens, completion_tokens):
        conv = self.data["conversations"].get(cid)
        if conv is None:
            return
        u = conv.setdefault("usage", {"prompt": 0, "completion": 0})
        u["prompt"] = int(u.get("prompt", 0)) + int(prompt_tokens or 0)
        u["completion"] = int(u.get("completion", 0)) + int(completion_tokens or 0)
        try:
            self._save_data()
        except Exception:
            pass
        if cid == self.data.get("current_id"):
            self.update_usage_bar()
            self.update_context_chip()

    def _last_user_text(self, conv):
        for m in reversed(conv.get("messages") or []):
            if m.get("role") == "user":
                return m.get("content", "")
        return ""

    def _build_api_messages(self, conv):
        messages = conv["messages"]
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
        dialog = [m for m in messages if m.get("role") != "system"]
        turns = len(dialog) // 2
        extra = []
        if self.composer.is_deep_think_on():
            native = bool(self.store.current_cfg().get("thinking_native"))
            if native:
                extra.append({"role": "system",
                              "content": "[深度思考] 当前为原生推理模型，请充分利用推理能力后再作答。"})
            else:
                extra.append({"role": "system",
                              "content": "[深度思考模式] 回答前请先在内部完成充分的推理："
                                         "拆解问题、列出关键假设与步骤、检查边界情况，"
                                         "再给出结构化、可验证的结论。不要输出推理过程本身。"})
        if self.composer.is_web_search_on():
            hits = WebSearch.search(self._last_user_text(conv))
            if hits:
                lines = [f"- {h['title']} ({h['url']})" for h in hits]
                extra.append({"role": "system",
                              "content": "[联网搜索结果，仅作参考]\n" + "\n".join(lines)})
            else:
                extra.append({"role": "system",
                              "content": "[本轮已开启智能搜索，但未获取到结果；如需实时信息请说明]"})
        est = self._conv_context_tokens(conv)
        window = CONTEXT_WINDOWS.get(self.store.current_cfg()["id"],
                                     DEFAULT_CONTEXT_WINDOW)
        if turns <= MAX_HISTORY_TURNS and est < window * 0.75:
            result = self._clean_messages_for_api(
                ([system_msg] if system_msg else []) + extra
                + [m for m in messages if m is not system_msg])
            return self._attach_images(conv, result)
        keep_count = MAX_HISTORY_TURNS * 2
        recent = dialog[-keep_count:]
        old = dialog[:-keep_count]
        self._note_compressed(conv)
        summary = conv.get("summary", "")
        if not summary and old and not conv.get("summary_pending"):
            conv["summary_pending"] = True
            threading.Thread(target=self._summary_worker,
                             args=(conv, old), daemon=True).start()
        result = []
        if system_msg:
            result.append({"role": "system",
                           "content": system_msg.get("content", "")})
        result.extend(extra)
        if summary:
            result.append({"role": "system",
                           "content": f"[历史对话摘要] {summary}"})
        result.extend(self._clean_messages_for_api(recent))
        return self._attach_images(conv, result)

    def _note_compressed(self, conv):
        """压缩发生时给界面一个提示徽标。"""
        try:
            self.root.after(0, lambda: self.update_context_chip(True))
        except Exception:
            pass

    def _attach_images(self, conv, messages):
        """把待发送的图片转成多模态 content parts，只作用于最后一条用户消息。"""
        paths = conv.get("pending_images") or []
        if not paths or not messages:
            return messages
        parts = []
        for p in paths:
            url = image_data_url(p)
            if url:
                parts.append({"type": "image_url", "image_url": {"url": url}})
        if not parts:
            return messages
        for m in reversed(messages):
            if m.get("role") == "user":
                text = m.get("content") or ""
                m["content"] = [{"type": "text", "text": text}] + parts
                break
        return messages

    def _summary_worker(self, conv, old_messages):
        """后台生成历史摘要，不阻塞本轮请求。"""
        try:
            summary = self._generate_summary(old_messages)
            if summary:
                conv["summary"] = summary
                try:
                    self._save_data()
                except Exception:
                    pass
        except Exception:
            log_exc("后台摘要生成失败")
        finally:
            conv["summary_pending"] = False

    def _generate_summary(self, old_messages):
        client = self.store.client()
        if client is None:
            return ""
        text = build_dialog_text(old_messages,
                                 max_chars=SUMMARY_MAX_CHARS,
                                 per_msg=SUMMARY_PER_MSG)
        if not text: return ""
        prompt = ("请用一段简洁的中文（不超过200字）概括以下对话的要点，"
                  "保留关键事实、结论和未完成的事项。\n\n" + text)
        try:
            resp = client.chat.completions.create(
                model=self.store.current_cfg()["api_model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=250, timeout=30)
            return resp.choices[0].message.content.strip()
        except Exception:
            return ""

    def load_conversation(self, cid):
        old_cid = self.data.get("current_id")
        if old_cid and old_cid != cid and old_cid in self.data["conversations"]:
            self._save_scroll_position(old_cid)

        if cid in self._pending:
            st = self._pending[cid]
            if st.get("timer") is not None:
                try: self.root.after_cancel(st["timer"])
                except Exception: pass
                st["timer"] = None

        self._suppress_scroll_save = True
        self.chat_area.config(state=tk.NORMAL)
        try:
            self.chat_area.delete("1.0", tk.END)
            self._think_lines.clear()
            self._regen_lines.clear()
            self._edit_lines.clear()

            if cid in self.data["conversations"]:
                for msg_idx, m in enumerate(
                        self.data["conversations"][cid]["messages"]):
                    if m["role"] == "user":
                        self.chat_area.insert(tk.END, "\n")
                        self.chat_area.insert(tk.END, "您\n", "name_user")
                        self.chat_area.insert(tk.END, m["content"] + "\n\n",
                                              "content_user")
                    elif m["role"] == "assistant":
                        self._ensure_block_start()
                        self.chat_area.insert(tk.END, AI_DISPLAY_NAME + "\n", "name_ai")
                        te = m.get("think_elapsed")
                        content = m.get("content") or ""
                        reasoning = m.get("reasoning") or ""
                        expanded = (cid, msg_idx) in self._expanded_reasoning
                        if content or reasoning or te is not None:
                            try:
                                self._render_message_at_end(
                                    self.chat_area, content, cid, msg_idx,
                                    reasoning, expanded, te)
                            except Exception as e:
                                log_exc(f"历史渲染失败，原文插入: {e}")
                                try: self.chat_area.insert(tk.END, content + "\n", "content")
                                except Exception: pass
                        if m.get("interrupted"):
                            try:
                                self._ensure_block_start()
                                line_no = int(self.chat_area.index("end").split(".")[0])
                                self.chat_area.insert(
                                    tk.END, "⚠ 生成已中断 · 点击这里重新生成\n",
                                    "regen_link")
                                self._regen_lines[(cid, msg_idx)] = line_no
                                line2 = int(self.chat_area.index("end").split(".")[0])
                                self.chat_area.insert(
                                    tk.END, "✏ 编辑这条提问后重新发送\n\n",
                                    "regen_link")
                                self._edit_lines[(cid, msg_idx)] = line2
                            except tk.TclError:
                                pass

                if cid in self._pending:
                    state = self._pending[cid]
                    self._clear_thinking_tags()
                    try:
                        self.chat_area.mark_set("think_block_start", "end")
                        self.chat_area.mark_gravity("think_block_start", tk.LEFT)
                    except tk.TclError: pass
                    state["think_start_idx"] = self.chat_area.index("end")
                    self._ensure_block_start()
                    self.chat_area.insert(tk.END, AI_DISPLAY_NAME + "\n", "name_ai")
                    if state["phase"] == "thinking":
                        line_start = self.chat_area.index("end-1c")
                        state["think_line_start"] = line_start
                        placeholder = self._think_label(THINKING_FRAMES[state["think_frame"]],
                                                     time.time() - state.get("think_start", time.time()))
                        self.chat_area.insert(tk.END, placeholder, "thinking_text")
                        line_end = self.chat_area.index("end-1c")
                        state["think_line_end"] = line_end
                        self.chat_area.insert(tk.END, "\n\n", "thinking_text")
                        if self.show_reasoning and state.get("reasoning"):
                            try:
                                self.chat_area.insert(
                                    tk.END, state["reasoning"], "reasoning_live")
                            except tk.TclError:
                                pass
                    else:
                        self.chat_area.insert(
                            tk.END,
                            f"已深度思考（用时 {state['think_elapsed']:.1f} 秒）\n\n",
                            "think_done")
                        state["content_start"] = self.chat_area.index("end")
    
                    state["stream"] = MarkdownStream(self.renderer, self.chat_area)
                    if state["rendered"]:
                        self.chat_area.insert(tk.END, state["rendered"], "content")

                    if state["queue"]:
                        try:
                            state["timer"] = self.root.after(
                                max(1, self.type_interval_ms),
                                lambda c=cid: self._type_next_for(c))
                        except tk.TclError:
                            state["timer"] = None
            self._trim_trailing_blank()
        finally:
            try: self.chat_area.config(state=tk.DISABLED)
            except tk.TclError: pass

        try: self.root.update()
        except tk.TclError: pass

        is_generating = (cid in self._pending)
        if is_generating:
            try: self.chat_area.yview_moveto(1.0)
            except tk.TclError: pass
            self._autoscroll_enabled = True
            self.root.after(50, lambda c=cid: self._force_bottom(c))
            self.root.after(200, lambda c=cid: self._force_bottom(c))
        else:
            self._restore_scroll_position(cid)
            saved = self._scroll_positions.get(cid)
            if saved and not saved.get("at_bottom"):
                top_idx = saved.get("top_index")
                if top_idx:
                    self.root.after(50, lambda c=cid, i=top_idx: self._force_index(c, i))
                    self.root.after(200, lambda c=cid, i=top_idx: self._force_index(c, i))
            else:
                self.root.after(50, lambda c=cid: self._force_bottom(c))
                self.root.after(200, lambda c=cid: self._force_bottom(c))

        if not _mpl_ready and cid not in self._pending:
            self._schedule_render_after_warmup(cid)

        self._update_floating_visibility()
        try:
            self.update_usage_bar()
            self.update_context_chip()
            self._apply_read_only()
        except Exception:
            pass
        self.root.after(250, self._release_suppress_scroll_save)

    def _release_suppress_scroll_save(self):
        self._suppress_scroll_save = False

    def _trim_trailing_blank(self):
        """去掉末尾多余空行，避免滚到底部时出现大片空白。"""
        try:
            guard = 0
            while guard < 8 and self.chat_area.index("end-1c") != "1.0":
                if self.chat_area.get("end-2c", "end-1c") != "\n":
                    break
                self.chat_area.delete("end-2c", "end-1c")
                guard += 1
        except tk.TclError:
            pass

    def send_message(self):
        if getattr(self, "read_only", False):
            messagebox.showinfo("只读查看",
                                "这是其他模型的对话，切换到该模型后才能继续。",
                                parent=self.root)
            return
        if self._generating_cid is not None:
            return
        try:
            user_input = self.composer.get_text()
            attachments = self.composer.take_attachments()
            if not user_input and not attachments:
                return
            if user_input.lower() in ["quit", "exit", "退出"] and not attachments:
                self.on_close()
                return
            if self.store.client() is None:
                messagebox.showwarning(
                    "未配置 API",
                    "当前模型还没有导入 API Key，请先在菜单 → 模型 中导入。",
                    parent=self.root)
                for att in attachments:
                    self.composer.attachments.append(att)
                self.composer._render_chips()
                return
            self.composer.clear_text()
            cfg_now = self.store.current_cfg()
            vision = cfg_now["id"] in VISION_MODELS
            images = [a for a in attachments
                      if os.path.splitext(a["name"])[1].lower()
                      in (".png", ".jpg", ".jpeg", ".webp", ".gif")]
            text_atts = [a for a in attachments if a not in images]
            content = user_input
            for att in text_atts:
                content = (content + "\n\n" if content else "") + \
                          self.composer.attachment_block(att)
            if images:
                if vision:
                    names = "、".join(a["name"] for a in images)
                    content = (content + "\n\n" if content else "") + \
                              f"[图片附件 {len(images)} 张：{names}]"
                else:
                    content = (content + "\n\n" if content else "") + \
                              "（本模型不支持图片输入，已忽略图片附件）"
            conv = self.current_conv()
            cid = self.data["current_id"]
            if cid in self._pending:
                return
            self._insert_user_message(content)
            conv["messages"].append({"role": "user", "content": content})
            if images and vision:
                conv["pending_images"] = [a["path"] for a in images]
            if conv.get("title") in (None, "", "新对话"):
                quick = " ".join((user_input or "").split())
                if quick:
                    conv["title"] = quick[:16] + ("…" if len(quick) > 16 else "")
            conv["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            conv["model_id"] = self.store.current
            self._refresh_one_item(cid)

            # 询问余额：不经过模型，直接调用服务商余额接口
            if (not attachments and len(user_input) <= 40
                    and BALANCE_RE.search(user_input)):
                self._autoscroll_enabled = True
                self._generating_cid = cid
                self._set_send_enabled(False)
                self._update_floating_visibility()
                threading.Thread(target=self._balance_worker,
                                 args=(cid,), daemon=True).start()
                return

            self._autoscroll_enabled = True
            self._generating_cid = cid
            self._set_send_enabled(False)
            self._update_floating_visibility()
            self._start_thinking_for(cid)
            threading.Thread(target=self.call_api, args=(cid,), daemon=True).start()
        except Exception:
            log_exc("send_message 异常")
            try:
                self._generating_cid = None
                self._set_send_enabled(True)
                self._update_floating_visibility()
            except Exception: pass

    # ---------- 余额查询 ----------
    def _balance_worker(self, cid):
        cfg = self.store.current_cfg()
        try:
            res = query_balance(cfg, self.store.get_key(cfg["id"]))
        except Exception as e:
            res = {"ok": False, "msg": f"余额查询失败：{e}"}
        try:
            self.root.after(0, lambda: self._show_balance(cid, cfg, res))
        except Exception:
            log_exc("余额结果回传失败")

    def _show_balance(self, cid, cfg, res):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if res.get("ok"):
            body = (f"**{model_title(cfg)} · API 余额**\n\n"
                    f"{res['text']}\n\n查询时间：{now}\n\n"
                    f"> 数据来自服务商余额接口，由本地查询，未经过模型生成。")
        else:
            body = f"**余额查询**\n\n{res.get('msg', '查询失败')}\n\n查询时间：{now}"
        conv = self.data["conversations"].get(cid)
        if conv is not None:
            conv["messages"].append({"role": "assistant", "content": body,
                                     "local": True})
            conv["time"] = now
            self._save_data()
            try:
                self._refresh_one_item(cid)
            except Exception:
                pass
        self._generating_cid = None
        self._set_send_enabled(True)
        try:
            if cid == self.data.get("current_id"):
                self.load_conversation(cid)
        except Exception:
            log_exc("余额结果渲染失败")
        self._update_floating_visibility()

    def call_api(self, cid):
        conv = self.data["conversations"].get(cid)
        if conv is None:
            def cleanup():
                self._pending.pop(cid, None)
                self._generating_cid = None
                self._set_send_enabled(True)
                self._update_floating_visibility()
            self.root.after(0, cleanup); return
        client = self.store.client()
        if client is None:
            self.root.after(0, lambda c=cid: self._handle_empty_response(
                c, hint="（当前模型未配置 API Key）"))
            return
        cfg = self.store.current_cfg()
        self._ensure_pending(cid)
        first_chunk = [False]
        think_on = bool(self.composer.is_deep_think_on())
        try:
            messages_for_api = self._build_api_messages(conv)
            conv.pop("pending_images", None)
            base_kwargs = dict(
                model=cfg["api_model"], messages=messages_for_api,
                temperature=(0.3 if self.composer.is_deep_think_on() else 0.7),
                max_tokens=3000, stream=True, timeout=API_TIMEOUT_SECONDS)
            level = getattr(self, "reasoning_level", "默认")
            conf = REASONING_CONFIG.get(cfg["id"])
            if conf and level != "默认":
                if conf["style"] == "qwen":
                    budget = {"低": 1024, "中": 4096, "高": 16384}.get(level, 4096)
                    base_kwargs["extra_body"] = {"enable_thinking": True,
                                                 "thinking_budget": budget}
                else:
                    base_kwargs["extra_body"] = {
                        "thinking": {"type": "enabled" if level == "开启" else "disabled"}}
            try:
                stream = client.chat.completions.create(
                    **base_kwargs, stream_options={"include_usage": True})
            except Exception as exc:
                msg_low = str(exc).lower()
                if "extra_body" in base_kwargs and (
                        "enable_thinking" in msg_low or "thinking_budget" in msg_low
                        or "unknown" in msg_low or "invalid" in msg_low):
                    base_kwargs.pop("extra_body", None)      # 退回默认推理
                    stream = client.chat.completions.create(
                        **base_kwargs, stream_options={"include_usage": True})
                elif "stream_options" not in msg_low:
                    raise
                else:
                    stream = client.chat.completions.create(**base_kwargs)
            self._pending.setdefault(cid, {})["stream_obj"] = stream
            usage = None
            for chunk in stream:
                if cid in self._stop_flags:
                    try: stream.close()
                    except Exception: pass
                    break
                got = getattr(chunk, "usage", None)
                if got is not None:
                    usage = got
                if not chunk.choices: continue
                delta = chunk.choices[0].delta
                if self.show_reasoning and think_on:
                    rsn = (getattr(delta, "reasoning_content", None)
                           or getattr(delta, "reasoning", None))
                    if rsn:
                        self.root.after(
                            0, lambda t=rsn, c=cid: self._feed_reasoning_for(c, t))
                piece = getattr(delta, "content", None)
                if not piece: continue
                if not first_chunk[0]:
                    first_chunk[0] = True
                    self.root.after(0, lambda c=cid: self._stop_thinking_for(c, True))
                self.root.after(0, lambda t=piece, c=cid: self._feed_typing_for(c, t))
            self.root.after(0, lambda c=cid: self._mark_stream_done_for(c))

            p_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
            c_tok = getattr(usage, "completion_tokens", 0) if usage else 0
            if not p_tok:
                p_tok = estimate_tokens("".join(
                    str(m.get("content", "")) for m in messages_for_api))
            if not c_tok:
                c_tok = estimate_tokens(self._pending.get(cid, {}).get("full", ""))
            self.root.after(0, lambda c=cid, a=p_tok, b=c_tok:
                            self._record_usage(c, a, b))

            def update_title(c=cid):
                try:
                    conv2 = self.data["conversations"].get(c)
                    if not conv2 or conv2.get("title_ai"): return
                    if not any(m.get("role") == "assistant" for m in conv2["messages"]):
                        return
                    new_title = self.ai_full_summary(conv2["messages"], TITLE_MAX)
                    if new_title:
                        conv2["title"] = new_title
                        conv2["title_ai"] = True
                        self._save_data()
                        self.root.after(0, lambda cc=c: self._refresh_one_item(cc))
                except Exception:
                    log_exc(f"update_title 异常 cid={c[:8]}")
            threading.Thread(target=update_title, daemon=True).start()

        except Exception as e:
            err_msg = str(e)
            log_exc(f"call_api 异常 cid={cid[:8]}: {err_msg}")

            def on_err(msg=err_msg, c=cid):
                try:
                    self._handle_empty_response(c, hint=f"（请求出错：{msg[:150]}）")
                except Exception:
                    try:
                        self._pending.pop(c, None)
                        self._generating_cid = None
                        self._set_send_enabled(True)
                        self._update_floating_visibility()
                    except Exception: pass
                try:
                    if c == self.data["current_id"]:
                        messagebox.showerror("请求出错", msg[:300])
                except Exception: pass
            self.root.after(0, on_err)

    def on_close(self):
        for cid, state in list(self._pending.items()):
            for key in ("timer", "think_timer", "safety_timer", "reason_timer"):
                t = state.get(key)
                if t is not None:
                    try: self.root.after_cancel(t)
                    except Exception: pass
                    state[key] = None
        try: self.floating_down.set_spinning(False)
        except Exception: pass
        try: self._save_data()
        except Exception: pass
        self.root.destroy()

    def _conv_model(self, conv):
        return conv.get("model_id") or DEFAULT_MODEL_ID

    def _is_read_only(self, cid=None):
        """查看其他模型的对话时只读。"""
        cid = cid or self.data.get("current_id")
        conv = self.data["conversations"].get(cid)
        if not conv:
            return False
        return self._conv_model(conv) != self.store.current

    def _sync_conversation_to_model(self):
        """切换模型后，把当前对话切到该模型自己的会话上。"""
        cid = self.data.get("current_id")
        conv = self.data["conversations"].get(cid)
        if conv is not None and self._conv_model(conv) == self.store.current:
            self._apply_read_only()
            return
        candidates = [(k, v) for k, v in self.data["conversations"].items()
                      if self._conv_model(v) == self.store.current]
        if candidates:
            candidates.sort(key=lambda kv: kv[1].get("time", ""), reverse=True)
            target = candidates[0][0]
            self.data["current_id"] = target
            self._rebuild_sidebar_active_state()
            self.load_conversation(target)
        else:
            self.new_conversation()

    def _apply_read_only(self):
        cid = self.data.get("current_id")
        ro = self._is_read_only(cid)
        self.read_only = ro
        try:
            if ro:
                conv = self.data["conversations"].get(cid) or {}
                name = MODELS_BY_ID.get(self._conv_model(conv), {}).get("name", "")
                self.composer.set_readonly(True, name)
            else:
                self.composer.set_readonly(False)
        except Exception:
            pass

    def _others_count(self):
        cur = self.store.current
        return sum(1 for c in self.data["conversations"].values()
                   if self._conv_model(c) != cur)

    def refresh_sidebar(self, full=False):
        cur = self.store.current
        show_other = (self.history_scope == "others")
        items = [
            (cid, conv) for cid, conv in self.data["conversations"].items()
            if (self._conv_model(conv) != cur) == show_other
        ]
        items.sort(key=lambda kv: kv[1].get("time", ""), reverse=True)
        self._update_more_bar()
        if full:
            for w in self.history_frame.winfo_children():
                w.destroy()
            self.sidebar_widgets.clear()
            for cid, conv in items:
                self._create_sidebar_item(cid, conv)
            self.history_canvas.update_idletasks()
            bbox = self.history_canvas.bbox("all")
            if bbox:
                self.history_canvas.configure(scrollregion=bbox)
                self._last_scrollregion = bbox
        else:
            for cid, conv in items:
                if cid in self.sidebar_widgets:
                    self._update_sidebar_item(cid, conv)
                else:
                    self._create_sidebar_item(cid, conv)
            for cid in list(self.sidebar_widgets.keys()):
                if cid not in self.data["conversations"]:
                    self.sidebar_widgets[cid]["canvas"].destroy()
                    del self.sidebar_widgets[cid]
        bind_wheel_all(self.history_frame, self.history_canvas)

    def _update_more_bar(self):
        """有其他模型的对话时，在列表底部浮出「更多记录」长条。"""
        try:
            others = self._others_count()
            need = others > 0
            if need and not self._more_visible:
                self.more_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 10))
                self._more_visible = True
            elif not need and self._more_visible:
                self.more_bar.pack_forget()
                self._more_visible = False
            if not need:
                return
            self.more_bar.delete("all")
            self.more_bar.update_idletasks()
            w = max(60, self.more_bar.winfo_width())
            on_others = (self.history_scope == "others")
            bgc = C_PRIMARY_SOFT if not on_others else C_ITEM_ACTIVE
            draw_round_rect(self.more_bar, 0, 2, w, 32, 15, bgc, bgc, 1)
            text = ("返回当前模型" if on_others
                    else f"更多记录 · 其他模型 {others} 条")
            self.more_bar.create_text(w / 2, 17, text=text,
                                      fill=C_PRIMARY if not on_others else "#ffffff",
                                      font=(FONT_UI, 8, "bold"))
        except Exception:
            pass

    def toggle_history_scope(self):
        self.history_scope = ("current" if self.history_scope == "others"
                              else "others")
        self.refresh_sidebar(full=True)

    def _create_sidebar_item(self, cid, conv):
        is_active = (cid == self.data["current_id"])
        title = conv.get("title", "新对话")
        if len(title) > 16: title = title[:16] + "…"
        time_str = conv.get("time", "")
        mid = self._conv_model(conv)
        model_name = MODELS_BY_ID.get(mid, {}).get("name", mid)
        canvas = tk.Canvas(self.history_frame, height=58, bg=C_BG_SIDEBAR,
                           highlightthickness=0, bd=0, cursor="hand2")
        canvas.pack(fill=tk.X, padx=4, pady=3)
        state = {"hover": False, "del_visible": False, "hover_del": False,
                 "is_active": is_active, "title": title, "time": time_str,
                 "model": model_name}

        def get_bg():
            if state["hover"] and not state["is_active"]:
                return C_ITEM_HOVER
            return C_ITEM_ACTIVE if state["is_active"] else C_ITEM

        def redraw():
            canvas.delete("all")
            try: w = canvas.winfo_width()
            except tk.TclError: return
            if w < 10: return
            h = 58; r = 14; bg_color = get_bg()
            canvas.create_oval(0, 0, 2*r, 2*r, fill=bg_color, outline=bg_color)
            canvas.create_oval(w - 2*r, 0, w, 2*r, fill=bg_color, outline=bg_color)
            canvas.create_oval(0, h - 2*r, 2*r, h, fill=bg_color, outline=bg_color)
            canvas.create_oval(w - 2*r, h - 2*r, w, h, fill=bg_color, outline=bg_color)
            canvas.create_rectangle(r, 0, w - r, h, fill=bg_color, outline=bg_color)
            canvas.create_rectangle(0, r, w, h - r, fill=bg_color, outline=bg_color)
            canvas.create_text(16, 20, anchor="w", text=state["title"],
                               fill="#ffffff", font=("Microsoft YaHei", 10, "bold"))
            canvas.create_text(16, 40, anchor="w", text=state["time"],
                               fill="#dbeafe" if state["is_active"] else C_TEXT_DIM,
                               font=("Microsoft YaHei", 8))
            label = state.get("model", "")
            if label:
                if len(label) > 14:
                    label = label[:14] + "…"
                canvas.create_text(w - 30, 40, anchor="e", text=label,
                                   fill="#c7d2fe" if state["is_active"] else "#64748b",
                                   font=("Microsoft YaHei", 7))
            if state["del_visible"]:
                del_color = C_DELETE if state["hover_del"] else C_TEXT_DIM
                canvas.create_text(w - 20, h // 2, anchor="center", text="✕",
                                   fill=del_color,
                                   font=("Microsoft YaHei", 12, "bold"),
                                   tags=("del_btn",))
                canvas.tag_bind("del_btn", "<Enter>", on_del_enter)
                canvas.tag_bind("del_btn", "<Leave>", on_del_leave)

        def on_del_enter(_e):
            if state["del_visible"]:
                state["hover_del"] = True
                try: canvas.itemconfig("del_btn", fill=C_DELETE)
                except tk.TclError: pass

        def on_del_leave(_e):
            if state["del_visible"]:
                state["hover_del"] = False
                try: canvas.itemconfig("del_btn", fill=C_TEXT_DIM)
                except tk.TclError: pass

        def on_enter(_e):
            if not state["hover"]:
                state["hover"] = True; state["del_visible"] = True; redraw()

        def on_leave(_e):
            if state["hover"]:
                state["hover"] = False; state["del_visible"] = False
                state["hover_del"] = False; redraw()

        def on_click(e):
            try: w = canvas.winfo_width()
            except tk.TclError: return
            if state["del_visible"] and e.x > w - 32:
                self.confirm_delete(cid)
            else:
                self.switch_conversation(cid)

        canvas.bind("<Configure>", lambda e: redraw())
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", on_click)
        self.sidebar_widgets[cid] = {"canvas": canvas, "redraw": redraw,
                                     "state": state, "title": title, "time": time_str}

    def _update_sidebar_item(self, cid, conv):
        widget = self.sidebar_widgets.get(cid)
        if not widget: return
        new_title = conv.get("title", "新对话")
        if len(new_title) > 16: new_title = new_title[:16] + "…"
        new_time = conv.get("time", "")
        if widget["title"] != new_title or widget["time"] != new_time:
            widget["title"] = new_title; widget["time"] = new_time
            widget["state"]["title"] = new_title
            widget["state"]["time"] = new_time
            try: widget["redraw"]()
            except tk.TclError: pass

    def _refresh_one_item(self, cid):
        conv = self.data["conversations"].get(cid)
        if conv and cid in self.sidebar_widgets:
            self._update_sidebar_item(cid, conv)

    def _rebuild_sidebar_active_state(self):
        for cid, widget in self.sidebar_widgets.items():
            active = (cid == self.data["current_id"])
            widget["state"]["is_active"] = active
            try: widget["redraw"]()
            except tk.TclError: pass

    def switch_conversation(self, cid):
        if cid == self.data["current_id"] or cid not in self.data["conversations"]:
            return
        old_cid = self.data.get("current_id")
        if old_cid: self._save_scroll_position(old_cid)
        self.data["current_id"] = cid
        self._rebuild_sidebar_active_state()
        self.load_conversation(cid)

    def new_conversation(self):
        if self._generating_cid is not None: return
        cid = str(uuid.uuid4())
        self.data["conversations"][cid] = make_new_conversation_dict(self.store.current)
        old_cid = self.data.get("current_id")
        if old_cid: self._save_scroll_position(old_cid)
        self.data["current_id"] = cid
        self._save_data()
        self.refresh_sidebar(full=True)
        self.load_conversation(cid)
        self.composer.focus_input()

    def confirm_delete(self, cid):
        if self._generating_cid == cid: return
        conv = self.data["conversations"].get(cid)
        if not conv: return
        title = conv.get("title", "新对话")
        dlg = Toplevel(self.root)
        dlg.title("删除对话")
        dlg.configure(bg=C_BG_MAIN)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.update_idletasks()
        w, h = 340, 170
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        Label(dlg, text="删除该对话？", bg=C_BG_MAIN, fg=C_TEXT_DARK,
              font=("Microsoft YaHei", 13, "bold")).pack(pady=(26, 6))
        Label(dlg, text=f"「{title}」的聊天记录将被永久删除", bg=C_BG_MAIN,
              fg=C_TEXT_MUTED, font=("Microsoft YaHei", 9)).pack()
        btn_row = Frame(dlg, bg=C_BG_MAIN)
        btn_row.pack(pady=22)

        def do_delete():
            state = self._pending.pop(cid, None)
            if state is not None:
                for key in ("timer", "think_timer", "safety_timer", "reason_timer"):
                    t = state.get(key)
                    if t is not None:
                        try: self.root.after_cancel(t)
                        except Exception: pass
            self.data["conversations"].pop(cid, None)
            self._scroll_positions.pop(cid, None)
            if self.data["current_id"] == cid:
                if self.data["conversations"]:
                    self.data["current_id"] = max(
                        self.data["conversations"].items(),
                        key=lambda kv: kv[1].get("time", ""))[0]
                else:
                    new_id = str(uuid.uuid4())
                    self.data["conversations"][new_id] = make_new_conversation_dict(self.store.current)
                    self.data["current_id"] = new_id
            if self.data["current_id"] not in self.data["conversations"]:
                self.data["current_id"] = next(iter(self.data["conversations"]))
            self._save_data()
            if cid in self.sidebar_widgets:
                self.sidebar_widgets[cid]["canvas"].destroy()
                del self.sidebar_widgets[cid]
            if self.data["current_id"] not in self.sidebar_widgets:
                self._create_sidebar_item(
                    self.data["current_id"],
                    self.data["conversations"][self.data["current_id"]])
            self._rebuild_sidebar_active_state()
            self.load_conversation(self.data["current_id"])
            dlg.destroy()
            self.composer.focus_input()

        make_rounded_button(btn_row, "取消", dlg.destroy, bg=C_BG_INPUT,
                            fg=C_TEXT_DARK, hover_bg=C_BORDER,
                            font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=8)
        make_rounded_button(btn_row, "删除", do_delete, bg=C_DELETE,
                            fg="white", hover_bg=C_DELETE_HOVER,
                            font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT, padx=8)

    def current_conv(self):
        if (not self.data.get("current_id")
                or self.data["current_id"] not in self.data["conversations"]):
            if not self.data["conversations"]:
                cid = str(uuid.uuid4())
                self.data["conversations"][cid] = make_new_conversation_dict(self.store.current)
            self.data["current_id"] = next(iter(self.data["conversations"]))
        return self.data["conversations"][self.data["current_id"]]

def unlock_store(root):
    """启动引导：首次创建密钥库，否则用主密码解锁。

    设置里关闭「启动密码」后，用内部口令自动解密，不再弹窗。
    """
    settings = load_settings()
    if not os.path.exists(CONFIG_FILE):
        res = KeySetupDialog(root, first_time=True).show()
        if not res:
            return None
        _, model_id, api_key, pwd = res
        payload = {"keys": {model_id: api_key},
                   "current": model_id}
        try:
            save_key_store(pwd, payload["keys"], payload["current"])
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")
            return None
        settings["password_required"] = True
        save_settings(settings)
        return ModelStore(pwd, payload)

    if not settings.get("password_required", True):
        payload = load_key_store(NO_PASSWORD)
        if payload is not None:
            store = ModelStore(NO_PASSWORD, payload)
            store.save()
            return store

    while True:
        res = KeySetupDialog(root, first_time=False).show()
        if not res:
            return None
        _, pwd = res
        payload = load_key_store(pwd)
        if payload is None:
            if not messagebox.askretrycancel("密码错误", "密码错误或配置文件损坏，是否重试？"):
                return None
            continue
        store = ModelStore(pwd, payload)
        store.save()
        return store


if __name__ == "__main__":
    enable_dpi_awareness()
    log_info("=" * 50)
    log_info(f"=== {APP_NAME} {APP_VERSION} 启动 ===")
    root = tk.Tk()
    center_window(root, 420, 220)
    root.title(f"{APP_NAME} - 启动中")
    root.configure(bg=C_BG_MAIN)
    Label(root, text="正在启动…", bg=C_BG_MAIN, fg=C_TEXT_DARK,
          font=("Microsoft YaHei", 12)).pack(expand=True)
    root.update()

    store = unlock_store(root)
    if store is None:
        log_info("用户取消启动")
        root.destroy()
        sys.exit(0)

    log_info(f"密钥库已解锁：{store.enabled_count()} 个模型已配置，"
             f"当前={store.current_cfg()['name']}")

    for w in root.winfo_children():
        w.destroy()
    center_window(root, 1080, 780)
    root.minsize(900, 640)
    root.title(f"{APP_NAME} {APP_VERSION_PUBLIC}")
    root.configure(bg=C_WELCOME_BG)

    settings = load_settings()

    def launch_main():
        for w in root.winfo_children():
            w.destroy()
        root.configure(bg=C_BG_MAIN)
        app = ChatApp(root, store)
        threading.Thread(target=warm_up_matplotlib, daemon=True).start()
        return app

    def on_welcome_enter(skip):
        if skip:
            settings["skip_welcome"] = True
            save_settings(settings)
            log_info("用户已勾选『以后不再显示欢迎页』，已保存")
        launch_main()

    if settings.get("skip_welcome"):
        log_info("设置：跳过欢迎页，直接进入主程序")
        launch_main()
    else:
        log_info("显示欢迎页")
        welcome = WelcomeView(root, on_enter=on_welcome_enter, show_enter=True)
        welcome.pack(fill=tk.BOTH, expand=True)

    root.mainloop()
