from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widgets import ContentSwitcher, Input, OptionList, Static
from textual.widgets.option_list import Option

from paper_daily import __version__, config
from paper_daily.config import HISTORY_FILE
from paper_daily.core.calendar import compute_streaks, load_history, render_calendar

TAB_NAMES = ["Info", "Config", "Calendar"]

CONFIG_ITEMS = [
    {
        "key": ("llm", "provider"),
        "label": "Provider",
        "values": list(config.PROVIDERS.keys()),
    },
    {
        "key": ("llm", "model"),
        "label": "Model",
        "values": config.PROVIDERS["openai"]["models"],
    },
    {
        "key": ("llm", "api_key"),
        "label": "API Key",
        "values": None,
        "display": lambda v: f"{v[:4]}...{v[-4:]}" if len(str(v)) > 8 else "****",
    },
    {
        "key": ("feed", "time_window"),
        "label": "Time Window",
        "values": [1, 2, 3],
        "display": lambda v: f"Last {v} day{'s' if v != 1 else ''}",
    },
    {
        "key": ("feed", "output_style"),
        "label": "Output Style",
        "values": ["compact", "detailed"],
    },
    {
        "key": ("feed", "show_abstract"),
        "label": "Show Abstract",
        "values": [False, True],
        "display": lambda v: "Yes" if v else "No",
    },
    {
        "key": ("feed", "top_n"),
        "label": "Top N",
        "values": [5, 10, 15, 20],
    },
    {
        "key": ("feed", "deep_top_n"),
        "label": "Report Top N",
        "values": [2, 3, 5],
    },
]


class SettingsPanel(Container):
    class BackRequested(Message):
        pass

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("space", "cycle_value", "Cycle"),
        Binding("e", "edit_field", "Edit"),
    ]

    def __init__(self, cfg: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg
        self.current_tab = 1
        self._editing_idx: int | None = None
        self._items = [dict(item) for item in CONFIG_ITEMS]
        self._sync_model_values()

    @property
    def is_editing(self) -> bool:
        return self._editing_idx is not None

    def _sync_model_values(self) -> None:
        provider = self.cfg.get("llm", {}).get("provider", "openai")
        if provider in config.PROVIDERS:
            self._items[1]["values"] = list(
                config.PROVIDERS[provider]["models"]
            )

    def compose(self) -> ComposeResult:
        with ContentSwitcher(initial="tab-1", id="tab-switcher"):
            with VerticalScroll(id="tab-0"):
                yield Static(self._render_info())

            with Container(id="tab-1"):
                yield OptionList(id="config-list")
                yield Input(
                    placeholder="Enter value...",
                    id="config-input",
                )

            with VerticalScroll(id="tab-2"):
                yield Static(self._render_calendar(), id="calendar-content")

    def on_mount(self) -> None:
        self._populate_config_list()

    def activate(self) -> None:
        self._focus_current_tab()

    def _focus_current_tab(self) -> None:
        if self.current_tab == 1:
            self.query_one("#config-list", OptionList).focus()
        else:
            try:
                self.query_one(f"#tab-{self.current_tab}").focus()
            except Exception:
                pass

    def _render_info(self) -> Text:
        text = Text()
        text.append("\n")
        text.append("  paper-daily\n", style="bold cyan")
        text.append(f"  Version:    {__version__}\n", style="dim")
        text.append("  License:    MIT\n", style="dim")
        text.append("\n")
        text.append(
            '  "Your daily arxiv digest, powered by LLM."\n',
            style="italic dim",
        )
        return text

    def _render_calendar(self) -> Text:
        sessions = load_history(HISTORY_FILE)
        current_streak, longest_streak = compute_streaks(sessions)

        text = Text()
        text.append("\n")
        text.append("  Your paper-daily activity (last 3 months)\n\n", style="dim")
        cal = render_calendar(sessions, months=3)
        text.append_text(cal)
        text.append("\n")
        text.append(f"  Total sessions: {len(sessions)}\n", style="dim")
        text.append(f"  Current streak: {current_streak} days\n", style="dim")
        text.append(f"  Longest streak: {longest_streak} days\n", style="dim")
        return text

    def _populate_config_list(self) -> None:
        option_list = self.query_one("#config-list", OptionList)
        option_list.clear_options()
        for item in self._items:
            section, key = item["key"]
            value = self.cfg.get(section, {}).get(key, "")
            display_fn = item.get("display")
            display_value = display_fn(value) if display_fn else str(value)
            label = item["label"]
            option_list.add_option(
                Option(f"{label + ':':<16} {display_value}")
            )

    def _refresh_config_item(self, idx: int) -> None:
        item = self._items[idx]
        section, key = item["key"]
        value = self.cfg.get(section, {}).get(key, "")
        display_fn = item.get("display")
        display_value = display_fn(value) if display_fn else str(value)
        label = item["label"]
        self.query_one("#config-list", OptionList).replace_option_prompt_at_index(
            idx, f"{label + ':':<16} {display_value}"
        )

    def switch_tab(self, tab: int) -> None:
        self.current_tab = tab
        self.query_one("#tab-switcher", ContentSwitcher).current = f"tab-{tab}"
        self._focus_current_tab()

    def prev_tab(self) -> None:
        if self._editing_idx is not None:
            return
        self.switch_tab((self.current_tab - 1) % len(TAB_NAMES))

    def next_tab(self) -> None:
        if self._editing_idx is not None:
            return
        self.switch_tab((self.current_tab + 1) % len(TAB_NAMES))

    def action_back(self) -> None:
        if self._editing_idx is not None:
            self._cancel_edit()
            return
        self.post_message(self.BackRequested())

    def action_cycle_value(self) -> None:
        if self.current_tab != 1 or self._editing_idx is not None:
            return

        option_list = self.query_one("#config-list", OptionList)
        idx = option_list.highlighted
        if idx is None:
            return

        item = self._items[idx]
        if item.get("values") is None:
            return

        section, key = item["key"]
        current = self.cfg.get(section, {}).get(key)
        values = item["values"]

        try:
            current_idx = values.index(current)
            next_idx = (current_idx + 1) % len(values)
        except ValueError:
            next_idx = 0

        new_value = values[next_idx]
        if section not in self.cfg:
            self.cfg[section] = {}
        self.cfg[section][key] = new_value

        if key == "provider" and new_value in config.PROVIDERS:
            provider_info = config.PROVIDERS[new_value]
            self.cfg["llm"]["api_base"] = provider_info["api_base"]
            self.cfg["llm"]["model"] = provider_info["default_model"]
            self._items[1]["values"] = list(provider_info["models"])
            self._refresh_config_item(1)

        config.save(self.cfg)
        self._refresh_config_item(idx)

    def action_edit_field(self) -> None:
        if self.current_tab != 1 or self._editing_idx is not None:
            return

        option_list = self.query_one("#config-list", OptionList)
        idx = option_list.highlighted
        if idx is None:
            return

        item = self._items[idx]
        if item.get("values") is not None:
            return

        self._editing_idx = idx
        input_widget = self.query_one("#config-input", Input)
        input_widget.display = True
        input_widget.value = ""
        section, key = item["key"]
        if key == "api_key":
            input_widget.password = True
        else:
            input_widget.password = False
        input_widget.placeholder = f"Enter {item['label']}..."
        input_widget.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "config-input" and self._editing_idx is not None:
            idx = self._editing_idx
            item = self._items[idx]
            section, key = item["key"]
            self.cfg[section][key] = event.value
            config.save(self.cfg)
            self._cancel_edit()
            self._refresh_config_item(idx)

    def _cancel_edit(self) -> None:
        self._editing_idx = None
        input_widget = self.query_one("#config-input", Input)
        input_widget.display = False
        self.query_one("#config-list", OptionList).focus()
