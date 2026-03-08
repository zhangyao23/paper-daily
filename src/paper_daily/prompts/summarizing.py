from __future__ import annotations


def build_summary_prompt(title: str, abstract: str, detailed: bool = False) -> list[dict]:
    length_hint = "3-5 sentences" if detailed else "1-2 sentences"

    return [
        {
            "role": "system",
            "content": (
                "You are a research paper summarizer. "
                "Given a paper's title and abstract, write a concise summary "
                f"in {length_hint} that captures the key contribution and results. "
                "Focus on what is novel and why it matters. "
                "Write in plain English, avoid jargon where possible."
            ),
        },
        {
            "role": "user",
            "content": f"Title: {title}\n\nAbstract: {abstract}",
        },
    ]
