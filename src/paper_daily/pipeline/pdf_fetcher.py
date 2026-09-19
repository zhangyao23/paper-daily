from __future__ import annotations

from pathlib import Path

import httpx

from paper_daily.config import CONFIG_DIR
from paper_daily.core.identifiers import normalize_arxiv_id

CACHE_DIR = CONFIG_DIR / "cache"
_ARXIV_PDF_URL = "https://arxiv.org/pdf/{}.pdf"
_TIMEOUT = 60.0


def download_pdf(arxiv_id: str) -> Path | None:
    try:
        identity = normalize_arxiv_id(arxiv_id)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        pdf_path = CACHE_DIR / f"{identity.identifier.replace('/', '_')}.pdf"
        # Unversioned URLs can change; only reuse version-pinned caches.
        if identity.version and pdf_path.exists():
            return pdf_path
        url = _ARXIV_PDF_URL.format(identity.identifier)
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        if not resp.content.lstrip().startswith(b"%PDF-"):
            return None
        pdf_path.write_bytes(resp.content)
        return pdf_path
    except Exception:
        return None


def extract_text(pdf_path: Path) -> str:
    import fitz

    with fitz.open(pdf_path) as doc:
        text_parts = [page.get_text() for page in doc]
    return "\n\n".join(text_parts)
