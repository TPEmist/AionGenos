# Verify the (e) two-arm result on Pin-4c (exploratory; before reporting to PI)
Runs (seeds 5000–5049, obs_rung 1, d1+d2, history+feedback, memory ON, fresh buffers, geometry pin4c ±75°):
- coords ON  (preamble has past round-1 targets): run 663c049a → 3/50
- coords OFF (lesson text only, coordinate patterns redacted at render; images kept): run 3786f4e5 → 13/50
- blind-sweep control on same geometry: aa2c36c3 → 5/50
Data: data/collect_dumps/<run>/*/meta.json, logs/push_smoke_<run>.json, logs/pilot_rung1p_p4c_*_2026102*.log, logs/validate_<run>.txt, logs/rho_<run>.txt
Lead's preliminary: OFF arm has 42 unique round-1 targets vs 10 (ON); ON arm z=53 in 161/183 rounds, OFF arm contact band 55/150; ρ_Y(OFF)=+0.278 p=0.026, ρ_X both n.s.
RULES: read-only on repo; scratch /home/control/audit/p4c/scratch_<name>/; no GPU/Isaac; cite paths + re-runnable commands.
- qa2: the 13 OFF and 3 ON successes physically real (cube flat, inside goal, which body part)? any success caused by physics glitch?
- prose_disc: arm comparison: Fisher exact two-sided p for 13/50 vs 3/50 and each vs blind 5/50; per-episode-order success curves; does the ON arm copy past round-1 targets from the preamble (match R1 target to retrieved recaps' r1 targets: logs/push_smoke_<run>.json memory_hits + recap buffer workspace/recaps_push_rung1p_p4c_coords)? does the OFF arm still converge on a path? cube-x/y variance in this geometry (is ρ_X a usable indicator when cube x spans only 6 cm?).
- beh2: thoughts: ON arm — cites past coordinates / copies? OFF arm — reasons about the cube in the image, uses lessons, descends? did any coordinates leak in OFF prompts despite redaction (check rendered preambles if logged; else lessons in recap buffer workspace/recaps_push_rung1p_p4c_lesson vs redaction patterns)?
Output /home/control/audit/p4c/arms_<name>.md. Reply: path + one-line verdict.
