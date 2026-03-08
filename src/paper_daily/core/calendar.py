from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from rich.text import Text


def load_history(path: Path) -> list[str]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("sessions", [])


def save_history(path: Path, sessions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sessions": sorted(set(sessions))}, f, indent=2)


def record_session(path: Path) -> None:
    sessions = load_history(path)
    today = date.today().isoformat()
    if today not in sessions:
        sessions.append(today)
        save_history(path, sessions)


def compute_streaks(sessions: list[str]) -> tuple[int, int]:
    if not sessions:
        return 0, 0
    dates = sorted({date.fromisoformat(s) for s in sessions})
    today = date.today()

    current = 0
    d = today
    while d in dates:
        current += 1
        d -= timedelta(days=1)

    longest = 1
    streak = 1
    for i in range(1, len(dates)):
        if dates[i] - dates[i - 1] == timedelta(days=1):
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 1
    return current, longest


def render_calendar(sessions: list[str], months: int = 3) -> Text:
    session_set = {date.fromisoformat(s) for s in sessions}
    today = date.today()

    start = (today.replace(day=1) - timedelta(days=(months - 1) * 28)).replace(day=1)

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    rows: list[list[tuple[str, str]]] = [[] for _ in range(7)]

    current = start
    current -= timedelta(days=current.weekday())

    month_headers: list[tuple[int, str]] = []
    last_month = -1

    while current <= today + timedelta(days=(6 - today.weekday())):
        if current.month != last_month:
            month_headers.append((len(rows[0]), current.strftime("%b")))
            last_month = current.month

        for dow in range(7):
            d = current + timedelta(days=dow)
            if d < start or d > today:
                rows[dow].append((" ", "dim"))
            elif d in session_set:
                rows[dow].append(("\u25a0", "green"))
            else:
                rows[dow].append(("\u25a1", "dim"))

        current += timedelta(weeks=1)

    text = Text()

    header_line = "       "
    for col_idx, label in month_headers:
        padding = col_idx * 2 - len(header_line) + 7
        if padding > 0:
            header_line += " " * padding
        header_line += label
    text.append(header_line + "\n", style="cyan")

    for dow in range(7):
        text.append(f"  {day_labels[dow]}  ", style="dim")
        for char, style in rows[dow]:
            text.append(f" {char}", style=style)
        text.append("\n")

    return text
