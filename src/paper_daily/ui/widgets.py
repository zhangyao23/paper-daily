from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from paper_daily import __version__

_ICON_STYLE = "#00bcd4"


class Banner(Container):
    DEFAULT_CSS = """
    Banner {
        layout: horizontal;
        width: 100%;
        height: auto;
        border: round $accent;
        padding: 0 1;
        margin-bottom: 1;
    }
    #banner-left {
        width: auto;
        padding-right: 1;
    }
    #banner-divider {
        width: 1;
        height: 100%;
        border-left: vkey $accent;
    }
    #banner-right {
        width: 1fr;
        padding-left: 2;
        content-align: left middle;
    }
    """

    def __init__(self, right_text: str | Text = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._right_text = right_text

    def compose(self) -> ComposeResult:
        yield Static(self._build_left(), id="banner-left")
        yield Static(id="banner-divider")
        if isinstance(self._right_text, Text):
            right = self._right_text
        else:
            right = _default_right(self._right_text)
        yield Static(right, id="banner-right")

    @staticmethod
    def _build_left() -> Text:
        c = _ICON_STYLE
        text = Text()
        text.append(" \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n", style=c)
        text.append(" \u2551 \u2580\u2580\u2580\u2580\u2580 \u2551\n", style=c)
        text.append(" \u2551 \u2500\u2500\u2500\u2500\u2500 \u2551", style=c)
        text.append("   Paper Daily\n", style=f"bold {c}")
        text.append(" \u2551 \u2500\u2500\u2500\u2500\u2500 \u2551", style=c)
        text.append(f"   v{__version__}\n", style="dim")
        text.append(" \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", style=c)
        return text

    def update_right(self, content: str | Text) -> None:
        if isinstance(content, Text):
            self.query_one("#banner-right", Static).update(content)
        else:
            self.query_one("#banner-right", Static).update(
                _default_right(content)
            )


def _default_right(subtitle: str) -> Text:
    text = Text()
    if subtitle:
        text.append(subtitle, style="dim")
    else:
        text.append(
            "Your daily arxiv digest,\npowered by LLM.", style="dim"
        )
    return text


def score_style(score: float) -> str:
    if score >= 0.80:
        return "green"
    if score >= 0.50:
        return "yellow"
    return "dim"
