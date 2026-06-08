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

DEFAULT_TIMEOUT = 300.0  # seconds (teacher CoT can be slow)
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
    # Gemma 4 / llama.cpp: fold system prompt into the user turn so the image
    # token and all instructions are co-located in a single message.  A
    # separate {"role": "system"} entry causes the vision token injector to
    # skip image embedding, producing empty responses.
    messages = []

    # Build user content (system prefix text + optional images + user text)
    user_content: list[dict] = []

    # Leading text block carries system instructions
    user_content.append({"type": "text", "text": system_prompt + "\n\n"})

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

    # Main user prompt
    user_content.append({"type": "text", "text": user_prompt})

    messages.append({"role": "user", "content": user_content})

    return {
        "model": "default",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }


class EpisodeConversation:
    """Manages the conversation history of a single episode."""
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.messages: list[dict] = []

    def append_user_turn(self, user_prompt: str, image_base64: Optional[str] = None):
        """Append a user turn to the conversation history, keeping only the latest image."""
        # Strip/remove image_url from all existing user messages to conserve context window
        for msg in self.messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                msg["content"] = [part for part in msg["content"] if part["type"] == "text"]

        user_content: list[dict] = []
        if len(self.messages) == 0:
            # First turn: fold system prompt into user message for Gemma-4 compatibility
            user_content.append({"type": "text", "text": self.system_prompt + "\n\n"})
        
        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
            })
        
        user_content.append({"type": "text", "text": user_prompt})
        self.messages.append({"role": "user", "content": user_content})

    def append_assistant_turn(self, assistant_response: str):
        """Append an assistant response to the conversation history."""
        self.messages.append({"role": "assistant", "content": assistant_response})


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


async def call_vlm_history(
    url: str,
    conversation: EpisodeConversation,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Call VLM endpoint with full conversation history."""
    endpoint = f"{url.rstrip('/')}/v1/chat/completions"
    payload = conversation.to_payload(temperature=temperature, max_tokens=max_tokens)

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("No choices in VLM response")

                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise ValueError("Empty content in VLM response")

                return content

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
            last_error = e
            logger.warning(f"VLM history call attempt {attempt + 1}/{MAX_RETRIES + 1} failed: {e}")
            if attempt < MAX_RETRIES:
                continue

    raise last_error  # type: ignore[misc]


def call_vlm_history_sync(
    url: str,
    conversation: EpisodeConversation,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Synchronous wrapper for call_vlm_history."""
    import asyncio
    return asyncio.run(call_vlm_history(
        url=url,
        conversation=conversation,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    ))


# Add payload helper method to EpisodeConversation
def _to_payload(self, temperature: float = 0.7, max_tokens: int = 1024) -> dict:
    return {
        "model": "default",
        "messages": self.messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

EpisodeConversation.to_payload = _to_payload

