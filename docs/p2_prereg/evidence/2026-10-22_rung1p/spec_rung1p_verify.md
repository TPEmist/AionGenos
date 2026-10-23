# Verify rung-1′ result (run 611a3e2a, 11/50 successes) — before reporting to PI
Data: data/collect_dumps/611a3e2a/*/meta.json, logs/push_smoke_611a3e2a.json, logs/pilot_rung1p_d1d2_20261022_155127.log, workspace/recaps_push_pilot_rung1p_d1d2/.
Interface: obs_rung=1 (front RGB + proprio, no distances), history+feedback (proprio-only), d1 FRAME line, memory ON (fresh buffer).
Cube region x∈[0.38,0.42], y∈[0.05,0.15]; goal = cube + (0.07–0.10, −0.04–0.04) (aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py:131-138). Success = cube→goal xy ≤ 5 cm.
Lead's preliminary: successes look like ONE fixed open-loop sweep (≈[40,20,50]→[60,20,50]→[80,20,50]) that ignores the cube position (ρ(R1 target, cube) ≈ 0), succeeding when the cube happens to lie in the hand's path. Challenge this.
RULES: read-only on repo; scratch only in /home/control/audit/d1d2/scratch_<name>/; no GPU/Isaac; cite data paths + re-runnable commands.
Tasks:
- qa2: are the 11 successes physically real? final cube pose (z on table, not tipped — use cube_quat_b_pre / final_cube_pose), cube inside goal disc, which body part pushed (contact anatomy), episode_end.png / _top check for 3 successes. Any success-detector artifact?
- prose_disc: is the policy situation-independent? Per round: target vs cube (x,y) correlation; how many episodes follow the stereotyped sequence; when does it first appear and does it spread via memory (which recaps were retrieved before each episode — logs/push_smoke_611a3e2a.json memory_hits; does the preamble text contain the sequence)? Would a FIXED scripted sweep [40,20,50]→[60,20,50]→[80,20,50] be expected to succeed on the same 50 cube/goal poses? (geometric estimate from poses: hand y-width — derive from contact data — vs |cube_y − 0.08|, and forward push distance vs goal offset.)
- beh2: thoughts (vlm_thought): do they use the FRAME line (cite +X forward etc.)? do they reason about the cube position from the image, or copy past episodes ("past successful episode", specific coordinates)? counts + quotes.
Output: /home/control/audit/d1d2/rung1p_<name>.md. Reply: path + one-line verdict.
