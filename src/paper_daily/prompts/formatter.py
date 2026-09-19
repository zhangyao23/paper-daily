from __future__ import annotations

import json
from paper_daily.pipeline.evidence import evidence_label


def build_format_prompt(papers_with_review: list[dict]) -> list[dict]:
    entries = []
    for p in papers_with_review:
        title = p.get("title", "")
        url = p.get("url", "")
        review = p.get("deep_review", {})
        entries.append(
            f"Title: {title}\nURL: {url}\nEvidence: {evidence_label(p.get('analysis_evidence'))}\n"
            f"Review error: {p.get('review_error', 'none')}\nDeep review JSON:\n{json.dumps(review, ensure_ascii=False)}"
        )
    block = "\n\n---\n\n".join(entries)

    system_content = (
        "You are a tech podcast host and senior editor. "
        "Convert the hard-core academic analysis JSON into human-friendly "
        "morning digest format. Use ACM MM-level standards to assess potential value. "
        "Use clear headings, bold key conclusions, and add a short 'Host Take' "
        "summarizing the inspiration for our own architecture design.\n\n"
        "Output format: Markdown with ## for each paper, ### for subsections "
        "State each paper's evidence source and fallback/truncation. Never imply a full-paper "
        "review for abstract-only or truncated input. Do not invent missing evidence. "
        "(Architecture, Innovations, Experiments, Host Take). "
        "No preamble, start directly with the digest content."
    )

    return [
        {"role": "system", "content": system_content},
        {
            "role": "user",
            "content": f"Papers to format:\n\n{block}",
        },
    ]
