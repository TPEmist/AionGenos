"""D11 Amendment 17 (DRAFT) — text vs image ablation of the retrieved context.

The C_retrieval preamble carries two components per retrieved episode: the
lesson text and the episode's init_pre image. A17 removes exactly one of them.
Retrieval itself is unchanged: the same records are selected by the same score,
including the image embedding. Only what reaches the prompt changes.

  text_only  : images dropped; the "Image i: ..." lines and the header clause
               that announces them are removed.
  image_only : lesson lines dropped; the header clause and the closing
               "past lessons" reference are reworded to "past episodes".

Every other line is byte-identical to C_retrieval's preamble: the state
anchors, outcome and round count.

This is a wrapper around the frozen retriever.py (never edited). Wiring:
scripts/run_collect.py --a17_context. When the flag is unset, run_collect never
constructs this class, so the L0/L2/D11 paths are unchanged.
"""
from __future__ import annotations

import dataclasses
import re

from aiongenos.memory.retriever import MemoryPreamble, MemoryRetriever

MODES = ("text_only", "image_only")

_IMAGE_LINE = re.compile(r"^  Image \d+: the scene at the start of that episode\n", re.MULTILINE)
_LESSON_LINE = re.compile(r"^  lesson     : .*\n", re.MULTILINE)
_HDR_IMAGE_CLAUSE = "what the scene looked like at start, "
_HDR_LESSON_CLAUSE = ", and a one-paragraph lesson you wrote afterwards"
_TAIL_LESSONS = "Use the past lessons above"
_TAIL_EPISODES = "Use the past episodes above"


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"A17: expected exactly one {old!r} in the preamble")
    return text.replace(old, new)


def ablate(pre: MemoryPreamble, mode: str) -> MemoryPreamble:
    """Return a NEW preamble with one component removed (input untouched)."""
    if mode not in MODES:
        raise ValueError(f"A17 mode must be one of {MODES}, got {mode!r}")
    if pre.is_empty:
        return pre
    n = len(pre.retrieved_records)
    text = pre.prelude_text
    if mode == "text_only":
        text, k = _IMAGE_LINE.subn("", text)
        if k != n:
            raise ValueError(f"A17 text_only: removed {k} image lines for {n} records")
        text = _replace_once(text, _HDR_IMAGE_CLAUSE, "")
        return dataclasses.replace(pre, prelude_text=text, past_image_base64_list=[])
    text, k = _LESSON_LINE.subn("", text)
    if k != n:
        raise ValueError(f"A17 image_only: removed {k} lesson lines for {n} records")
    if any(r.text_lesson.strip() and r.text_lesson.strip() in text for r in pre.retrieved_records):
        raise ValueError("A17 image_only: lesson text survived (multi-line lesson?)")
    text = _replace_once(text, _HDR_LESSON_CLAUSE, "")
    text = _replace_once(text, _TAIL_LESSONS, _TAIL_EPISODES)
    return dataclasses.replace(pre, prelude_text=text)


class AblatedMemoryRetriever:
    """Same interface as MemoryRetriever.retrieve_for_episode; ablates the result."""

    def __init__(self, inner: MemoryRetriever, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"A17 mode must be one of {MODES}, got {mode!r}")
        self.inner = inner
        self.mode = mode

    def retrieve_for_episode(self, *args, **kwargs) -> MemoryPreamble:
        return ablate(self.inner.retrieve_for_episode(*args, **kwargs), self.mode)

    def __getattr__(self, name: str):
        return getattr(self.inner, name)
