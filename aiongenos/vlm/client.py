"""VLM HTTP client — async httpx wrapper for llama-server /v1/chat/completions.

Handles base64 image encoding, retry policy, and structured request building.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0  # seconds (teacher CoT can be slow)
MAX_RETRIES = 2


def encode_image_base64(image_path: str | Path) -> str:
    """Read an image file and return base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_image_bytes_base64(image_bytes: bytes) -> str:
    """Encode raw image bytes to base64."""
    return base64.b64encode(image_bytes).decode("utf-8")


def build_chat_request(
    system_prompt: str,
    user_prompt: str,
    image_base64: Optional[str] = None,
    image_base64_list: Optional[list[str]] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> dict:
    """Build a /v1/chat/completions request payload.

    Args:
        system_prompt: System message.
        user_prompt: User message text.
        image_base64: Single base64-encoded image (optional).
        image_base64_list: Multiple base64-encoded images (optional).
        temperature: Sampling temperature.
        max_tokens: Max response tokens.

    Returns:
        Request body dict compatible with llama-server.
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Build user content (text + optional images)
    user_content: list[dict] = []

    # Add images
    images = []
    if image_base64:
        images.append(image_base64)
    if image_base64_list:
        images.extend(image_base64_list)

    for img_b64 in images:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })

    # Add text
    user_content.append({"type": "text", "text": user_prompt})

    messages.append({"role": "user", "content": user_content})

    return {
        "model": "default",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }


async def call_vlm(
    url: str,
    system_prompt: str,
    user_prompt: str,
    image_base64: Optional[str] = None,
    image_base64_list: Optional[list[str]] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Call VLM endpoint and return the response text.

    Args:
        url: Base URL (e.g. "http://10.80.9.148:18888").
        system_prompt: System prompt.
        user_prompt: User prompt.
        image_base64: Optional single image.
        image_base64_list: Optional multiple images.
        temperature: Sampling temperature.
        max_tokens: Max tokens.
        timeout: Request timeout in seconds.

    Returns:
        Response text from the model.

    Raises:
        httpx.HTTPStatusError: On non-2xx response.
        ValueError: If response format is unexpected.
    """
    endpoint = f"{url.rstrip('/')}/v1/chat/completions"
    payload = build_chat_request(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        image_base64=image_base64,
        image_base64_list=image_base64_list,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

                # Extract response text
                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("No choices in VLM response")

                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise ValueError("Empty content in VLM response")

                return content

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
            last_error = e
            logger.warning(f"VLM call attempt {attempt + 1}/{MAX_RETRIES + 1} failed: {e}")
            if attempt < MAX_RETRIES:
                continue

    raise last_error  # type: ignore[misc]


def call_vlm_sync(
    url: str,
    system_prompt: str,
    user_prompt: str,
    image_base64: Optional[str] = None,
    image_base64_list: Optional[list[str]] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Synchronous wrapper for call_vlm."""
    import asyncio
    return asyncio.run(call_vlm(
        url=url,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        image_base64=image_base64,
        image_base64_list=image_base64_list,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    ))
