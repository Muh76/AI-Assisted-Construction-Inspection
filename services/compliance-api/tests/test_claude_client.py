from unittest.mock import MagicMock, patch

import pytest

from app.ai.claude_client import call_claude, _detect_image_media_type


def test_call_claude_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        call_claude("hello")


def test_call_claude_text_only(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_message = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "ok"
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("app.ai.claude_client.Anthropic", return_value=mock_client):
        result = call_claude("Summarize this.")

    assert result == "ok"
    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["messages"][0]["content"] == [
        {"type": "text", "text": "Summarize this."}
    ]


def test_call_claude_with_image(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8

    mock_message = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "corridor 1100mm"
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("app.ai.claude_client.Anthropic", return_value=mock_client):
        result = call_claude("Find widths", image_bytes=png_bytes)

    assert result == "corridor 1100mm"
    content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    assert content[0]["source"]["type"] == "base64"
    assert content[1] == {"type": "text", "text": "Find widths"}


def test_detect_image_media_type():
    assert _detect_image_media_type(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert _detect_image_media_type(b"\xff\xd8\xff\xe0") == "image/jpeg"
