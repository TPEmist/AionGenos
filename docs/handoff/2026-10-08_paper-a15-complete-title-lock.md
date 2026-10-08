# Handoff → paper session: A15 complete (4/4 arms); input for the title amendment lock

**From** isaac, 2026-10-08. For: paper-v1.1-wip (TITLE AMENDMENT 2, lock pending A15 stats).

- Full table and lock comparison: `docs/paper/a15_ab_results.md` (replaces
  the 2-arm version from 10-06).
- Data:
  - `docs/paper/data/a15_ab_stats.json` (all four arms, each vs C_retrieval,
    each (b) arm vs its own D11 run, and the pin-8 sensitivity);
  - `docs/paper/data/a15_slope_probe_gate15mm.json`.

## Verdicts (lock 989a753)
- **(a) MISS → recipe-rewrite route.** base+buffer 48 vs C_retrieval 49
  (Δ −1, p = 0.887).
- **(b) HIT, 3/3 → "+34 pp generalised beyond A_ctrl_rat".** z is primary,
  α .05.

| Arm | Own D11 (no retrieval) | With buffer | Δ | p |
|---|---|---|---|---|
| action_only | 25 | 53 | +28 | 4.9e-5 |
| B_main | 26 | 53 | +27 | 9.4e-5 |
| D_gist | 19 | 55 | +36 | 1.4e-7 |

- No arm differs from C_retrieval (|Δ| ≤ 6, p ≥ 0.39).
- Pin-8 sensitivity changes no verdict.
- **Slopes (A15.1 reading):** every with-buffer arm is above its band
  (r +0.29 to +0.49). Every no-buffer adapter is at or below its band
  (r −0.16 to −0.30).

## For the title lock
Together, the routes say:
- With the frozen buffer, SR is 48–55 whatever weights are loaded (base or
  any of the 4 adapters).
- Without it, SR is 15–26.

"Externalise the Memory" is supported, and "distil the competence" is
downgraded per the (a) route.

The results do not separate lesson text from the anchor images; they are
confounded. That will be A17 (text vs image), run at night.
- If A17 lands before 10/16, it is eligible for one line on camera-ready
  page 5.
- Otherwise it goes to the TMLR version.

## D_gist provenance (for the methods / REPRODUCE)
- Run `fdb2a9b0`, started 10-07 13:37 after the host reboot (manual start
  `--ignore-window`; flags, seeds and buffer unchanged).
- Adapter sha256:
  - SFT `dba178f3f974b8c90d63667bdc2c9d74a5e9eff512335ca3f14e977ba059ff85`
  - KTO `d5ebc32f1645a01e7ffc01e9cc1454161d5b947928955cc7f85b75b21801dfd6`
- Buffer tree hash after the run: `7d4f3f9e…` (readonly OK).
