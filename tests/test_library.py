import json
from pathlib import Path

import bibtexparser
import pytest

from paper_daily.core.bibtex import escape_bibtex, export_bibtex
from paper_daily.core.identifiers import deduplicate_papers, normalize_arxiv_id
from paper_daily.core.reading_list import ReadingList, export_document


@pytest.mark.parametrize("value,expected", [
    ("2401.00001", "2401.00001"),
    (" arXiv:2401.00001v12 ", "2401.00001v12"),
    ("https://arxiv.org/abs/2401.00001v2?foo=bar#page=3", "2401.00001v2"),
    ("http://export.arxiv.org/pdf/hep-th/9901001v3.pdf", "hep-th/9901001v3"),
    ("arxiv.org/html/2401.00001v1", "2401.00001v1"),
    ("https://arxiv.org/pdf/math.GT%2F0309136.pdf", "math.GT/0309136"),
    ("0704.0001v1", "0704.0001v1"),
])
def test_normalization(value, expected):
    assert normalize_arxiv_id(value).identifier == expected


@pytest.mark.parametrize("value", ["", "../../../secret", "2401.00001v0", "2413.00001",
    "2401.00000", "2401.0001", "0601.0001", "hep-th/2401001", "2401.00001 junk",
    "https://evil.test/abs/2401.00001", "https://arxiv.org.evil.test/pdf/2401.00001",
    "https://arxiv.org@evil.test/abs/2401.00001", None])
def test_invalid_ids(value):
    with pytest.raises(ValueError):
        normalize_arxiv_id(value)


def test_versions_and_order(paper):
    other = {**paper, "arxiv_id": "2401.00002v1"}
    newest = {"arxiv_id": "2401.00001v10", "title": "new title"}
    records = [paper, other, newest, {**paper, "arxiv_id": "2401.00001v2"},
               {**paper, "arxiv_id": "2401.00001"}]
    result = deduplicate_papers(records)
    assert [p["arxiv_id"] for p in result] == ["2401.00001v10", "2401.00002v1"]
    assert result[0]["title"] == "new title"
    assert "authors" not in result[0]  # Do not mix metadata across versions.
    assert deduplicate_papers([paper, {**paper, "title": "conflict"}])[0] == paper


def test_bibtex_escape_and_parse(paper):
    paper["title"] = 'A {B} & 50% #1_$ ~ ^ \\ path: café 中文'
    paper["authors"] = ["Research and Development", "Zoë Example"]
    paper["doi"] = "10.1234/test_abc"
    text = export_bibtex([paper, paper])
    parsed = bibtexparser.loads(text).entries
    assert len(parsed) == 1
    assert parsed[0]["eprint"] == "2401.00001v1"
    assert parsed[0]["year"] == "2024"
    assert parsed[0]["url"] == paper["url"]
    assert parsed[0]["author"] == "{Research and Development} and {Zoë Example}"
    for escaped in (r"\{B\}", r"\&", r"50\%", r"\#", r"\_", r"\$", r"\textbackslash{}"):
        assert escaped in text
    assert escape_bibtex("x\ny") == "x y"


def test_missing_metadata_and_key_collision():
    # Two syntactically valid legacy archive names collapse to the same key stem.
    papers = [{"arxiv_id": "ab-c/9901001"}, {"arxiv_id": "a-bc/9901001"}]
    text = export_bibtex(papers)
    parsed = bibtexparser.loads(text).entries
    assert {p["ID"] for p in parsed} == {"arxiv_abc9901001", "arxiv_abc9901001_2"}
    assert all("title" not in p and "author" not in p and "year" not in p for p in parsed)
    assert export_bibtex(list(reversed(papers))) == text


def test_persist_and_merge_versions(tmp_path, paper):
    store = ReadingList(tmp_path / "list.json")
    store.add(paper)
    store.toggle(paper["url"], "read")
    store.toggle(paper["arxiv_id"], "starred")
    store.add({**paper, "arxiv_id": "2401.00001v3", "title": "v3"})
    state = ReadingList(store.path).load()
    assert len(state) == 1 and state[0]["read"] and state[0]["starred"]
    assert state[0]["paper"]["title"] == "v3"
    store.add(paper)
    assert store.load()[0]["paper"]["title"] == "v3"
    target = ReadingList(tmp_path / "imported.json")
    target.import_json(store.export_json())
    target.import_json(store.export_json())
    assert target.load() == store.load()


def test_import_atomic_and_metadata_allowlist(tmp_path, paper):
    store = ReadingList(tmp_path / "list.json")
    store.add({**paper, "api_key": "private", "summary": "LLM-generated"})
    previous = store.path.read_bytes()
    document = json.loads(store.export_json())
    document["items"].append({"paper": {"arxiv_id": "not an ID"}, "read": False, "starred": True})
    with pytest.raises(ValueError):
        store.import_json(json.dumps(document))
    assert store.path.read_bytes() == previous
    assert "private" not in store.export_json() and "LLM-generated" not in store.export_json()
    document["schema_version"] = 2
    with pytest.raises(ValueError):
        store.import_json(json.dumps(document))


def test_corrupt_store_and_lock_preserved(tmp_path, paper):
    store = ReadingList(tmp_path / "list.json")
    store.path.write_text("corrupt", encoding="utf-8")
    with pytest.raises(ValueError):
        store.add(paper)
    assert store.path.read_text() == "corrupt"
    store.path.with_suffix(".json.lock").touch()
    with pytest.raises(ValueError, match="locked"):
        store.add(paper)
    assert store.path.read_text() == "corrupt"


def test_import_preserves_positive_states(paper):
    store = ReadingList()
    store.add(paper)
    store.toggle(paper["arxiv_id"], "read")
    store.import_json(export_document([{"paper": paper, "starred": False, "read": False}]))
    assert store.load()[0]["read"] and store.load()[0]["starred"]


def test_failed_atomic_replace_preserves_original(monkeypatch, paper):
    store = ReadingList()
    store.add(paper)
    previous = store.path.read_bytes()
    def denied(*args, **kwargs):
        raise PermissionError("simulated file in use")
    monkeypatch.setattr(Path, "replace", denied)
    with pytest.raises(PermissionError):
        store.toggle(paper["arxiv_id"], "read")
    assert store.path.read_bytes() == previous
    assert not list(store.path.parent.glob("*.tmp"))
    assert not store.path.with_suffix(".json.lock").exists()


@pytest.mark.parametrize("invalid", ["true", 1, None])
def test_import_rejects_nonboolean_state(paper, invalid):
    store = ReadingList()
    with pytest.raises(ValueError, match="booleans"):
        store.import_json(export_document([{"paper": paper, "starred": invalid, "read": False}]))
    assert not store.path.exists()
