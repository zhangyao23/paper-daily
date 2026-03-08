from __future__ import annotations

import json
from collections.abc import Callable

from paper_daily.core import llm
from paper_daily.prompts.scoring import (
    DIMENSION_KEYS,
    DIMENSION_WEIGHTS,
    build_scoring_prompt,
)


_BATCH_SIZE = 10


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
        parsed = _parse_scores(raw, len(batch))

        for j, paper in enumerate(batch):
            paper_copy = dict(paper)
            dim_scores = parsed.get(j, {})
            paper_copy["dim_scores"] = dim_scores
            paper_copy["score"] = _compute_weighted(dim_scores)
            scored.append(paper_copy)

        done += len(batch)
        if on_progress:
            on_progress(done, total)

    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored[:top_n]


def _compute_weighted(dim_scores: dict[str, float]) -> float:
    total = 0.0
    for key in DIMENSION_KEYS:
        total += dim_scores.get(key, 0.0) * DIMENSION_WEIGHTS[key]
    return round(total, 2)


def _parse_scores(raw: str, expected: int) -> dict[int, dict[str, float]]:
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
            if not isinstance(idx, int) or idx < 0 or idx >= expected:
                continue
            dim_scores = {}
            for key in DIMENSION_KEYS:
                val = item.get(key, 0.0)
                try:
                    dim_scores[key] = min(max(float(val), 0.0), 1.0)
                except (TypeError, ValueError):
                    dim_scores[key] = 0.0
            result[idx] = dim_scores
    return result
