"""Phase 4 D11 — action-only constrained decoding for student inference.

The student LoRA is trained with target format:
    PAST_LESSONS (from similar past attempts):
      (1) [✓/✗] {lesson_1}
      (2) [✓/✗] {lesson_2}
      (3) [✓/✗] {lesson_3}

    {teacher's original THOUGHT block}
    LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>
    RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>
    STOP: <true|false>

At inference time we do NOT want the student to spend tokens emitting the
PAST_LESSONS block or the free-form THOUGHT (that would defeat the
"high-Hz, context-free student" claim). Instead we pre-fill the assistant
message up to "LEFT_TARGET_POS:" and let the student generate only the
coordinate lines + STOP token.

Approach (llama.cpp OpenAI-compatible endpoint):
  - The final message we send is a user message with the current scene.
  - We append an assistant message that PREFILLS all tokens up to and
    including the line ``LEFT_TARGET_POS: `` (with trailing space).
  - llama.cpp treats a trailing-assistant-message as "continue generating
    this response" — model resumes from there.
  - We set stop=["STOP: true", "STOP: false"] so it terminates once the
    STOP line is produced.

This preserves paper claim (rationale internalised, action-only emit) while
letting llama.cpp handle everything server-side. No custom sampling.

Fallback: if the endpoint doesn't support assistant prefill continuation,
callers can pass ``skip_prefill=True`` to just add a stop token after the
first ``LEFT_TARGET_POS:`` boundary — the response will still contain the
rationale but at least stops before the second half. Slower but safe.
"""

from __future__ import annotations

from typing import Optional


# Prefill string that the assistant will "continue from". Contains the full
# rationale-shaped stub the model was trained to emit — but since the
# rationale is dependent on retrieved memories that the student doesn't
# have, we use a placeholder stub. Alternatively we drop all rationale
# scaffolding and just start at LEFT_TARGET_POS: — the trained weights
# should still produce good coords because the rationale-generating
# hidden-state work was baked in at training time.
#
# Minimal prefill (recommended — puts the model in "action emission" state):
ACTION_ONLY_PREFILL = "LEFT_TARGET_POS: "

# Stop tokens: sample until STOP line is produced.
STOP_TOKENS = ("STOP: true", "STOP: false")


def build_constrained_payload(
    base_payload: dict,
    *,
    prefill: str = ACTION_ONLY_PREFILL,
    stop_tokens: tuple[str, ...] = STOP_TOKENS,
    max_action_tokens: int = 60,
) -> dict:
    """Given a normal chat-completions payload (from build_chat_request),
    convert it into a constrained-decoding request that starts the model
    output at ``prefill`` and stops on any ``stop_tokens``.

    Args:
        base_payload: dict returned by build_chat_request(...). We mutate
            a shallow copy of ``messages`` — the input is not modified.
        prefill: assistant-message content the model resumes from.
        stop_tokens: server-side stop sequences.
        max_action_tokens: budget for action + STOP line. ~60 tokens covers
            "X=... Y=... Z=... X=... Y=... Z=... STOP: true" comfortably.

    Returns:
        New payload dict ready to send to /v1/chat/completions.
    """
    new_messages = list(base_payload.get("messages", []))
    # Append an assistant message that acts as a prefill.
    new_messages.append({"role": "assistant", "content": prefill})

    return {
        **base_payload,
        "messages": new_messages,
        "stop": list(stop_tokens),
        "max_tokens": max_action_tokens,
        # Some llama.cpp builds honor this; harmless when they don't.
        "continue": True,
    }


def reassemble_response(prefill: str, model_completion: str) -> str:
    """The server returns only the tokens generated after the prefill.
    Concatenate prefill + completion so the downstream parser sees the
    canonical format it expects.

    Also normalizes trailing whitespace so parse_stage1 works.
    """
    return prefill + model_completion.rstrip()
