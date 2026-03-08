from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx


_ARXIV_API = "https://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}
_RATE_LIMIT_SECONDS = 3.0
_MAX_RESULTS_PER_QUERY = 200


def search(keywords: list[str], time_window_hours: int = 24) -> list[dict]:
    query = _build_query(keywords)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

    papers: list[dict] = []
    start = 0

    while True:
        url = (
            f"{_ARXIV_API}?search_query={query}"
            f"&start={start}&max_results={_MAX_RESULTS_PER_QUERY}"
            f"&sortBy=submittedDate&sortOrder=descending"
        )

        resp = httpx.get(url, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        entries = root.findall("atom:entry", _NS)

        if not entries:
            break

        batch_has_old = False
        for entry in entries:
            paper = _parse_entry(entry)
            if paper is None:
                continue
            published = datetime.fromisoformat(paper["published"])
            if published < cutoff:
                batch_has_old = True
                continue
            papers.append(paper)

        if batch_has_old or len(entries) < _MAX_RESULTS_PER_QUERY:
            break

        start += _MAX_RESULTS_PER_QUERY
        time.sleep(_RATE_LIMIT_SECONDS)

    seen = set()
    unique = []
    for p in papers:
        if p["arxiv_id"] not in seen:
            seen.add(p["arxiv_id"])
            unique.append(p)
    return unique


def _build_query(keywords: list[str]) -> str:
    parts = []
    for kw in keywords:
        parts.append(quote(f'all:"{kw}"'))
    return "+OR+".join(parts)


def _parse_entry(entry: ET.Element) -> dict | None:
    id_elem = entry.find("atom:id", _NS)
    title_elem = entry.find("atom:title", _NS)
    summary_elem = entry.find("atom:summary", _NS)
    published_elem = entry.find("atom:published", _NS)

    if id_elem is None or title_elem is None or summary_elem is None or published_elem is None:
        return None

    authors = []
    for author in entry.findall("atom:author", _NS):
        name = author.find("atom:name", _NS)
        if name is not None and name.text:
            authors.append(name.text.strip())

    arxiv_id = id_elem.text.strip().split("/abs/")[-1]

    return {
        "arxiv_id": arxiv_id,
        "title": " ".join(title_elem.text.strip().split()),
        "abstract": " ".join(summary_elem.text.strip().split()),
        "authors": authors,
        "published": published_elem.text.strip(),
        "url": f"https://arxiv.org/abs/{arxiv_id}",
    }
