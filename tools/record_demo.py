"""Record real Textual interactions with synthetic, isolated, offline services.

Run from the checkout: uv run --group demo tools/record_demo.py
Install Playwright Chromium first, or pass --browser-channel msedge / chrome.
Only public images go to assets/; working files stay in ignored .local-audit/.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack
import copy
from datetime import datetime
from html import escape
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from playwright.async_api import async_playwright
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from textual.widgets import Input, Static

from paper_daily import config
from paper_daily.core.reading_list import ReadingList
from paper_daily.prompts.scoring import DIMENSION_KEYS
from paper_daily.ui.app import PaperDailyApp
from paper_daily.ui.screens.library import LibraryScreen
from paper_daily.ui.screens.results import ResultsScreen

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PAPER = {
    "arxiv_id": "2401.00001v1",
    "title": "Synthetic example: Reliable Research Assistants",
    "authors": ["Example Author"],
    "abstract": "Synthetic metadata for a UI demonstration, not a real paper claim.",
    "published": "2024-01-01T00:00:00Z",
    "url": "https://arxiv.org/abs/2401.00001v1",
    "metadata_source": "synthetic_fixture",
}


def fixture_chat(api_base, api_key, model, messages, **kwargs):
    system = messages[0]["content"]
    if "scoring system" in system:
        return json.dumps([{"index": 0, **dict.fromkeys(DIMENSION_KEYS, 0.85)}])
    if "summarizer" in system:
        return "Synthetic summary for this demo. Scores and metadata are fixtures, not research findings."
    if "conference reviewer" in system:
        assert "Abstract only" in messages[1]["content"]
        return json.dumps({"innovations": [], "experiments": {"ablation_present": None},
                           "risk_reason": "Cannot assess experiments from this synthetic abstract."})
    if "senior editor" in system:
        return (
            "## Synthetic example: Reliable Research Assistants\n\n"
            "**Offline fixture output, not a real paper review.**\n\n"
            "### Evidence boundary\n\n"
            "Only the synthetic abstract was available. The PDF download was deliberately "
            "made to fail for this demonstration.\n\n"
            "### Experiments\n\n"
            "Not established by the supplied abstract. No claim of full-paper verification."
        )
    raise AssertionError("Unexpected LLM request in demo")


def document_svg(renderable, title: str) -> str:
    console = Console(record=True, width=100, force_terminal=True, file=StringIO())
    console.print(renderable)
    return console.export_svg(title=title)


async def capture_flow(work: Path) -> list[dict]:
    cfg = copy.deepcopy(config.DEFAULTS)
    cfg["llm"]["api_key"] = "offline-demo-placeholder"
    frames = []
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {"PAPER_DAILY_DATA_DIR": "demo-data", "COLORTERM": "truecolor"}))
        os.environ.pop("NO_COLOR", None)  # Record the app's normal color theme, even in CI.
        stack.enter_context(patch("paper_daily.config.exists", return_value=True))
        stack.enter_context(patch("paper_daily.config.load", return_value=cfg))
        stack.enter_context(patch("paper_daily.config.resolve_api_key", return_value="offline-demo-placeholder"))
        stack.enter_context(patch("paper_daily.config.HISTORY_FILE", Path("demo-data/history.json")))
        stack.enter_context(patch("paper_daily.pipeline.arxiv.search", return_value=[PAPER]))
        stack.enter_context(patch("paper_daily.pipeline.pdf_fetcher.download_pdf", return_value=None))
        stack.enter_context(patch("paper_daily.core.llm.chat", side_effect=fixture_chat))
        stack.enter_context(patch("httpx.get", side_effect=AssertionError("Demo must stay offline")))
        stack.enter_context(patch("pyperclip.copy"))  # Never replace the user's real clipboard.
        app = PaperDailyApp()
        async with app.run_test(size=(100, 32)) as pilot:
            async def shot(caption, *, svg=None, still=None, duration=2600):
                await pilot.pause()
                content = svg if svg is not None else app.export_screenshot(title="Paper Daily | Offline fixture demo")
                (work / f"{len(frames):02d}.svg").write_text(content, encoding="utf-8")
                frames.append({"caption": caption, "svg": content, "still": still, "duration": duration})

            await pilot.press("space")
            await shot("01  Select a keyword preset with Space, then press Enter")
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, ResultsScreen)
            await shot("02  Results explicitly label ranking and summaries as abstract-only", still="results-library.png")
            assert await pilot.click("#save-paper-0")
            assert len(ReadingList().load()) == 1
            await shot("03  Click Save #1 to reading list — a local starred record is created")
            await pilot.press("b")
            bib = next(Path("demo-data/exports").glob("results-*.bib"))
            assert "@misc{arxiv_240100001" in bib.read_text(encoding="utf-8")
            await shot("04  Press B to export BibTeX from the displayed results")
            await shot("05  Exported .bib file — metadata and source URL, no LLM completion",
                       svg=document_svg(Syntax(bib.read_text(encoding="utf-8"), "bibtex", theme="monokai", padding=1),
                                        "Exported BibTeX | File preview"))
            await pilot.press("l")
            assert isinstance(app.screen, LibraryScreen)
            await shot("06  Press L to open the reading list; new papers start unread")
            await pilot.press("r")
            assert ReadingList().load()[0]["read"]
            await shot("07  Press R to mark the selected paper read — state is saved locally", still="reading-list.png")
            await pilot.press("f")
            assert not ReadingList().load()[0]["starred"]
            await shot("08  Press F to unstar; the paper and its read state are retained")
            await pilot.press("e")
            backup = next(Path("demo-data/exports").glob("reading-list-*.json"))
            assert json.loads(backup.read_text(encoding="utf-8"))["items"][0]["read"]
            await shot("09  Press E to export a JSON backup, including reading state")
            await pilot.press("i")
            app.screen.query_one("#import-path", Input).value = backup.as_posix()
            await shot("10  Press I and enter a JSON backup path, then press Enter")
            await pilot.press("enter")
            assert len(ReadingList().load()) == 1 and ReadingList().load()[0]["read"]
            assert "Imported" in str(app.screen.query_one("#library-status", Static).render())
            await shot("11  Import merges the duplicate — one paper, with read state preserved")
            await pilot.press("escape", "d")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, ResultsScreen)
            report = next(Path("demo-data/exports").glob("digest-*.md"))
            content = report.read_text(encoding="utf-8")
            assert "Abstract only; FALLBACK" in content
            await shot("12  Back to results: press D to generate and save a Markdown report")
            await shot("13  Saved report: the evidence manifest discloses PDF-to-abstract fallback",
                       svg=document_svg(Markdown(content), "Saved Markdown report | File preview"),
                       still="report-evidence.png", duration=5000)
    return frames


async def render_frames(frames: list[dict], work: Path, channel: str | None) -> None:
    images = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel=channel, headless=True)
        context = await browser.new_context(viewport={"width": 1200, "height": 1020}, device_scale_factor=1)
        await context.route("**/*", lambda route: route.abort())
        page = await context.new_page()
        for index, frame in enumerate(frames):
            await page.set_content(
                "<html><head><style>"
                "*{box-sizing:border-box}body{margin:0;background:#0c131b;color:#eef5fa;font:20px Arial,sans-serif}"
                "main{width:1200px;height:1020px;padding:22px}header{height:100px}"
                "h1{font-size:25px;margin:0 0 13px}p{font-size:16px;color:#9fb4c4;margin:0}"
                "section{height:870px;display:flex;align-items:flex-start;justify-content:center}"
                "svg{width:100%;max-height:870px}svg text{font-family:Consolas,'Liberation Mono',monospace!important}"
                "</style></head><body><main><header>"
                f"<h1>{escape(frame['caption'])}</h1>"
                "<p>REAL TERMINAL UI / FILE PREVIEWS · SYNTHETIC DATA · MOCKED NETWORK &amp; LLM · NO API KEY</p>"
                f"</header><section>{frame['svg']}</section></main></body></html>"
            )
            png = await page.screenshot()
            (work / f"{index:02d}.png").write_bytes(png)
            images.append(Image.open(BytesIO(png)).convert("RGB"))
            if frame["still"]:
                (ASSETS / frame["still"]).write_bytes(png)
        await browser.close()
    images[0].save(ASSETS / "demo-library.gif", save_all=True, append_images=images[1:],
                   duration=[f["duration"] for f in frames], loop=0, optimize=True, disposal=2)
    (work / "manifest.json").write_text(json.dumps([
        {key: value for key, value in frame.items() if key != "svg"} for frame in frames
    ], indent=2), encoding="utf-8")


async def main(channel: str | None) -> None:
    work = ROOT / ".local-audit" / ("demo-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    work.mkdir(parents=True)
    original_cwd = Path.cwd()
    try:
        os.chdir(work)
        frames = await capture_flow(work)
        await render_frames(frames, work, channel)
    finally:
        os.chdir(original_cwd)
    print(f"Recorded {len(frames)} verified steps: {ASSETS / 'demo-library.gif'}")
    print(f"Private working frames and generated fixture files: {work}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-channel", default=None, choices=["msedge", "chrome", "chromium"])
    asyncio.run(main(parser.parse_args().browser_channel))
