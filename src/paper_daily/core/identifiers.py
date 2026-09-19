"""arXiv identity and deterministic, version-aware deduplication (no network)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class ArxivID:
    base: str
    version: int | None = None

    @property
    def identifier(self) -> str:
        return self.base + (f"v{self.version}" if self.version else "")

    @property
    def url(self) -> str:
        return f"https://arxiv.org/abs/{self.identifier}"


def normalize_arxiv_id(value: str) -> ArxivID:
    if not isinstance(value, str):
        raise ValueError("arXiv ID must be a string")
    value = value.strip()
    if value.lower().startswith("arxiv:"):
        value = value[6:].strip()
    if value.startswith(("arxiv.org/", "www.arxiv.org/", "export.arxiv.org/")):
        value = "https://" + value
    if "://" in value:
        url = urlsplit(value)
        if (url.scheme not in ("http", "https") or url.netloc.lower() not in
                {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}):
            raise ValueError("Expected an arxiv.org URL")
        match = re.fullmatch(r"/(?:abs|pdf|html)/(.+?)/?", unquote(url.path))
        if not match:
            raise ValueError("Expected an arXiv abs, pdf, or html URL")
        value = match[1]
    value = re.sub(r"\.pdf$", "", value, flags=re.IGNORECASE)
    match = re.fullmatch(
        r"(?P<base>(?P<date>\d{4})\.(?P<seq>\d{4,5})|"
        r"(?P<archive>[a-zA-Z][a-zA-Z-]*(?:\.[a-zA-Z]{2})?)/(?P<old>\d{7}))"
        r"(?:v(?P<version>[1-9]\d*))?", value,
    )
    if not match:
        raise ValueError(f"Invalid arXiv ID: {value}")
    stamp = match["date"] or match["old"][:4]
    year, month = int(stamp[:2]), int(stamp[2:])
    if not 1 <= month <= 12:
        raise ValueError("Invalid month in arXiv ID")
    if match["date"]:
        if stamp < "0704" or len(match["seq"]) != (4 if stamp < "1501" else 5):
            raise ValueError("Invalid modern arXiv ID date or sequence length")
        sequence = match["seq"]
        base = match["base"]
    else:
        if not (year >= 91 or year <= 6 or (year == 7 and month <= 3)):
            raise ValueError("Invalid legacy arXiv ID date")
        archive, _, subject = match["archive"].partition(".")
        base = archive.lower() + ("." + subject.upper() if subject else "")
        base += "/" + match["old"]
        sequence = match["old"][4:]
    if int(sequence) == 0:
        raise ValueError("arXiv sequence starts at 1")
    return ArxivID(base, int(match["version"]) if match["version"] else None)


def canonical_paper(paper: dict) -> dict:
    identity = normalize_arxiv_id(paper.get("arxiv_id") or paper.get("url", ""))
    return {**paper, "arxiv_id": identity.identifier, "url": identity.url}


def deduplicate_papers(papers: list[dict]) -> list[dict]:
    """One record per work; highest explicit version wins; first wins ties.

    An unversioned ID means unknown/latest at source, not a known version number.
    Never splice bibliographic fields or analysis from different versions.
    """
    unique: dict[str, dict] = {}
    for paper in papers:
        paper = canonical_paper(paper)
        identity = normalize_arxiv_id(paper["arxiv_id"])
        previous = unique.get(identity.base)
        if previous is None or (identity.version or 0) > (
            normalize_arxiv_id(previous["arxiv_id"]).version or 0
        ):
            unique[identity.base] = paper
    return list(unique.values())
