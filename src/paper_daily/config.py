from __future__ import annotations

import copy
import os
from pathlib import Path

from paper_daily.core import config_store


CONFIG_DIR = Path.home() / ".paper-daily"
CONFIG_FILE = CONFIG_DIR / "config.toml"
HISTORY_FILE = CONFIG_DIR / "history.json"

PROVIDERS = {
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "models": ["gpt-5-mini", "gpt-5.4", "gpt-5.4-pro"],
        "default_model": "gpt-5-mini",
    },
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "models": [
            "gemini-3.1-flash-lite-preview",
            "gemini-3.1-pro-preview",
            "gemini-3-flash-preview",
        ],
        "default_model": "gemini-3.1-flash-lite-preview",
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "models": [
            "openai/gpt-5-mini",
            "google/gemini-3.1-flash-lite-preview",
            "anthropic/claude-sonnet-4-6",
            "anthropic/claude-haiku-4-5",
        ],
        "default_model": "openai/gpt-5-mini",
    },
}

DEFAULT_PRESETS = {
    "agents": ["LLM agents", "tool use", "function calling"],
    "rag": ["retrieval augmented generation", "dense retrieval"],
    "multimodal": ["vision language model", "multimodal LLM"],
    "reasoning": ["chain of thought", "reasoning", "planning"],
    "alignment": ["RLHF", "preference optimization", "DPO"],
    "code": ["code generation", "program synthesis", "code LLM"],
    "fine-tuning": ["fine-tuning", "LoRA", "parameter efficient"],
    "evaluation": ["LLM evaluation", "benchmark", "leaderboard"],
    "safety": ["AI safety", "jailbreak", "red teaming"],
    "inference": ["LLM inference", "quantization", "speculative decoding"],
    "long-context": ["long context", "context window", "needle in haystack"],
    "embedding": ["text embedding", "sentence similarity"],
    "prompting": ["prompt engineering", "in-context learning", "few-shot"],
    "knowledge": ["knowledge graph", "knowledge editing", "factuality"],
    "training": ["pre-training", "scaling law", "data mixture"],
    "moe": ["mixture of experts", "sparse model"],
}

DEFAULTS = {
    "llm": {
        "provider": "openai",
        "api_base": PROVIDERS["openai"]["api_base"],
        "api_key": "",
        "model": PROVIDERS["openai"]["default_model"],
    },
    "feed": {
        "time_window": 2,
        "top_n": 10,
        "output_style": "compact",
        "show_abstract": False,
    },
    "keywords": {
        "presets": dict(DEFAULT_PRESETS),
    },
}


def load() -> dict:
    data = config_store.load(CONFIG_FILE)
    if not data:
        return copy.deepcopy(DEFAULTS)
    return data


def save(data: dict) -> None:
    config_store.save(CONFIG_FILE, data)


def exists() -> bool:
    return CONFIG_FILE.exists()


def resolve_api_key(cfg: dict) -> str:
    provider = cfg.get("llm", {}).get("provider", "openai")
    env_var = PROVIDERS.get(provider, {}).get("env_key", "")
    return os.environ.get(env_var, "") or cfg.get("llm", {}).get("api_key", "")
