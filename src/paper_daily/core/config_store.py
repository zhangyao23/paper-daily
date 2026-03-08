from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def save(path: Path, data: dict) -> None:
    ensure_dir(path.parent)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
