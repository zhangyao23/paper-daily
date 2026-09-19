"""Private, non-overwriting exports shared by the terminal screens."""
from datetime import datetime
from pathlib import Path

from paper_daily.core.reading_list import data_dir


def save_export(content: str, stem: str, suffix: str) -> Path:
    directory = data_dir() / "exports"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = directory / f"{stem}-{stamp}.{suffix}"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)
    return path
