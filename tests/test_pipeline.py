from datetime import datetime, timezone
from pathlib import Path
import json

import httpx
import pytest

from paper_daily.core import llm
from paper_daily.pipeline import arxiv, deep_reviewer, evidence, formatter, pdf_fetcher, scorer, summarizer


def response(text="", content=None):
    return httpx.Response(200, text=text if content is None else None, content=content,
                          request=httpx.Request("GET", "https://arxiv.org"))


def test_feed_dedup_metadata_and_lookup(monkeypatch):
    xml = (Path(__file__).parent / "fixtures/arxiv.xml").read_text(encoding="utf-8")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: response(xml))
    monkeypatch.setattr(arxiv, "_business_days_ago", lambda _: datetime(2023, 1, 1, tzinfo=timezone.utc))
    papers = arxiv.search(["test"])
    assert len(papers) == 1 and papers[0]["arxiv_id"].endswith("v2")
    assert papers[0]["doi"] == "10.0000/synthetic_fixture"
    assert papers[0]["primary_category"] == "cs.AI"
    assert arxiv.fetch_by_id("2401.00001v1")["title"] == "Synthetic old version"
    with pytest.raises(ValueError):
        arxiv.fetch_by_id("2401.00001v3")


@pytest.mark.parametrize("failure", ["timeout", "http", "html"])
def test_download_failures_fall_back(monkeypatch, paper, failure):
    def get(*args, **kwargs):
        if failure == "timeout":
            raise httpx.ReadTimeout("offline")
        if failure == "http":
            return httpx.Response(503, request=httpx.Request("GET", "https://arxiv.org"))
        return response("<html>not a PDF</html>")
    monkeypatch.setattr(httpx, "get", get)
    prepared, text = evidence.prepare_review(paper)
    assert text == paper["abstract"]
    assert prepared["analysis_evidence"]["source"] == "abstract"
    assert "FALLBACK" in evidence.evidence_label(prepared["analysis_evidence"])


@pytest.mark.parametrize("extraction", ["exception", "empty", "truncated", "complete"])
def test_extraction_provenance(monkeypatch, paper, extraction):
    monkeypatch.setattr(pdf_fetcher, "download_pdf", lambda _: Path("fixture.pdf"))
    def extract(_):
        if extraction == "exception":
            raise RuntimeError("bad PDF")
        return {"empty": "  ", "truncated": "X" * 80_001, "complete": "Full extracted text"}[extraction]
    monkeypatch.setattr(pdf_fetcher, "extract_text", extract)
    prepared, text = evidence.prepare_review(paper)
    meta = prepared["analysis_evidence"]
    assert meta["source"] == ("abstract" if extraction in ("empty", "exception") else "pdf")
    assert meta["truncated"] == (extraction == "truncated")
    assert len(text) <= 80_000
    if extraction == "truncated":
        assert meta["original_chars"] == 80_001 and meta["used_chars"] == 80_000


def test_real_pdf_extraction_and_legacy_cache(tmp_path, monkeypatch):
    import fitz
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), "Synthetic PDF extraction fixture")
        content = doc.tobytes()
    calls = []
    def get(*args, **kwargs):
        calls.append(args[0])
        return response(content=content)
    monkeypatch.setattr(httpx, "get", get)
    path = pdf_fetcher.download_pdf("hep-th/9901001v1")
    assert path.name == "hep-th_9901001v1.pdf"
    assert "Synthetic PDF" in pdf_fetcher.extract_text(path)
    assert pdf_fetcher.download_pdf("hep-th/9901001v1") == path and len(calls) == 1
    pdf_fetcher.download_pdf("hep-th/9901001")
    pdf_fetcher.download_pdf("hep-th/9901001")
    assert len(calls) == 3


def test_review_prompt_and_report_manifest(monkeypatch, paper):
    monkeypatch.setattr(pdf_fetcher, "download_pdf", lambda _: None)
    prepared, text = evidence.prepare_review(paper)
    prompts = []
    def chat(*args, **kwargs):
        prompts.append(args[3])
        return '{"experiments": {"ablation_present": null}}' if len(prompts) == 1 else "## Generated fixture"
    monkeypatch.setattr(llm, "chat", chat)
    reviewed = deep_reviewer.review_paper(prepared, text, "", "", "")
    assert "Abstract only" in prompts[0][1]["content"]
    assert "Full text:" not in prompts[0][1]["content"]
    report = formatter.format_to_markdown([reviewed], "", "", "")
    assert "## Evidence used" in report and "FALLBACK" in report
    assert "Abstract only" in prompts[1][1]["content"]


def test_empty_source_skips_llm_and_mismatched_inputs(paper):
    reviewed = deep_reviewer.review_paper(paper, "", "", "", "")
    assert "skipped" in reviewed["review_error"]
    with pytest.raises(ValueError):
        deep_reviewer.review_papers([paper], [], "", "", "")


def test_scoring_sort_and_summary_preserve_metadata(monkeypatch, paper):
    from paper_daily.prompts.scoring import DIMENSION_KEYS
    scores = [{"index": i, **dict.fromkeys(DIMENSION_KEYS, value)} for i, value in enumerate((0.2, 0.9))]
    monkeypatch.setattr(llm, "chat", lambda *a, **k: json.dumps(scores))
    ranked = scorer.score_papers([paper, {**paper, "arxiv_id": "2401.00002v1"}], ["test"], "", "", "")
    assert [p["score"] for p in ranked] == [0.9, 0.2]
    assert all(p["score_evidence"]["source"] == "abstract" for p in ranked)
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "Synthetic summary")
    result = summarizer.summarize_papers(ranked, "", "", "")
    assert result[0]["summary_evidence"]["source"] == "abstract"
    assert result[0]["metadata_source"] == "synthetic_fixture"


def test_truncation_and_invalid_review_visible_in_report(monkeypatch, paper):
    calls = []
    def chat(*args, **kwargs):
        calls.append(args[3])
        return "not valid JSON" if len(calls) == 1 else "Generated report"
    monkeypatch.setattr(llm, "chat", chat)
    reviewed = deep_reviewer.review_paper(
        {**paper, "analysis_evidence": {"source": "pdf"}}, "x" * 80_001, "", "", ""
    )
    report = formatter.format_to_markdown([reviewed], "", "", "")
    assert "TRUNCATED: 80000/80001 characters" in report
    assert "valid JSON" in report
    assert "TRUNCATED" in calls[0][1]["content"]


def test_arxiv_network_failure_propagates(monkeypatch):
    def get(*args, **kwargs):
        raise httpx.ConnectError("synthetic network outage")
    monkeypatch.setattr(httpx, "get", get)
    with pytest.raises(httpx.ConnectError):
        arxiv.search(["test"])
    with pytest.raises(httpx.ConnectError):
        arxiv.fetch_by_id("2401.00001v1")
