"""A17 ablation: each mode removes exactly one component; everything else byte-identical."""
from pathlib import Path

import pytest

from aiongenos.memory import retriever as R
from aiongenos.memory.a17_ablation import AblatedMemoryRetriever, ablate
from aiongenos.memory.recap_buffer import RecapBuffer

BUF = Path("workspace/recaps_d10_frozen_c_retrieval")


@pytest.fixture(scope="module")
def pre() -> R.MemoryPreamble:
    if not BUF.exists():
        pytest.skip("frozen buffer not unpacked")
    b = RecapBuffer(root=str(BUF))
    b.load()
    recs = b._records[:3]
    sims = [0.9, 0.8, 0.7]
    return R.MemoryPreamble(prelude_text=R._format_preamble_text(recs, sims),
                            past_image_base64_list=["a", "b", "c"],
                            retrieved_records=tuple(recs), similarities=tuple(sims))


def _diff_lines(a: str, b: str) -> set[str]:
    return set(a.splitlines()) - set(b.splitlines())


def test_text_only(pre):
    out = ablate(pre, "text_only")
    assert out.past_image_base64_list == [] and pre.past_image_base64_list == ["a", "b", "c"]
    removed = _diff_lines(pre.prelude_text, out.prelude_text)
    assert sum(l.startswith("  Image ") for l in removed) == 3
    assert all(l.startswith("  Image ") or l.startswith("PAST SIMILAR") for l in removed)
    assert out.prelude_text.count("  lesson     : ") == 3
    assert "Image 1" not in out.prelude_text and "scene looked like" not in out.prelude_text


def test_image_only(pre):
    out = ablate(pre, "image_only")
    assert out.past_image_base64_list == pre.past_image_base64_list
    assert "  lesson     : " not in out.prelude_text
    for r in pre.retrieved_records:
        assert r.text_lesson.strip()[:40] not in out.prelude_text
    assert out.prelude_text.count("  Image ") == 3
    assert "one-paragraph lesson" not in out.prelude_text and "past lessons" not in out.prelude_text
    removed = _diff_lines(pre.prelude_text, out.prelude_text)
    assert all(l.startswith("  lesson") or l.startswith("PAST SIMILAR") or l.startswith("The LAST image")
               for l in removed)


def test_empty_and_bad_mode(pre):
    e = R._empty_preamble()
    assert ablate(e, "text_only") is e
    with pytest.raises(ValueError):
        ablate(pre, "both")
    with pytest.raises(ValueError):
        AblatedMemoryRetriever(object(), "none")
