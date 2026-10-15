# Handoff → isaac: adapter copy for the GitHub Release (PI ruling 2026-10-15)

**From:** paper session, 2026-10-15.

## PI ruling
The artifacts are released as a **GitHub Release** of `TPEmist/AionGenos`:
- tag `paper-v1-artifacts`;
- created as a draft;
- published by the PI on arXiv upload day, after PREPUB is all green and
  `release-step5` has been pushed.

HF is deferred to later. The PI states that the HF channel is also covered
by the company permission. For F3, please record that as **PI-stated,
2026-10-15**; it is not used in v1.

## Request (servers are your territory)
Copy the two A_ctrl_rat adapters from the GPU host to the local machine.
Do it read-only, with no server restart.

| source (`/home/exx/CYTu/AionGenos_server/`) | local target | sha256 (must match) |
|---|---|---|
| `data/lora_gguf/d11_A_ctrl_rat_sft/adapter.gguf` | `~/AionGenos/workspace/release/d11_A_ctrl_rat_sft.gguf` | `4807767d2140ba3166a790fc5d621d19096d85e59c9332f0ebb34ed369e55ebc` |
| `data/lora_gguf/d11_A_ctrl_rat_kto/adapter.gguf` | `~/AionGenos/workspace/release/d11_A_ctrl_rat_kto.gguf` | `7f7f73636e1a3453bfd6f236b0446e765e4cb3cd16d29ea8deb167421415a036` |

- Verify both hashes on the **local** copies.
- The third release file is already local:
  `workspace/release/aiongenos_d10ext_frozen_buffer_v1.tar.gz` (`7a405eb1…`).
- `release-step5` @ `4132e1f` now carries these
  exact filenames and the download URLs in REPRODUCE.md.
- Lower priority than the audit; any time before 10/17 works.
