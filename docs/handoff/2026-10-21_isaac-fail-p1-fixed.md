# Handoff → isaac: FAIL-P1 fixed (reply to fd91c1e)

**From:** paper session, 2026-10-21.

**New SHAs:**
- `paper-v1.1-wip` @ **`cbfca46`**
- `paper-v1.1-cameraready` @ **`d9f5347`**

**Upload archive:** sha256 **`e0394483…b3cb`**.

## The fix
Diff from `c69e85a`: 1 file, +3/−1 lines, `methods_l2.tex` §5.9.3(c). I used your second option, the sentence. The parenthetical is not restored, because the PI's reviewer flagged bare one-word tags as note-style. After "…is decisive within L2." the paragraph now reads: "This was not the expected outcome: the expectation recorded with the pre-registered prediction was a diffuse, distance-independent rescue set."

## Builds
| build | result |
|---|---|
| `make bar` | gate OK, page guard 5/5 |
| `make arxiv` | gate OK |
| `make tmlr` | gate OK, anon PASS |
