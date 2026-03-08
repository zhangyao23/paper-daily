from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Input, OptionList, Static
from textual.widgets.option_list import Option

from paper_daily import __version__
from paper_daily.ui.screens.settings import SettingsPanel, TAB_NAMES
from paper_daily.ui.widgets import Banner


def _hint_text(pairs: list[tuple[str, str]]) -> Text:
    text = Text()
    for i, (key, label) in enumerate(pairs):
        if i > 0:
            text.append("    ")
        text.append(f"[{key}]", style="cyan bold")
        text.append(f" {label}", style="dim")
    return text


def _render_keyword_option(
    name: str, kws: list[str], selected: bool
) -> Text:
    text = Text()
    if selected:
        text.append(" \u258e ", style="cyan")
        text.append(name, style="bold cyan")
        if kws:
            text.append(f"  -- {', '.join(kws)}", style="cyan")
    else:
        text.append("   ")
        text.append(name)
        if kws:
            text.append(f"  -- {', '.join(kws)}", style="dim")
    return text


_KEYWORD_HINTS = [
    ("space", "Toggle"),
    ("enter", "Fetch"),
    ("s", "Settings"),
    ("q", "Quit"),
]
_SETTINGS_HINTS = [
    ("</>", "Switch tab"),
    ("space", "Cycle"),
    ("e", "Edit"),
    ("esc", "Back"),
    ("q", "Quit"),
]


class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("enter", "confirm", "Fetch", priority=True, show=False),
        Binding(
            "space", "toggle_selection", "Toggle",
            priority=True, show=False,
        ),
        Binding("s", "settings", "Settings", priority=True, show=False),
        Binding("q", "quit_app", "Quit", priority=True, show=False),
        Binding("escape", "handle_escape", "", priority=True, show=False),
        Binding("left", "prev_tab", "", priority=True, show=False),
        Binding("right", "next_tab", "", priority=True, show=False),
    ]

    def __init__(self, cfg: dict) -> None:
        super().__init__()
        self.cfg = cfg
        self._mode = "menu"
        self._awaiting_custom = False
        self._selected: set[str] = set()
        presets = cfg.get("keywords", {}).get("presets", {})
        self._preset_names: list[str] = list(presets.keys()) + ["__custom__"]

    def check_action(
        self, action: str, parameters: tuple[object, ...]
    ) -> bool | None:
        if action in ("confirm", "toggle_selection"):
            if self._mode == "settings" or self._awaiting_custom:
                return None
        if action in ("settings", "quit_app"):
            if self._awaiting_custom:
                return None
        if action == "handle_escape":
            if self._mode == "settings":
                return None
        return True

    def compose(self) -> ComposeResult:
        yield Banner(id="main-banner")
        with ContentSwitcher(initial="keyword-view", id="view-switcher"):
            with Container(id="keyword-view"):
                yield Static(
                    "  Select keyword presets "
                    "(space to toggle, enter to fetch):",
                    classes="section-label",
                )
                presets = self.cfg.get("keywords", {}).get("presets", {})
                options = []
                for name, kws in presets.items():
                    options.append(
                        Option(
                            _render_keyword_option(name, kws, False),
                            id=name,
                        )
                    )
                options.append(
                    Option(
                        _render_keyword_option(
                            "Custom keywords...", [], False
                        ),
                        id="__custom__",
                    )
                )
                yield OptionList(*options, id="keyword-list")
                yield Input(
                    placeholder="Enter custom keywords (comma-separated)",
                    id="custom-input",
                )
            yield SettingsPanel(self.cfg, id="settings-view")
        yield Static(_hint_text(_KEYWORD_HINTS), id="hint-bar")

    def on_mount(self) -> None:
        self._update_banner()
        self.query_one("#keyword-list", OptionList).focus()

    def on_screen_resume(self) -> None:
        if self._mode == "settings":
            self._switch_to_keywords()
        if self._awaiting_custom:
            self._awaiting_custom = False
            self.query_one("#custom-input", Input).display = False
        self.query_one("#keyword-list", OptionList).focus()

    def action_toggle_selection(self) -> None:
        option_list = self.query_one("#keyword-list", OptionList)
        idx = option_list.highlighted
        if idx is None:
            return
        name = self._preset_names[idx]
        if name in self._selected:
            self._selected.discard(name)
        else:
            self._selected.add(name)
        self._refresh_keyword_option(idx)

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        if event.option_list.id != "keyword-list":
            return
        name = event.option.id
        if name in self._selected:
            self._selected.discard(name)
        else:
            self._selected.add(name)
        idx = event.option_index
        self._refresh_keyword_option(idx)

    def _refresh_keyword_option(self, idx: int) -> None:
        name = self._preset_names[idx]
        is_selected = name in self._selected
        presets = self.cfg.get("keywords", {}).get("presets", {})
        if name == "__custom__":
            prompt = _render_keyword_option(
                "Custom keywords...", [], is_selected
            )
        else:
            kws = presets.get(name, [])
            prompt = _render_keyword_option(name, kws, is_selected)
        self.query_one(
            "#keyword-list", OptionList
        ).replace_option_prompt_at_index(idx, prompt)

    def action_confirm(self) -> None:
        selected = list(self._selected)

        if "__custom__" in selected:
            self._awaiting_custom = True
            custom_input = self.query_one("#custom-input", Input)
            custom_input.display = True
            custom_input.focus()
            return

        self._start_fetch_with_keywords(selected, [])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "custom-input":
            custom_kws = [
                k.strip() for k in event.value.split(",") if k.strip()
            ]
            selected = list(self._selected)
            self._start_fetch_with_keywords(selected, custom_kws)

    def _start_fetch_with_keywords(
        self, selected: list, custom: list[str]
    ) -> None:
        presets = self.cfg.get("keywords", {}).get("presets", {})
        keywords: list[str] = []
        for name in selected:
            if name == "__custom__":
                continue
            keywords.extend(presets.get(name, []))
        keywords.extend(custom)
        if not keywords:
            return
        self._awaiting_custom = False
        custom_input = self.query_one("#custom-input", Input)
        custom_input.value = ""
        custom_input.display = False
        self._launch_pipeline(keywords)

    def _launch_pipeline(self, keywords: list[str]) -> None:
        from paper_daily.ui.screens.running import RunningScreen

        self.app.push_screen(
            RunningScreen(self.cfg, keywords), callback=self._on_pipeline
        )

    def _on_pipeline(self, papers: list[dict] | None) -> None:
        if not papers:
            return
        from paper_daily.ui.screens.results import ResultsScreen

        self.app.push_screen(ResultsScreen(self.cfg, papers))

    def action_handle_escape(self) -> None:
        if self._awaiting_custom:
            self._awaiting_custom = False
            custom_input = self.query_one("#custom-input", Input)
            custom_input.display = False
            self.query_one("#keyword-list", OptionList).focus()

    def action_settings(self) -> None:
        if self._mode == "settings":
            return
        self._switch_to_settings()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_prev_tab(self) -> None:
        if self._mode != "settings":
            return
        panel = self.query_one("#settings-view", SettingsPanel)
        if panel.is_editing:
            return
        panel.prev_tab()
        self._update_banner()

    def action_next_tab(self) -> None:
        if self._mode != "settings":
            return
        panel = self.query_one("#settings-view", SettingsPanel)
        if panel.is_editing:
            return
        panel.next_tab()
        self._update_banner()

    def on_settings_panel_back_requested(
        self, event: SettingsPanel.BackRequested
    ) -> None:
        self._switch_to_keywords()

    def _switch_to_settings(self) -> None:
        self._mode = "settings"
        self._update_banner()
        self.query_one("#hint-bar", Static).update(
            _hint_text(_SETTINGS_HINTS)
        )
        self.query_one("#view-switcher", ContentSwitcher).current = (
            "settings-view"
        )
        self.query_one("#settings-view", SettingsPanel).activate()

    def _switch_to_keywords(self) -> None:
        self._mode = "menu"
        self._update_banner()
        self.query_one("#hint-bar", Static).update(
            _hint_text(_KEYWORD_HINTS)
        )
        self.query_one("#view-switcher", ContentSwitcher).current = (
            "keyword-view"
        )
        self.query_one("#keyword-list", OptionList).focus()

    def _update_banner(self) -> None:
        banner = self.query_one("#main-banner", Banner)
        if self._mode == "settings":
            text = Text()
            panel = self.query_one("#settings-view", SettingsPanel)
            text.append("Settings -- ", style="dim")
            for i, name in enumerate(TAB_NAMES):
                if i > 0:
                    text.append("  ")
                if i == panel.current_tab:
                    text.append(f"[{name}]", style="bold cyan")
                else:
                    text.append(name, style="dim")
            banner.update_right(text)
        else:
            banner.update_right("")
