from __future__ import annotations

import json
from collections.abc import Callable

from paper_daily.core import llm
from paper_daily.prompts.deep_review import build_deep_review_prompt
from paper_daily.pipeline.evidence import MAX_TEXT_CHARS


def review_paper(
    paper: dict,
    full_text: str,
    api_base: str,
    api_key: str,
    model: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    paper_id = paper.get("arxiv_id", "")
    evidence = dict(paper.get("analysis_evidence") or {"source": "unknown"})
    if len(full_text) > MAX_TEXT_CHARS:
        evidence.update(truncated=True, original_chars=len(full_text), used_chars=MAX_TEXT_CHARS)
    if not full_text.strip():
        return {**paper, "analysis_evidence": evidence, "deep_review": {},
                "review_error": "No usable source text; review skipped"}
    messages = build_deep_review_prompt(paper_id, full_text, evidence)
    raw = llm.chat(api_base, api_key, model, messages, temperature=0.1)
    parsed = _parse_json(raw)
    paper_copy = dict(paper)
    paper_copy["deep_review"] = parsed if parsed else {}
    paper_copy["analysis_evidence"] = evidence
    if parsed is None:
        paper_copy["review_error"] = "LLM did not return a valid JSON object"
    return paper_copy


def review_papers(
    papers: list[dict],
    full_texts: list[str],
    api_base: str,
    api_key: str,
    model: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict]:
    results = []
    total = len(papers)
    if len(papers) != len(full_texts):
        raise ValueError("Each paper requires exactly one text input")
    for i, (paper, text) in enumerate(zip(papers, full_texts)):
        result = review_paper(
            paper, text, api_base, api_key, model, on_progress
        )
        results.append(result)
        if on_progress:
            on_progress(i + 1, total)
    return results


def _parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(
            lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        )
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None
