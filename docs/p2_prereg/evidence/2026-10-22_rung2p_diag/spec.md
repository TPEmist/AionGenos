# Spec — rung-2′ diagnosis: is the 0/50 real, or an instrument artifact? + macro view + Argon lessons

Lead: isaac. 2026-10-22. Repo: /home/control/AionGenos (master). Run under study: 71134939 (rung-2′, seeds 5000–5049, memory ON).
Data: data/collect_dumps/71134939/<ep>/meta.json (per-round: prompt feedback text, targets, TCP, cube, thought, contact) + round_XX_pre.png / _top.png;
      data/replays/71134939/failure/*.json. Code: aiongenos/orchestrator/{push_collect,push_feedback,push_memory,isaaclab_env_interface,push_body}.py,
      aiongenos/vlm/{prompts,parser,client}.py, aiongenos/pipeline/stage1_reasoning.py. P1 reference path: aiongenos/orchestrator/collect.py (+ stage3_critic).
Mission (must not be violated by any recommendation): docs/aiongenos_founding_intent.md — zero DEMONSTRATIONS, conditional knowledge earned,
marginal grants only via ledger (docs/harness_grant_ledger.md).
Already verified by lead (do not redo, but you may challenge): /home/control/audit/rung2p_diag/validate.py → feedback numbers 547/547 match runtime,
controller tracking median 0.05 cm, images fresh, parser strict (no Z default), scripted push succeeds in 2 rounds (logs/wp3a_reach_real.log).

RULES (everyone): do NOT trust comments/docstrings/handoffs — follow the code path. Every claim cites file:line or a data path + a re-runnable command.
May: read anything; write ONLY your output file (and scratch under /home/control/audit/rung2p_diag/scratch_<name>/). May NOT: edit repo files, git
commit/checkout/stash, run Isaac/GPU jobs, contact the GPU host, kill anything. Output: /home/control/audit/rung2p_diag/<name>.md.
Reply: only the output path + one line verdict.

## Tasks
- mem1 (Memory-condition auditor, Rule 10): field-by-field, what does the teacher actually receive at round r in rung-2′ vs P1 L0a?
  (a) cross-episode memory: what is retrieved, how many, text and/or images (which images? start image only?), which rounds;
  (b) within-episode history: EpisodeConversation contents — which turns kept, are older IMAGES stripped (client.py), is the top view kept;
  (c) critic feedback; (d) system prompt. Table: item | P1 code path | rung-2′ code path | same/different | evidence.
- qa1 (Instrument QA): copy tests to scratch and run `python3 -m pytest -q tests/test_push_memory.py` (CPU only; if it needs Isaac, say so, don't force);
  independently reconstruct ONE episode's full round-5 prompt (text + which images) from code + meta.json, and confirm the feedback & history
  that code would send. Negative test: show one mutation that your reconstruction would detect.
- qa2 (Perception QA): open round_01_pre.png and _top.png for 10 episodes (seeds 5000–5009). Report cube size in pixels, whether a human can judge
  the fingertip-vs-cube HEIGHT difference (≈4.3 cm) from these 256×256 images, and whether front/top axes match the base frame (+X,+Y,+Z) —
  derive axis directions from TCP motion between consecutive rounds (meta.json) vs where the gripper moves in the image.
- prose_res (Behaviour analyst): classify all 597 `vlm_thought` texts: (i) reasons about Z at all, (ii) believes Z=53 is cube/contact height,
  (iii) axis or scale misunderstanding (says ±X/±Y means a direction that contradicts actual motion), (iv) uses fingertip→cube distance correctly,
  (v) mentions memory/past episodes. Counts + 2 verbatim quotes each + script.
- prose_disc (Comparator): same seeds rung-2 run vs rung-2′ (find rung-2 run id in docs/p2_prereg/wp3a_push_provenance.md): per-seed Z distribution
  and whether rung-2′'s z-anchoring appears from round 2 onward (history effect) — test the claim "history/feedback caused height anchoring".
- critic1 (Critic, fresh): review /home/control/audit/rung2p_diag/validate.py and its output (run it). Find what it does NOT check that could still make
  0/50 an artifact (e.g. cube yaw ignored in box distance, success uses xy only, round cap, auto-reset, scene guard clamps, ORI offsets).
- researcher (Source verifier): verify these claims about Google DeepMind "Gemini 4 Argon" robotics against primary sources
  https://developers.googleblog.com/gemini-4-argon-for-robotics , https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/ ,
  https://deepmind.google/models/gemini-robotics/vla/ : (1) Argon acts as reasoner/coder over action primitives, not a VLA; (2) harness supplies
  calibrated camera + projected world coordinates + axis convention in prompt; (3) contact skills practised in MuJoCo twins with "no sim cheating" rules;
  (4) 56%→75% from VLA fine-tune on 4,500+ sim episodes; (5) cornhole video-to-sim-to-real 7 shots. Mark each CONFIRMED / NOT FOUND / DIFFERENT, quote.
- lit1 (Literature): privileged/multi-view TEACHER distilled into a single-view (monocular) STUDENT for manipulation: is it known to work, and what
  fails? (learning by cheating, asymmetric actor-critic, privileged-teacher distillation, multi-view→single-view / cross-view distillation, monocular
  depth for contact). 6–10 papers with URL, what was distilled, what student lost. Note which require demonstrations (conflict with zero-demo).
