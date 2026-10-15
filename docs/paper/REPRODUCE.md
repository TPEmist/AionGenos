# Reproducing the identical-weights contrast (C_retrieval vs A_ctrl_rat)

This guide re-runs the two 100-episode evaluations behind the paper's
identical-weights contrast (+34 pp; Table 1 / §4.2): the `A_ctrl_rat`
adapter evaluated bare, and the same adapter with the frozen retrieval
buffer attached (`C_retrieval`). Every value below is copied from a file
in this repository; the source is named next to it.

## Status of the inputs

**Status:** checkable and runnable once the GitHub Release `paper-v1-artifacts`
is published (arXiv upload day); until then, checkable only.


| input | identifier | release |
|---|---|---|
| code (instrument at evaluation time) | commit `e0ad00f` (last code commit before the D11 evaluations of 2026-07-11/12; no `aiongenos/` or `scripts/run_collect.py` change until both finished) | public (`TPEmist/AionGenos`) |
| simulator task | Isaac Lab upstream `isaac-sim/IsaacLab` @ `84dc3f66ce` (v2.2.1-290), task cfg `manipulation/reach/config/openarm/bimanual/reach_openarm_bi_env_cfg.py`, unmodified | public |
| base model | `ggml-org/gemma-4-31B-it-GGUF`, files `gemma-4-31B-it-Q4_K_M.gguf` + `mmproj-gemma-4-31B-it-Q8_0.gguf` (`server_side/reload_student_dual.sh`) | public (Apache-2.0) |
| inference server | llama.cpp `llama-server` (`server_side/reload_student_dual.sh`, ctx 16384) | public (MIT) |
| `A_ctrl_rat` adapters | `d11_A_ctrl_rat_sft/adapter.gguf` + `d11_A_ctrl_rat_kto/adapter.gguf`; sha256 SFT `4807767d2140ba3166a790fc5d621d19096d85e59c9332f0ebb34ed369e55ebc`, KTO `7f7f73636e1a3453bfd6f236b0446e765e4cb3cd16d29ea8deb167421415a036` (isaac handoff `7229335`, hashed read-only on the GPU host); released as `d11_A_ctrl_rat_sft.gguf` and `d11_A_ctrl_rat_kto.gguf` | GitHub Release `paper-v1-artifacts` of this repository, published on the arXiv upload day: `https://github.com/TPEmist/AionGenos/releases/download/paper-v1-artifacts/d11_A_ctrl_rat_sft.gguf`, `https://github.com/TPEmist/AionGenos/releases/download/paper-v1-artifacts/d11_A_ctrl_rat_kto.gguf`. Trained from public Gemma weights on simulator-generated data; no company data |
| frozen retrieval buffer — **evaluated identity** | `d10ext_final_buffer.tar.gz`, sha256 `a762386b79e18ce50440d1ff3e7045f6f82f32bd7b05092ac332b9217fb0eb9c` (`scripts/training/run_d11_pipeline_v2.sh:56`; re-hashed 2026-10-06); 547 recap JSONs (lesson text, outcome, state anchor, 768-d DINOv2 image embedding, absolute image-anchor paths) | the hash identifies the buffer that was evaluated; this exact tarball is not the release file |
| frozen retrieval buffer — **release identity** | `aiongenos_d10ext_frozen_buffer_v1.tar.gz`, sha256 `7a405eb1cbe83a2199152918cc78b375cda2fb465dca8dc0a26324235fdfaaa0` (pack tree hash `e29224a196fa778f89d638e8ba693cabe600aeb7d1cbb1a60ec09f10a558a673`); built by `scripts/release/build_buffer_release.py` (deterministic: two builds give the same hash; handoff `docs/handoff/2026-10-06_paper-release-artifact-shas.md`); `buffer/` (547 recap JSONs) + `images/` (the 547 `init_pre` anchor images) + `MANIFEST.sha256` + `README.md` | same GitHub Release: `https://github.com/TPEmist/AionGenos/releases/download/paper-v1-artifacts/aiongenos_d10ext_frozen_buffer_v1.tar.gz` |
| raw replays / other images | `data/replays/`, other `data/collect_dumps/` images | not released: generated on company hardware; the permission covers publication, not data release |

**Evaluated vs release identity.** The records are byte-identical except
for `image_anchors`. `init_pre` is rewritten from
`/home/control/AionGenos/data/collect_dumps/<run>/<ep>/round_01_pre.png` to
the relative path `images/<run>/<ep>/init_pre.png`, and that file is a byte
copy of the original (547/547 hashes match). `final_post` and
`key_round_pre` are set to null and their images are not included: they were
used only when each recap was written, never at retrieval. The retriever
loads `init_pre` only (`aiongenos/memory/retriever.py`,
`_load_past_image_b64_list`). The unformatted `{target_color}` instruction is
kept as evaluated; it is a disclosed instrument defect (paper §4.5, "Two
instrument defects"; `docs/paper/a15_p1_disclosure_pack.md` §2) and does
not enter the retrieval prompt.

### Pre-release scan of the buffer (2026-10-06, all 547 records)

| check | result |
|---|---|
| company names, person names, e-mail, URLs, IPs/hosts, secrets | 0 hits in any field |
| prompt/pipeline tokens in lesson text | 0 hits |
| local absolute paths | 547/547 in `image_anchors` of the evaluated buffer; none in the release pack (`/home/`, host IPs, URLs, e-mail: 0 files, re-scanned 2026-10-15); none in lessons |
| unformatted `{target_color}` template | 547/547 in `metadata.instruction` (disclosed instrument defect); 0 in lessons |
| anchor images (547 PNG, 256×256 simulator renders) | 64 of 547 viewed (random sample, seed 0) plus 1 at full size: simulator scene only (arms, cube, floor grid); no overlaid text |

### Why the images are part of the buffer

The `C_retrieval` prompt contains, for each retrieved episode, its lesson
text **and its initial image**; all 547 images were present during the
D11 run (0 "missing image" warnings in
`logs/d11_C_retrieval_20260712_222441.log`). Without them the retriever
sends text only, which is a different protocol. With the release buffer,
the code, the base model and the adapters, both protocols are runnable.

## Commands

From a clone at `e0ad00f`, with Isaac Lab installed at the commit above
and a GPU host serving the student:

```bash
# 0. Release files (GitHub Release `paper-v1-artifacts`) + integrity check
for f in d11_A_ctrl_rat_sft.gguf d11_A_ctrl_rat_kto.gguf aiongenos_d10ext_frozen_buffer_v1.tar.gz; do
  curl -LO https://github.com/TPEmist/AionGenos/releases/download/paper-v1-artifacts/$f
done
sha256sum d11_A_ctrl_rat_sft.gguf d11_A_ctrl_rat_kto.gguf   # must equal 4807767d...5ebc / 7f7f7363...a036

# 1. Student server: base + the A_ctrl_rat SFT and KTO adapters (summed).
MODEL_PATH=<gemma-4-31B-it-Q4_K_M.gguf> MMPROJ_PATH=<mmproj-gemma-4-31B-it-Q8_0.gguf> \
  bash server_side/reload_student_dual.sh \
    d11_A_ctrl_rat_sft.gguf d11_A_ctrl_rat_kto.gguf

# 2. A_ctrl_rat (bare)
<isaaclab>/isaaclab.sh -p scripts/run_collect.py \
  --level -2 --num_episodes 100 --teacher_url http://<student-host>:18889 \
  --freeze_level --env_seed_base 4500 --eval_template_variant rationale \
  --headless --enable_cameras

# 3. C_retrieval (same adapters; release pack extracted at the clone root)
sha256sum aiongenos_d10ext_frozen_buffer_v1.tar.gz   # must equal 7a405eb1...faaa0
tar xzf aiongenos_d10ext_frozen_buffer_v1.tar.gz     # -> aiongenos_d10ext_frozen_buffer_v1/{buffer,images,MANIFEST.sha256,README.md}
(cd aiongenos_d10ext_frozen_buffer_v1 && sha256sum -c MANIFEST.sha256)
ln -s "$PWD/aiongenos_d10ext_frozen_buffer_v1/images" images   # at the clone root: anchors are images/<run>/<ep>/init_pre.png
<isaaclab>/isaaclab.sh -p scripts/run_collect.py \
  --level -2 --num_episodes 100 --teacher_url http://<student-host>:18889 \
  --freeze_level --env_seed_base 4500 --eval_template_variant rationale_with_retrieval \
  --recap_buffer_root aiongenos_d10ext_frozen_buffer_v1/buffer --use_memory --recap_buffer_readonly \
  --headless --enable_cameras
```

Flags are those of `scripts/training/run_d11_pipeline_v2.sh` step 8
(`D11_LEVEL=-2`, `D11_NUM_EPISODES=100`, `D11_ENV_SEED_BASE=4500`,
`PROTOCOL_TO_VARIANT`). Episode *k* uses seed 4500 + *k* in both runs,
so the two runs are paired by episode index.

## Expected result

The success count is printed in each log's `Collect loop done` line.
Generation is sampled, so a re-run is not bit-identical; compare against
the 95% Wilson interval of the published count
(`docs/paper/birth_certificates/derived_stats.txt`, `[repro ...]` lines):

| protocol | published | 95% Wilson interval |
|---|---|---|
| `C_retrieval` | 49/100 | [39.4, 58.7] |
| `A_ctrl_rat` | 15/100 | [9.3, 23.3] |

The paper's primary success rate is the as-run count. The pre-registered
auto-reset sensitivity count (Amendment 15 pin 8; 48 and 12) is
recomputed from the replays by `scripts/analysis/a15_p1_autoreset_sensitivity.py`.
The contrast statistics (two-proportion z, Newcombe interval) are computed
by `scripts/analysis/d11_mcnemar.py` and
`docs/paper/birth_certificates/derived_stats.py`.

## Future

Release of the raw replays and the remaining images (generated on company
hardware) is listed as future work.
