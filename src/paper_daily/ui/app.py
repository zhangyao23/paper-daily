from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.theme import Theme

from paper_daily import config

_THEME = Theme(
    name="paper-daily",
    primary="#00acc1",
    secondary="#006064",
    accent="#00bcd4",
    dark=True,
)


class PaperDailyApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "paper-daily"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.register_theme(_THEME)
        self.theme = "paper-daily"

    def on_mount(self) -> None:
        if not config.exists():
            from paper_daily.ui.screens.wizard import WizardScreen

            self.push_screen(WizardScreen(), callback=self._on_wizard_done)
        else:
            self.cfg = config.load()
            self._show_main_menu()

    def _on_wizard_done(self, cfg: dict) -> None:
        self.cfg = cfg
        self._show_main_menu()

    def _show_main_menu(self) -> None:
        from paper_daily.ui.screens.main_menu import MainMenuScreen

        self.push_screen(MainMenuScreen(self.cfg))


def run() -> None:
    PaperDailyApp().run()
