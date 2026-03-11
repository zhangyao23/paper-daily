from __future__ import annotations

from pathlib import Path

import httpx

from paper_daily.config import CONFIG_DIR

CACHE_DIR = CONFIG_DIR / "cache"
_ARXIV_PDF_URL = "https://arxiv.org/pdf/{}.pdf"
_TIMEOUT = 60.0


def download_pdf(arxiv_id: str) -> Path | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = CACHE_DIR / f"{arxiv_id}.pdf"
    if pdf_path.exists():
        return pdf_path
    url = _ARXIV_PDF_URL.format(arxiv_id)
    try:
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        pdf_path.write_bytes(resp.content)
        return pdf_path
    except Exception:
        return None


def extract_text(pdf_path: Path) -> str:
    import fitz

    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n\n".join(text_parts)
