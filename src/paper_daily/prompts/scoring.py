from __future__ import annotations


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
                "You are a research paper relevance scorer. "
                "Given a list of arxiv papers and a set of interest keywords, "
                "score each paper's relevance from 0.00 to 1.00.\n\n"
                "Rules:\n"
                "- 1.00 = directly about the topic\n"
                "- 0.70-0.99 = closely related\n"
                "- 0.30-0.69 = somewhat related\n"
                "- 0.00-0.29 = not related\n\n"
                "Respond ONLY with a JSON array of objects, each with "
                '"index" (int) and "score" (float). No explanation.'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Interest keywords: {keywords_str}\n\n"
                f"Papers:\n{papers_block}\n\n"
                "Score each paper. Respond with JSON array only."
            ),
        },
    ]
