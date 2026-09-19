from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from paper_daily.core.identifiers import deduplicate_papers, normalize_arxiv_id


_ARXIV_API = "https://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
_RATE_LIMIT_SECONDS = 3.0
_MAX_RESULTS_PER_QUERY = 200
_MAX_RECALL = 50
_ET = ZoneInfo("America/New_York")


def _business_days_ago(days: int) -> datetime:
    now_et = datetime.now(_ET)
    target = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = days
    while remaining > 0:
        target -= timedelta(days=1)
        if target.weekday() < 5:
            remaining -= 1
    return target


def search(keywords: list[str], time_window_days: int = 1) -> list[dict]:
    query = _build_query(keywords)
    cutoff = _business_days_ago(time_window_days).astimezone(timezone.utc)

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

    unique = deduplicate_papers(papers)

    unique.sort(key=lambda p: (-_pub_ts(p), p["title"]))
    return unique[:_MAX_RECALL]


def _pub_ts(paper: dict) -> float:
    return datetime.fromisoformat(paper["published"]).timestamp()


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

    if not all(element.text for element in (id_elem, title_elem, summary_elem, published_elem)):
        return None
    try:
        identity = normalize_arxiv_id(id_elem.text)
    except ValueError:
        return None

    paper = {
        "arxiv_id": identity.identifier,
        "title": " ".join(title_elem.text.strip().split()),
        "abstract": " ".join(summary_elem.text.strip().split()),
        "authors": authors,
        "published": published_elem.text.strip(),
        "url": identity.url,
        "metadata_source": "arxiv_api",
    }
    for field, tag in (("updated", "atom:updated"), ("doi", "arxiv:doi"),
                       ("journal_ref", "arxiv:journal_ref")):
        value = entry.findtext(tag, default="", namespaces=_NS).strip()
        if value:
            paper[field] = value
    category = entry.find("arxiv:primary_category", _NS)
    if category is not None and category.get("term"):
        paper["primary_category"] = category.get("term")
    return paper


def fetch_by_id(identifier: str) -> dict:
    identity = normalize_arxiv_id(identifier)
    response = httpx.get(_ARXIV_API, params={"id_list": identity.identifier},
                         timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    for entry in ET.fromstring(response.text).findall("atom:entry", _NS):
        paper = _parse_entry(entry)
        if paper is not None:
            found = normalize_arxiv_id(paper["arxiv_id"])
            if found.base == identity.base and (identity.version is None or found.version == identity.version):
                return paper
    raise ValueError("arXiv returned no matching paper/version")
