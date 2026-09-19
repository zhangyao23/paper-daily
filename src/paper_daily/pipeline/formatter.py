from __future__ import annotations

from datetime import date

from paper_daily.core import llm
from paper_daily.prompts.formatter import build_format_prompt
from paper_daily.pipeline.evidence import evidence_label


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
    # This manifest is generated in code, so a formatter cannot silently omit provenance.
    entries = []
    for paper in papers_with_review:
        entry = f"- {paper['arxiv_id']}: {evidence_label(paper.get('analysis_evidence'))}"
        if paper.get("review_error"):
            entry += f"; {paper['review_error']}"
        entries.append(entry)
    manifest = "## Evidence used\n\n" + "\n".join(entries)
    return header + manifest + "\n\n## Generated analysis\n\n" + raw.strip()
