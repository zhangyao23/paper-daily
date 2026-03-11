from __future__ import annotations

_MAX_TEXT_LEN = 80000


def build_deep_review_prompt(paper_id: str, full_text: str) -> list[dict]:
    text = full_text[: _MAX_TEXT_LEN]
    if len(full_text) > _MAX_TEXT_LEN:
        text += "\n\n[Text truncated due to length]"

    system_content = (
        "You are a strict top-tier conference reviewer. "
        "Extract model architecture, innovation points, and experimental evidence "
        "from the paper text. Focus on Introduction, Method, and Experiments.\n\n"
        "Execute internally: (1) Architecture Decomposition - backbone, modules, "
        "input/output format. (2) Innovation Localization - motivation, main changes "
        "vs baseline, 1-3 technical contributions. (3) Experiment Verification - "
        "key metrics, ablation presence, comparison baselines.\n\n"
        "Hard constraints: Base analysis strictly on paper content. "
        "If experiments are insufficient or logic has clear flaws, set risk_level to "
        '"high". Only extract information present in the paper. Use null for missing '
        "fields. Output raw JSON only, no markdown wrapper.\n\n"
        "Output structure:\n"
        '{"paper_id": "string", "architecture": {"backbone": "string|null", '
        '"modules": ["string"], "input_format": "string|null", '
        '"output_format": "string|null"}, "innovations": '
        '[{"description": "string", "section_ref": "string|null"}], '
        '"experiments": {"datasets": [{"name": "string", "metric": "string", '
        '"value": "string|number"}], "ablation_present": true|false, '
        '"comparison_baselines": ["string"]}, '
        '"risk_level": "low"|"medium"|"high", "risk_reason": "string|null"}'
    )

    return [
        {"role": "system", "content": system_content},
        {
            "role": "user",
            "content": f"Paper ID: {paper_id}\n\nFull text:\n{text}",
        },
    ]
