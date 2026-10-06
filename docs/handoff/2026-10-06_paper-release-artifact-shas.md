# Handoff → paper session: release-artifact hashes (reply to 0a6fe8f)

**From:** isaac · **Date:** 2026-10-06

## 1. A_ctrl_rat adapters (GPU host 10.80.9.148, read-only, no restart)
Paths are relative to `/home/exx/CYTu/AionGenos_server`.

| File | sha256 | Size | mtime |
|---|---|---|---|
| `data/lora_gguf/d11_A_ctrl_rat_sft/adapter.gguf` | `4807767d2140ba3166a790fc5d621d19096d85e59c9332f0ebb34ed369e55ebc` | 489,774,208 B | 2026-07-11 01:59:20 |
| `data/lora_gguf/d11_A_ctrl_rat_kto/adapter.gguf` | `7f7f73636e1a3453bfd6f236b0446e765e4cb3cd16d29ea8deb167421415a036` | 489,774,208 B | 2026-07-11 01:59:21 |

**These are the same files that served D11.**
- Export: they were written by D11 driver Step 7 (`export_lora_gguf.py` from
  `checkpoints/d11/A_ctrl_rat/{sft_A,kto_B}/final_adapter`, master log
  `logs/d11_pipeline_master_v2_20260711_020130.log` l.129).
- Load: Step 8 loaded exactly these paths (l.186–206, `/lora-adapters` echo)
  for A_ctrl_rat (2026-07-11 13:44) and C_retrieval (2026-07-12 22:24).
- Not modified since: the mtime predates both evals, and no later export or
  write exists.
- Same files in A15: the A15 cost re-measure loaded the same paths
  (2026-10-05).

## 2. C_retrieval top_k / image cap
- `top_k = 3`, as logged at eval time in `logs/d11_C_retrieval_20260712_222441.log`:
  "MemoryRetriever ready: 547 recaps in buffer, top_k=3, image_weight=0.4,
  state_scale_cm=30.0, success_floor=0.67".
- `run_collect.py` at `e0ad00f`: `--memory_top_k` default 3; the D11 command
  line has no override.
- Image cap: one `init_pre` image per retrieved record, so ≤ 3 past images,
  plus the current scene.

## 3. Release pack (buffer + 547 init_pre images)
- Built by `scripts/release/build_buffer_release.py`; the source buffer is
  untouched and tree-hash asserted.
- Layout: `buffer/<run>/<ep>.json` + `images/<run>/<ep>/init_pre.png`, all
  paths relative.
- Record changes: records are byte-identical except `image_anchors`.
  `init_pre` is rewritten to its relative path; `final_post` and
  `key_round_pre` are set to null. Those two were used only when the recap
  was written, never at retrieval.
- Image check: all 547 images match their originals by hash (0 mismatches).
- Load test: run from the pack root, `RecapBuffer("buffer")` +
  `MemoryRetriever(top_k=3)` returned 3 hits with 3 images.
- Archive: `workspace/release/aiongenos_d10ext_frozen_buffer_v1.tar.gz`, 26 MB.
  It is deterministic: rebuilt twice with the same hash.
  - tar sha256: **`7a405eb1cbe83a2199152918cc78b375cda2fb465dca8dc0a26324235fdfaaa0`**
  - pack tree hash: `e29224a196fa778f89d638e8ba693cabe600aeb7d1cbb1a60ec09f10a558a673`
- Integrity files: `MANIFEST.sha256` inside the pack, plus a README that
  covers the image dependency, relative paths and the `{target_color}`
  literal.
- **Release action:** none from isaac. The PI uploads from the PI account on
  arXiv upload day.
