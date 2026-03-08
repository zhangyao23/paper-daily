from __future__ import annotations

from openai import OpenAI


_TIMEOUT = 60.0
_MAX_RETRIES = 2


def chat(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
) -> str:
    client = OpenAI(
        base_url=api_base,
        api_key=api_key,
        max_retries=_MAX_RETRIES,
        timeout=_TIMEOUT,
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content
