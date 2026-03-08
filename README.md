# Paper Daily

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=uv&logoColor=white)

**Your daily arxiv digest, powered by LLM.**

An interactive terminal tool that searches arxiv, scores papers with LLM across 7 dimensions, and generates concise summaries. Clone, run, read.

<div align="center">

![demo](assets/demo.gif)

</div>

---

## Features

- **16 keyword presets** covering major LLM research topics (agents, RAG, reasoning, alignment, ...), plus custom keywords
- **7-dimension LLM scoring** — relevance, novelty, depth, utility, rigor, clarity, impact — with weighted ranking
- **Multi-provider support** — OpenAI, Gemini, OpenRouter, all through OpenAI-compatible API
- **Setup wizard on first launch** — select provider, enter API key, pick model, done
- **Activity calendar** — GitHub-style heatmap tracking your reading streaks

---

## Quick Start

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
git clone https://github.com/Lin5412/paper-daily.git
cd paper-daily
uv run paper-daily
```

First run launches the setup wizard automatically. No manual config needed.

---

## Usage

### Main Menu

Select keyword presets with `space`, enter custom keywords, then press `enter` to fetch.

![main menu](assets/main-menu.png)

### Results

Papers are ranked by weighted score. Each card shows score, title, authors, summary, and arxiv link.

![results](assets/results.png)

### Settings

Press `s` to open settings. Three tabs:

- **Info** — version and project info
- **Config** — change provider, model, time window, output style
- **Calendar** — activity heatmap with current and longest streaks

![settings](assets/settings.png)

---

## License

[MIT](LICENSE)
