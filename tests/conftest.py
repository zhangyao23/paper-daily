import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Tests must neither use private configuration nor make paid/network calls."""
    from paper_daily import config
    from paper_daily.core import llm
    from paper_daily.pipeline import pdf_fetcher

    monkeypatch.setenv("PAPER_DAILY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setattr(config, "HISTORY_FILE", tmp_path / "history.json")
    monkeypatch.setattr(pdf_fetcher, "CACHE_DIR", tmp_path / "cache")

    def forbidden(*args, **kwargs):
        raise AssertionError("Network/LLM calls must be explicitly mocked")

    original_connect = socket.socket.connect

    def offline_connect(sock, address):
        # Windows asyncio implements its internal wakeup pipe with loopback sockets.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(sock, address)
        forbidden()

    monkeypatch.setattr(socket.socket, "connect", offline_connect)
    monkeypatch.setattr(llm, "chat", forbidden)
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def paper():
    return {"arxiv_id": "2401.00001v1", "title": "Synthetic fixture: A & B",
            "authors": ["Example Author"], "abstract": "A synthetic test abstract.",
            "published": "2024-01-01T00:00:00Z", "metadata_source": "synthetic_fixture",
            "url": "https://arxiv.org/abs/2401.00001v1"}
