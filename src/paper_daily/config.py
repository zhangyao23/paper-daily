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
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        "default_model": "gpt-4o-mini",
    },
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "models": [
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ],
        "default_model": "gemini-2.0-flash-lite",
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "models": [
            "openai/gpt-4o-mini",
            "google/gemini-2.0-flash-lite",
            "anthropic/claude-3-5-sonnet",
            "anthropic/claude-3-haiku",
        ],
        "default_model": "openai/gpt-4o-mini",
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
        "mode": "lite",
        "deep_top_n": 3,
        "digest_path": "",
    },
    "keywords": {
        "presets": dict(DEFAULT_PRESETS),
    },
}


def load() -> dict:
    data = config_store.load(CONFIG_FILE)
    if not data:
        return copy.deepcopy(DEFAULTS)
    for section, default_section in DEFAULTS.items():
        if section not in data:
            data[section] = copy.deepcopy(default_section)
        else:
            for key, default_val in default_section.items():
                if key not in data[section]:
                    data[section][key] = copy.deepcopy(default_val)
    return data


def save(data: dict) -> None:
    config_store.save(CONFIG_FILE, data)


def exists() -> bool:
    return CONFIG_FILE.exists()


def resolve_api_key(cfg: dict) -> str:
    provider = cfg.get("llm", {}).get("provider", "openai")
    env_var = PROVIDERS.get(provider, {}).get("env_key", "")
    return os.environ.get(env_var, "") or cfg.get("llm", {}).get("api_key", "")


def resolve_digest_path(cfg: dict) -> Path:
    from datetime import date

    path = cfg.get("feed", {}).get("digest_path", "")
    if path:
        return Path(path)
    report_dir = Path.cwd() / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir / f"digest-{date.today().isoformat()}.md"
