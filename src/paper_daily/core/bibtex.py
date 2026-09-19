"""Deterministic export of supplied metadata; never calls an LLM."""
from __future__ import annotations

from datetime import datetime
import re

from paper_daily.core.identifiers import deduplicate_papers, normalize_arxiv_id

_ESCAPES = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def escape_bibtex(value: str) -> str:
    # Single pass: do not re-escape braces introduced by an earlier replacement.
    return "".join(_ESCAPES.get(char, char) for char in " ".join(value.split()))


def export_bibtex(papers: list[dict]) -> str:
    entries = []
    used: set[str] = set()
    for paper in sorted(deduplicate_papers(papers), key=lambda p: p["arxiv_id"]):
        identity = normalize_arxiv_id(paper["arxiv_id"])
        stem = "arxiv_" + re.sub(r"[^A-Za-z0-9]", "", identity.base)
        key, suffix = stem, 2
        while key in used:
            key = f"{stem}_{suffix}"
            suffix += 1
        used.add(key)
        fields = {}
        if paper.get("title"):
            fields["title"] = "{" + escape_bibtex(paper["title"]) + "}"
        if paper.get("authors"):
            # Brace literal names, including organizations and names containing 'and'.
            fields["author"] = " and ".join(
                "{" + escape_bibtex(author) + "}" for author in paper["authors"]
            )
        if paper.get("published"):
            try:
                fields["year"] = str(datetime.fromisoformat(paper["published"]).year)
            except ValueError:
                pass  # A year is not inferred from an ID or invented for missing dates.
        fields.update(archivePrefix="arXiv", eprint=identity.identifier, url=identity.url)
        for source, target in (("primary_category", "primaryClass"), ("doi", "doi")):
            if paper.get(source):
                fields[target] = escape_bibtex(paper[source])
        if paper.get("journal_ref"):
            fields["note"] = escape_bibtex("Journal reference: " + paper["journal_ref"])
        body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields.items())
        entries.append(f"@misc{{{key},\n{body}\n}}")
    return "\n\n".join(entries) + ("\n" if entries else "")
