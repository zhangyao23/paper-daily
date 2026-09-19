"""Small local JSON library. Atomic writes and a fail-fast interprocess lock."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from paper_daily.core.identifiers import canonical_paper, deduplicate_papers, normalize_arxiv_id

_TEXT_FIELDS = ("title", "abstract", "published", "updated", "doi", "journal_ref",
                "primary_category", "metadata_source")


def data_dir() -> Path:
    return Path(os.environ.get("PAPER_DAILY_DATA_DIR", str(Path.home() / ".paper-daily")))


def clean_metadata(paper: dict) -> dict:
    if not isinstance(paper, dict):
        raise ValueError("Each paper must be an object")
    canonical = canonical_paper(paper)
    result = {key: canonical[key] for key in ("arxiv_id", "url")}
    for key in _TEXT_FIELDS:
        if key in paper:
            if not isinstance(paper[key], str):
                raise ValueError(f"{key} must be a string")
            result[key] = paper[key]
    authors = paper.get("authors", [])
    if not isinstance(authors, list) or not all(isinstance(a, str) for a in authors):
        raise ValueError("authors must be a list of strings")
    result["authors"] = authors
    return result


def export_document(items: list[dict]) -> str:
    return json.dumps({"schema_version": 1, "items": items}, ensure_ascii=False, indent=2) + "\n"


def parse_document(text: str) -> list[dict]:
    document = json.loads(text)
    if (not isinstance(document, dict) or type(document.get("schema_version")) is not int
            or document["schema_version"] != 1 or not isinstance(document.get("items"), list)):
        raise ValueError("Expected reading-list JSON with schema_version: 1 and items: []")
    items = []
    for item in document["items"]:
        if not isinstance(item, dict):
            raise ValueError("Each item must be an object")
        paper = clean_metadata(item.get("paper"))
        if not isinstance(item.get("starred"), bool) or not isinstance(item.get("read"), bool):
            raise ValueError("starred and read must be booleans")
        added_at = item.get("added_at", "")
        if not isinstance(added_at, str):
            raise ValueError("added_at must be a string")
        items.append({"paper": paper, "starred": item["starred"],
                      "read": item["read"], "added_at": added_at})
    return items


class ReadingList:
    def __init__(self, path: Path | None = None):
        self.path = path if path is not None else data_dir() / "reading-list.json"

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        # Corrupt/unknown schemas are errors, never silently replaced with an empty list.
        return parse_document(self.path.read_text(encoding="utf-8"))

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            handle = lock.open("x")
        except FileExistsError as exc:
            raise ValueError("Reading list is locked by another writer. Retry; after a crash, "
                             "remove its .lock file only when no process is writing.") from exc
        try:
            with handle:
                yield
        finally:
            lock.unlink()

    def _write(self, items: list[dict]) -> None:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(export_document(items))
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _merge(items: list[dict], incoming: dict) -> None:
        identity = normalize_arxiv_id(incoming["paper"]["arxiv_id"])
        for existing in items:
            if normalize_arxiv_id(existing["paper"]["arxiv_id"]).base == identity.base:
                existing["paper"] = deduplicate_papers([existing["paper"], incoming["paper"]])[0]
                # Import never undoes existing positive user state. Explicit toggles do.
                existing["starred"] |= incoming["starred"]
                existing["read"] |= incoming["read"]
                return
        items.append(incoming)

    def add(self, paper: dict, *, starred: bool = True) -> None:
        incoming = {"paper": clean_metadata(paper), "starred": starred, "read": False,
                    "added_at": datetime.now(timezone.utc).isoformat()}
        with self._locked():
            items = self.load()
            self._merge(items, incoming)
            self._write(items)

    def toggle(self, identifier: str, field: str) -> None:
        if field not in ("starred", "read"):
            raise ValueError("Only starred and read can be toggled")
        base = normalize_arxiv_id(identifier).base
        with self._locked():
            items = self.load()
            for item in items:
                if normalize_arxiv_id(item["paper"]["arxiv_id"]).base == base:
                    item[field] = not item[field]
                    self._write(items)
                    return
            raise ValueError("Paper is not in the reading list")

    def import_json(self, text: str) -> int:
        incoming = parse_document(text)  # Validate the entire input before any mutation.
        with self._locked():
            items = self.load()
            for item in incoming:
                self._merge(items, item)
            self._write(items)
        return len(incoming)

    def export_json(self) -> str:
        return export_document(self.load())
