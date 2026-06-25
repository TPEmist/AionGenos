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
    """Manages the conversation history of a single episode.

    Sliding-window context strategy (A fix for F30/F43):
    Run b6783e98 / 7c29e8ae showed teacher CoT degrading to schema
    violations after ~25 rounds — the fully-accumulated thoughts +
    critic feedbacks blow past the model's ability to keep emitting
    the strict response format. We keep:
      - the system prompt (folded into the original first user turn)
      - the *first* user turn intact (sets the task)
      - the most recent ``recent_window`` user/assistant pairs

    Critic feedback already summarises prior rounds' deltas so dropping
    older raw thoughts loses little signal. Image URLs are stripped from
    all but the latest user turn (unchanged behaviour).
    """

    DEFAULT_RECENT_WINDOW: int = 6  # keep first turn + last 6 user/assistant pairs

    def __init__(self, system_prompt: str, recent_window: int = DEFAULT_RECENT_WINDOW):
        self.system_prompt = system_prompt
        self.messages: list[dict] = []
        self.recent_window = recent_window

    def _prune_to_window(self) -> None:
        """Drop middle history but keep the first user turn + last K pairs."""
        # Keep first message (it has the system prompt baked in) + the last
        # ``2 * recent_window`` messages (each round = 1 user + 1 assistant).
        keep_tail = 2 * self.recent_window
        if len(self.messages) <= keep_tail + 1:
            return  # nothing to prune yet

        first = self.messages[0]
        tail = self.messages[-keep_tail:]
        # Make sure tail starts on a user turn so the prompt is well-formed.
        while tail and tail[0]["role"] != "user":
            tail = tail[1:]
        self.messages = [first] + tail

    def append_user_turn(
        self,
        user_prompt: str,
        image_base64: Optional[str] = None,
        preamble_text: Optional[str] = None,
        preamble_image_base64_list: Optional[list[str]] = None,
    ):
        """Append a user turn to the conversation history, keeping only the latest image.

        ``preamble_text`` / ``preamble_image_base64_list`` are only honored on the
        FIRST turn of the conversation (when ``messages`` is empty). They carry
        Phase 4 memory injection: a block of retrieved past episodes (text +
        their init images) is glued in BEFORE the current scene image and prompt
        so the VLM can do visual analogy against past experiences.
        """
        # Strip/remove image_url from all existing user messages to conserve context window
        for msg in self.messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                msg["content"] = [part for part in msg["content"] if part["type"] == "text"]

        user_content: list[dict] = []
        is_first_turn = len(self.messages) == 0
        if is_first_turn:
            # First turn: fold system prompt into user message for Gemma-4 compatibility
            user_content.append({"type": "text", "text": self.system_prompt + "\n\n"})

            # Phase 4: prepend retrieved-memory preamble + past-episode images
            if preamble_text:
                user_content.append({"type": "text", "text": preamble_text + "\n"})
            for b64 in preamble_image_base64_list or []:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })

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
        # Prune AFTER each completed round so the next user_turn sees a
        # bounded context. We do this here (not in append_user_turn) so the
        # pair is added atomically before pruning.
        self._prune_to_window()


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

