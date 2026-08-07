"""Anthropic Claude client helpers."""

from __future__ import annotations

import base64

from anthropic import Anthropic

from app.config import get_anthropic_api_key, get_anthropic_model


def _detect_image_media_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
        return "image/webp"
    return "image/png"


def _extract_text_response(content: list) -> str:
    text_parts = [
        block.text
        for block in content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ]
    return "\n".join(text_parts).strip()


def call_claude(prompt: str, image_bytes: bytes | None = None) -> str:
    """Call Claude Messages API with optional image attachment.

    Raises:
        RuntimeError: If ANTHROPIC_API_KEY is not set.
    """
    api_key = get_anthropic_api_key()
    client = Anthropic(api_key=api_key)

    if image_bytes is None:
        content: list[dict] = [{"type": "text", "text": prompt}]
    else:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _detect_image_media_type(image_bytes),
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                },
            },
            {"type": "text", "text": prompt},
        ]

    message = client.messages.create(
        model=get_anthropic_model(),
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
    return _extract_text_response(message.content)
