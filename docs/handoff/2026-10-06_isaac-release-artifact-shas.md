# Handoff → isaac: release-artifact hashes for REPRODUCE.md (PI ruling 2026-10-06)

**From:** paper session · **Date:** 2026-10-06

PI ruled that two G3 artifacts are released on the arXiv upload day
(release action = PI account). The paper's `docs/paper/REPRODUCE.md`
(paper-v1.1-wip) needs their hashes. The adapters live on the GPU host
(your territory), so please compute — read-only, no server restart:

1. `sha256sum data/lora_gguf/d11_A_ctrl_rat_sft/adapter.gguf data/lora_gguf/d11_A_ctrl_rat_kto/adapter.gguf`
   on the host that served the D11 evaluation (the paths in
   `logs/cost_remeasure_20261005_181930.md` "student /lora-adapters at start").
   Confirm these are the same files loaded for the 2026-07-11/12 D11
   `A_ctrl_rat` / `C_retrieval` evaluations (training_meta / mtime / train SHA).
2. Confirm `top_k` (and any image cap) used by `C_retrieval` at evaluation
   time (`aiongenos/memory/retriever.py` default 3; any override in the
   `run_collect.py` path at `e0ad00f`).

Already done on the paper side: frozen buffer tar re-hashed
(`a762386b…0eb9c`, matches pin); 547-record pre-release scan (lessons clean;
`image_anchors` hold absolute local paths; `{target_color}` in instruction).

**Finding for PI (recorded in REPRODUCE.md):** `C_retrieval` attaches each
retrieved episode's `init_pre` image to the prompt
(`retriever.py:210–224`); all 547 were present during the D11 run (0
"missing image" warnings). Without those images the protocol is
text-only and differs from the evaluated one.

Send the two SHAs back; paper fills `[SFT sha256]` / `[KTO sha256]`.
