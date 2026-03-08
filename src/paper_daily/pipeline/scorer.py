from __future__ import annotations

import json
from collections.abc import Callable

from paper_daily.core import llm
from paper_daily.prompts.scoring import build_scoring_prompt


_BATCH_SIZE = 15


def score_papers(
    papers: list[dict],
    keywords: list[str],
    api_base: str,
    api_key: str,
    model: str,
    top_n: int = 10,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict]:
    scored = []
    total = len(papers)
    done = 0

    for i in range(0, total, _BATCH_SIZE):
        batch = papers[i : i + _BATCH_SIZE]
        messages = build_scoring_prompt(batch, keywords)
        raw = llm.chat(api_base, api_key, model, messages, temperature=0.1)
        scores = _parse_scores(raw, len(batch))

        for j, paper in enumerate(batch):
            paper_copy = dict(paper)
            paper_copy["score"] = scores.get(j, 0.0)
            scored.append(paper_copy)

        done += len(batch)
        if on_progress:
            on_progress(done, total)

    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored[:top_n]


def _parse_scores(raw: str, expected: int) -> dict[int, float]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(
            lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        )

    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    result = {}
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            idx = item.get("index")
            score = item.get("score", 0.0)
            if isinstance(idx, int) and 0 <= idx < expected:
                result[idx] = min(max(float(score), 0.0), 1.0)
    return result
