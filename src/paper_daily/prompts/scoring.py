from __future__ import annotations

DIMENSIONS = [
    ("relevance", 0.25),
    ("novelty", 0.20),
    ("depth", 0.15),
    ("utility", 0.15),
    ("rigor", 0.10),
    ("clarity", 0.10),
    ("impact", 0.05),
]

DIMENSION_KEYS = [d[0] for d in DIMENSIONS]
DIMENSION_WEIGHTS = {d[0]: d[1] for d in DIMENSIONS}


def build_scoring_prompt(
    papers: list[dict], keywords: list[str]
) -> list[dict]:
    paper_entries = []
    for i, p in enumerate(papers):
        paper_entries.append(
            f"[{i}] Title: {p['title']}\nAbstract: {p['abstract']}"
        )
    papers_block = "\n\n".join(paper_entries)
    keywords_str = ", ".join(keywords)

    return [
        {
            "role": "system",
            "content": (
                "You are a research paper scoring system. "
                "Given arxiv papers and interest keywords, "
                "score each paper on 7 dimensions (0.00 to 1.00).\n\n"
                "Dimensions:\n"
                "- relevance: topic match to user keywords "
                "(1.0 = directly about it, 0.0 = unrelated)\n"
                "- novelty: new method/framework/finding vs incremental/survey "
                "(1.0 = groundbreaking, 0.0 = purely incremental)\n"
                "- depth: how deeply the paper treats the relevant topic "
                "(1.0 = core contribution, 0.0 = superficial mention)\n"
                "- utility: practical value, code release, tools, applications "
                "(1.0 = open-source tool/benchmark, 0.0 = purely theoretical)\n"
                "- rigor: experimental quality, baselines, ablations "
                "(1.0 = comprehensive evaluation, 0.0 = no experiments)\n"
                "- clarity: abstract quality, motivation, readability "
                "(1.0 = crystal clear, 0.0 = incomprehensible)\n"
                "- impact: breadth of applicability "
                "(1.0 = broadly applicable, 0.0 = extremely niche)\n\n"
                "Respond ONLY with a JSON array. Each element must have "
                '"index" (int) and one float field per dimension. '
                "Example for 2 papers:\n"
                "[{\"index\": 0, \"relevance\": 0.90, \"novelty\": 0.75, "
                "\"depth\": 0.80, \"utility\": 0.60, \"rigor\": 0.70, "
                "\"clarity\": 0.85, \"impact\": 0.65}, "
                "{\"index\": 1, \"relevance\": 0.40, \"novelty\": 0.50, "
                "\"depth\": 0.35, \"utility\": 0.20, \"rigor\": 0.55, "
                "\"clarity\": 0.70, \"impact\": 0.30}]\n\n"
                "Output the JSON array ONLY. No explanation, no markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Interest keywords: {keywords_str}\n\n"
                f"Papers:\n{papers_block}\n\n"
                "Score each paper on all 7 dimensions. "
                "Respond with JSON array only, no explanation."
            ),
        },
    ]
