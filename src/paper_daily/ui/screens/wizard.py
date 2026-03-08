from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from paper_daily import config
from paper_daily.ui.widgets import Banner


class WizardScreen(Screen):
    BINDINGS = [
        Binding("escape", "prev_step", "Back", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.values: dict = {}
        self.current_step = 0
        self.total_steps = 6

    def compose(self) -> ComposeResult:
        yield Banner()
        yield Static("Welcome to paper-daily! Let's get you set up.", id="welcome-text")
        yield Static("", id="step-label")

        with ContentSwitcher(initial="step-0", id="wizard-steps"):
            with Container(id="step-0"):
                yield OptionList(
                    *[Option(p, id=p) for p in config.PROVIDERS],
                    id="provider-select",
                )

            with Container(id="step-1"):
                yield Static("", id="api-key-hint")
                yield Input(
                    placeholder="Enter your API key",
                    password=True,
                    id="api-key-input",
                )

            with Container(id="step-2"):
                yield OptionList(id="model-select")

            with Container(id="step-3"):
                yield OptionList(
                    Option("Last 1 day", id="1"),
                    Option("Last 2 days", id="2"),
                    Option("Last 3 days", id="3"),
                    id="time-window-select",
                )

            with Container(id="step-4"):
                yield OptionList(
                    Option("Compact (title + one-line summary)", id="compact"),
                    Option("Detailed (title + full summary)", id="detailed"),
                    id="output-style-select",
                )

            with Container(id="step-5"):
                yield OptionList(
                    Option("No", id="false"),
                    Option("Yes", id="true"),
                    id="abstract-select",
                )

        yield Footer()

    def on_mount(self) -> None:
        self._update_step_label()
        self.query_one("#provider-select", OptionList).focus()

    def _update_step_label(self) -> None:
        labels = [
            "Select LLM Provider",
            "Enter API Key",
            "Select Model",
            "Time Window for Paper Search",
            "Output Style",
            "Include Paper Abstract?",
        ]
        label = labels[self.current_step]
        self.query_one("#step-label", Static).update(
            f"  Step {self.current_step + 1}/{self.total_steps}: {label}"
        )

    def _go_to_step(self, step: int) -> None:
        self.current_step = step
        self.query_one("#wizard-steps", ContentSwitcher).current = f"step-{step}"
        self._update_step_label()
        self._focus_current()

    def _focus_current(self) -> None:
        step = self.current_step
        if step == 1:
            provider = self.values.get("provider", "openai")
            env_key = config.PROVIDERS[provider]["env_key"]
            self.query_one("#api-key-hint", Static).update(
                f"  (or set {env_key} env var later)"
            )
            self.query_one("#api-key-input", Input).focus()
        elif step == 2:
            self._populate_models()
            self.query_one("#model-select", OptionList).focus()
        else:
            step_map = {
                0: "#provider-select",
                3: "#time-window-select",
                4: "#output-style-select",
                5: "#abstract-select",
            }
            widget_id = step_map.get(step)
            if widget_id:
                self.query_one(widget_id, OptionList).focus()

    def _populate_models(self) -> None:
        provider = self.values.get("provider", "openai")
        models = config.PROVIDERS[provider]["models"]
        model_list = self.query_one("#model-select", OptionList)
        model_list.clear_options()
        for m in models:
            model_list.add_option(Option(m, id=m))

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        control_id = event.option_list.id
        opt_id = event.option.id

        if control_id == "provider-select":
            self.values["provider"] = opt_id
            self._go_to_step(1)
        elif control_id == "model-select":
            self.values["model"] = opt_id
            self._go_to_step(3)
        elif control_id == "time-window-select":
            self.values["time_window"] = int(opt_id)
            self._go_to_step(4)
        elif control_id == "output-style-select":
            self.values["output_style"] = opt_id
            self._go_to_step(5)
        elif control_id == "abstract-select":
            self.values["show_abstract"] = opt_id == "true"
            self._finish()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self.values["api_key"] = event.value
            self._go_to_step(2)

    def action_prev_step(self) -> None:
        if self.current_step > 0:
            self._go_to_step(self.current_step - 1)

    def _finish(self) -> None:
        provider = self.values.get("provider", "openai")
        provider_info = config.PROVIDERS[provider]

        cfg = {
            "llm": {
                "provider": provider,
                "api_base": provider_info["api_base"],
                "api_key": self.values.get("api_key", ""),
                "model": self.values.get(
                    "model", provider_info["default_model"]
                ),
            },
            "feed": {
                "time_window": self.values.get("time_window", 2),
                "top_n": 10,
                "output_style": self.values.get("output_style", "compact"),
                "show_abstract": self.values.get("show_abstract", False),
            },
            "keywords": {
                "presets": dict(config.DEFAULT_PRESETS),
            },
        }

        config.save(cfg)
        self.dismiss(cfg)
