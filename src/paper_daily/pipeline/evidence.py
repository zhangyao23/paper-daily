"""Code-owned provenance: never ask an LLM to decide what it was given."""
from __future__ import annotations

from paper_daily.pipeline import pdf_fetcher

MAX_TEXT_CHARS = 80_000


def prepare_review(paper: dict) -> tuple[dict, str]:
    text = paper.get("abstract", "")
    source, reason = "abstract", "PDF download failed or returned non-PDF content"
    path = pdf_fetcher.download_pdf(paper["arxiv_id"])
    if path is not None:
        try:
            extracted = pdf_fetcher.extract_text(path)
            if extracted.strip():
                text, source, reason = extracted, "pdf", None
            else:
                reason = "PDF contained no extractable text (OCR is not supported)"
        except Exception:
            reason = "PDF text extraction failed"
    if not text.strip():
        source = "none"
        reason = (reason or "") + "; no abstract available"
    evidence = {"source": source, "fallback_reason": reason,
                "truncated": len(text) > MAX_TEXT_CHARS,
                "original_chars": len(text), "used_chars": min(len(text), MAX_TEXT_CHARS)}
    return {**paper, "analysis_evidence": evidence}, text[:MAX_TEXT_CHARS]


def evidence_label(evidence: dict | None) -> str:
    if not evidence:
        return "Analysis source: unknown (legacy record)"
    source = evidence.get("source")
    labels = {"abstract": "Abstract only", "pdf": "PDF extracted text (not a visual/formula audit)",
              "none": "No usable source text", "unknown": "Unknown source"}
    label = labels.get(source, "Unknown source")
    if evidence.get("fallback_reason"):
        label += "; FALLBACK: " + evidence["fallback_reason"]
    if evidence.get("truncated"):
        label += f"; TRUNCATED: {evidence['used_chars']}/{evidence['original_chars']} characters"
    return label
