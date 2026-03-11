from __future__ import annotations

from datetime import date

from paper_daily.core import llm
from paper_daily.prompts.formatter import build_format_prompt


def format_to_markdown(
    papers_with_review: list[dict],
    api_base: str,
    api_key: str,
    model: str,
) -> str:
    if not papers_with_review:
        return ""
    messages = build_format_prompt(papers_with_review)
    raw = llm.chat(api_base, api_key, model, messages, temperature=0.3)
    header = f"# Paper Daily Digest — {date.today().isoformat()}\n\n"
    return header + raw.strip()
