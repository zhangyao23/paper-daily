from __future__ import annotations

from collections.abc import Callable

from paper_daily.core import llm
from paper_daily.prompts.summarizing import build_summary_prompt


def summarize_papers(
    papers: list[dict],
    api_base: str,
    api_key: str,
    model: str,
    detailed: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict]:
    total = len(papers)
    results = []

    for i, paper in enumerate(papers):
        messages = build_summary_prompt(
            paper["title"], paper["abstract"], detailed=detailed
        )
        summary = llm.chat(api_base, api_key, model, messages)
        paper_copy = dict(paper)
        paper_copy["summary"] = summary.strip()
        results.append(paper_copy)

        if on_progress:
            on_progress(i + 1, total)

    return results
