from __future__ import annotations

from pathlib import Path

from textual.app import App

from paper_daily import config


class PaperDailyApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "paper-daily"

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
