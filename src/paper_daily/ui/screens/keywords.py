from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Input, SelectionList, Static
from textual.widgets.selection_list import Selection

from paper_daily.ui.widgets import Banner


class KeywordScreen(Screen):
    BINDINGS = [
        Binding("enter", "confirm", "Go", priority=True),
        Binding("escape", "cancel", "Back", priority=True),
    ]

    def __init__(self, cfg: dict) -> None:
        super().__init__()
        self.cfg = cfg
        self._awaiting_custom = False

    def compose(self) -> ComposeResult:
        yield Banner()
        yield Static(
            "  Select keyword presets (space to toggle, enter to go):",
            classes="section-label",
        )

        presets = self.cfg.get("keywords", {}).get("presets", {})
        selections = []
        for name, kws in presets.items():
            label = f"{name}  -- {', '.join(kws)}"
            selections.append(Selection(label, name, False))
        selections.append(Selection("Custom keywords...", "__custom__", False))

        yield SelectionList(*selections, id="keyword-list")
        yield Input(
            placeholder="Enter custom keywords (comma-separated)",
            id="custom-input",
        )
        yield Footer()

    def action_confirm(self) -> None:
        if self._awaiting_custom:
            return

        selection_list = self.query_one("#keyword-list", SelectionList)
        selected = list(selection_list.selected)

        if "__custom__" in selected:
            self._awaiting_custom = True
            custom_input = self.query_one("#custom-input", Input)
            custom_input.display = True
            custom_input.focus()
            return

        self._dismiss_with_keywords(selected, [])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "custom-input":
            custom_kws = [
                k.strip() for k in event.value.split(",") if k.strip()
            ]
            selection_list = self.query_one("#keyword-list", SelectionList)
            selected = list(selection_list.selected)
            self._dismiss_with_keywords(selected, custom_kws)

    def _dismiss_with_keywords(
        self, selected: list, custom: list[str]
    ) -> None:
        presets = self.cfg.get("keywords", {}).get("presets", {})
        keywords: list[str] = []
        for name in selected:
            if name == "__custom__":
                continue
            keywords.extend(presets.get(name, []))
        keywords.extend(custom)
        self.dismiss(keywords if keywords else None)

    def action_cancel(self) -> None:
        if self._awaiting_custom:
            self._awaiting_custom = False
            custom_input = self.query_one("#custom-input", Input)
            custom_input.display = False
            self.query_one("#keyword-list", SelectionList).focus()
            return
        self.dismiss(None)
