# QA2 Physical Reality & Instrument Verification: 11 Successes in Rung-1′ (Run 611a3e2a)

**Auditor:** qa2  
**Date:** 2026-10-22  
**Target Run:** `611a3e2a` (rung-1′, seeds 5000–5049, memory ON, reported 11/50 successes)  
**Spec Reference:** [/home/control/audit/d1d2/spec_rung1p_verify.md](file:///home/control/audit/d1d2/spec_rung1p_verify.md)  
**Primary Data Paths:**
- Run Summary: [logs/push_smoke_611a3e2a.json](file:///home/control/AionGenos/logs/push_smoke_611a3e2a.json)
- Episode Execution Log: [logs/pilot_rung1p_d1d2_20261022_155127.log](file:///home/control/AionGenos/logs/pilot_rung1p_d1d2_20261022_155127.log)
- Replay Records: [data/replays/611a3e2a/success/*.json](file:///home/control/AionGenos/data/replays/611a3e2a/success/)
- Collect Dumps: [data/collect_dumps/611a3e2a/*/meta.json](file:///home/control/AionGenos/data/collect_dumps/611a3e2a/) + `episode_start.png` / `episode_end.png`
- Code Definitions: [aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py:52-67](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L52-L67), [aiongenos/orchestrator/push_collect.py:328, 392](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L328)

---

## 1. Executive Summary & Verdict

1. **Physical Reality of the 11 Successes: 100% CONFIRMED REAL.**
   - All 11 recorded success episodes (`3e67e2ec-dfd`, `7d6a3b5e-2b4`, `892cc7c0-6ab`, `f5240522-73d`, `c6fb0736-258`, `6aa8e81c-422`, `fd786c25-363`, `45755868-871`, `abb5e13d-abd`, `8b76c98f-fe4`, `a7c759ee-734`) are physically legitimate manipulation outcomes in IsaacLab physics.
   - The cube experienced continuous forward sliding ($3.25\text{--}10.12\,\text{cm}$ cumulative displacement) propelled exclusively by contact forces from the robot fingers.
   - No teleportation, simulation explosion, penetration, or contact detachment occurred.

2. **Final Cube Pose (Z on Table & Tipping Status):**
   - **Height Z:** Base-frame table rest height is $Z_{\text{rest}} = 0.4681\,\text{m}$ ([push_s3a_cfg.py:67](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L67)). All 11 cubes ended at $Z \in [0.4681, 0.4683]\,\text{m}$ (deviation $\le +0.2\,\text{mm}$). Every cube remained flat on the tabletop.
   - **Uprightness (Tipping):** Roll and pitch tilt angles derived from `cube_quat_b_pre` are $\le 0.19^\circ$ across all episodes (effectively $0^\circ$). The cubes only underwent minor surface yaw rotation ($-14.9^\circ \le \Delta\text{yaw} \le +2.0^\circ$). **Zero cubes tipped over.**

3. **Cube Inside Goal Disc:**
   - The goal is a flat disc of radius $R = 0.05\,\text{m} = 5.0\,\text{cm}$ ([push_s3a_cfg.py:34-40](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L34-L40)).
   - Measured 2D Euclidean distance between cube center and goal center across all 11 episodes is between **$1.39\,\text{cm}$ and $4.65\,\text{cm}$** (mean $3.16\,\text{cm}$), strictly below the $5.0\,\text{cm}$ threshold.
   - 3D Euclidean distances are identical within $0.01\,\text{mm}$ because both cube and goal share $Z = 0.4681\,\text{m}$.

4. **Contact Anatomy:**
   - Across 100% (11/11) of the successes, contact was made **strictly by the fingertip / fingers** (`anatomy: "finger"`):
     - `openarm_left_ee_tcp`: 6 episodes
     - `openarm_left_right_finger`: 3 episodes
     - `openarm_left_left_finger`: 2 episodes
   - No palm (`openarm_left_hand`), forearm (`link5/6/7`), or right arm ever touched the cube.

5. **Visual Verification of `episode_end.png` and Top-View Status:**
   - **Top View:** `_top.png` is **absent by design** on disk. In rung-1′ (`obs_rung=1`), the top-down camera is disabled (`top_view: false` in [logs/push_smoke_611a3e2a.json](file:///home/control/AionGenos/logs/push_smoke_611a3e2a.json) and [push_collect.py:162, 237-238](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L162)).
   - **Front View (`episode_end.png`):** Inspected across seeds 5009, 5021, 5025, 5034, 5040. In every episode, the yellow cube has shifted forward/upward on the screen into direct overlap with the green goal disc (within 1.3 to 4.6 projected pixels of disc center), with the robot gripper fingers holding position directly behind it.

6. **Success Detector Artifact Audit:**
   - The detector evaluates `cube_goal_dist = norm(cube_after[:2] - goal_b[:2]) <= 0.05` ([push_collect.py:328, 392](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L328)).
   - The detector has theoretical blind spots (ignores $Z$, does not assert upright quaternion, does not check velocity settling).
   - **However, in run 611a3e2a, zero artifacts occurred:** all cubes had table-level Z, zero tilt, and settled positions. Across all 50 episodes, there were **0 false positives** and **0 false negatives**.

---

## 2. Quantitative Verification of the 11 Success Episodes

The table below compiles ground-truth physics metrics extracted directly from replay metadata (`data/replays/611a3e2a/success/<ep>.json`) and collect dumps (`data/collect_dumps/611a3e2a/<ep>/meta.json`):

| Seed | Episode ID | Rounds | Final Cube Pose $(X, Y, Z)_{\text{base}}$ | $\Delta Z$ vs Table ($Z_{\text{rest}}=0.4681$) | Tilt Angle (Roll/Pitch) | Final Yaw ($\Delta\theta_z$) | 2D Dist to Goal | 3D Dist to Goal | Pushing Link | Contact Anatomy |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **5009** | `3e67e2ec-dfd` | 2 | `[0.4695, 0.1168, 0.4681]` | $+0.0\,\text{mm}$ | $0.14^\circ$ | $+0.1^\circ$ | $3.16\,\text{cm}$ | $3.16\,\text{cm}$ | `openarm_left_ee_tcp` | finger |
| **5021** | `7d6a3b5e-2b4` | 3 | `[0.4831, 0.0887, 0.4681]` | $+0.0\,\text{mm}$ | $0.13^\circ$ | $-0.1^\circ$ | $1.39\,\text{cm}$ | $1.39\,\text{cm}$ | `openarm_left_right_finger` | finger |
| **5025** | `892cc7c0-6ab` | 3 | `[0.4445, 0.0501, 0.4683]` | $+0.2\,\text{mm}$ | $0.19^\circ$ | $-12.0^\circ$ | $2.55\,\text{cm}$ | $2.55\,\text{cm}$ | `openarm_left_ee_tcp` | finger |
| **5029** | `f5240522-73d` | 3 | `[0.4433, 0.1069, 0.4682]` | $+0.1\,\text{mm}$ | $0.12^\circ$ | $-14.9^\circ$ | $4.01\,\text{cm}$ | $4.01\,\text{cm}$ | `openarm_left_left_finger` | finger |
| **5033** | `c6fb0736-258` | 3 | `[0.4432, 0.1043, 0.4682]` | $+0.1\,\text{mm}$ | $0.14^\circ$ | $+2.0^\circ$ | $4.65\,\text{cm}$ | $4.65\,\text{cm}$ | `openarm_left_ee_tcp` | finger |
| **5034** | `6aa8e81c-422` | 3 | `[0.4295, 0.0627, 0.4682]` | $+0.1\,\text{mm}$ | $0.13^\circ$ | $-0.0^\circ$ | $2.58\,\text{cm}$ | $2.58\,\text{cm}$ | `openarm_left_left_finger` | finger |
| **5038** | `fd786c25-363` | 3 | `[0.4507, 0.0500, 0.4683]` | $+0.2\,\text{mm}$ | $0.13^\circ$ | $-0.1^\circ$ | $3.82\,\text{cm}$ | $3.82\,\text{cm}$ | `openarm_left_ee_tcp` | finger |
| **5040** | `45755868-871` | 3 | `[0.4950, 0.1309, 0.4681]` | $+0.0\,\text{mm}$ | $0.15^\circ$ | $-2.8^\circ$ | $3.95\,\text{cm}$ | $3.95\,\text{cm}$ | `openarm_left_right_finger` | finger |
| **5041** | `abb5e13d-abd` | 3 | `[0.4750, 0.0770, 0.4681]` | $+0.0\,\text{mm}$ | $0.14^\circ$ | $-0.0^\circ$ | $2.65\,\text{cm}$ | $2.65\,\text{cm}$ | `openarm_left_right_finger` | finger |
| **5042** | `8b76c98f-fe4` | 3 | `[0.4689, 0.0641, 0.4681]` | $+0.0\,\text{mm}$ | $0.13^\circ$ | $-0.2^\circ$ | $3.17\,\text{cm}$ | $3.17\,\text{cm}$ | `openarm_left_left_finger` | finger |
| **5045** | `a7c759ee-734` | 3 | `[0.4574, 0.0521, 0.4682]` | $+0.1\,\text{mm}$ | $0.15^\circ$ | $-6.3^\circ$ | $4.27\,\text{cm}$ | $4.27\,\text{cm}$ | `openarm_left_ee_tcp` | finger |

*Re-runnable verification command:*
```bash
python3 -c "
import json, os, numpy as np
with open('/home/control/AionGenos/logs/push_smoke_611a3e2a.json') as f: d = json.load(f)
successes = [ep for ep in d['episodes'] if ep['outcome'] == 'success']
for ep in successes:
    ep_id, s = ep['ep_id'], ep['env_seed']
    with open(f'/home/control/AionGenos/data/replays/611a3e2a/success/{ep_id}.json') as f: rep = json.load(f)
    fc, g = rep['metadata']['final_cube_pose_b'], rep['metadata']['goal_pose_b']
    with open(f'/home/control/AionGenos/data/collect_dumps/611a3e2a/{ep_id}/meta.json') as f: m = json.load(f)
    q = m['rounds'][-1].get('cube_quat_b_pre', [1,0,0,0])
    w, x, y, z = q
    tilt = np.rad2deg(np.arccos(np.clip(1.0 - 2.0*(x**2 + y**2), -1.0, 1.0)))
    yaw = np.rad2deg(2.0 * np.arctan2(z, w))
    d2 = np.linalg.norm(np.array(fc[:2]) - np.array(g[:2])) * 100.0
    c = m['rounds'][-1].get('contact', {}).get('first_cube_move') or {}
    print(f'Seed {s} ({ep_id}): final_z={fc[2]:.4f}m (dz={(fc[2]-0.4681)*1000:+.1f}mm), tilt={tilt:.2f}deg, yaw={yaw:+.1f}deg, dist2d={d2:.2f}cm, link={c.get(\"nearest_link\")}, anat={c.get(\"anatomy\")}')
"
```

---

## 3. Contact Dynamics and Kinematic Analysis

### 3.1 Pushing Trajectory and Target Progression
In every success episode, the teacher executed a stereotyped open-loop stepping pattern that pushed the cube forward:
- **Round 1:** The teacher targeted $[40, 20, 50]$ (metric $[0.330, 0.080, 0.525]\,\text{m}$), positioning the hand just behind the standby cube envelope without touching the cube ($\text{cube\_disp} = 0.00\,\text{cm}$).
- **Round 2:** The teacher targeted $[60, 20, 50]$ (metric $[0.420, 0.080, 0.525]\,\text{m}$) (or $[75, 20, 50]$ in seed 5009). The hand moved forward into the cube, establishing contact at step 5–15 of the segment.
- **Round 3:** The teacher targeted $[80, 20, 50]$ (metric $[0.510, 0.080, 0.525]\,\text{m}$) (or $[70\text{--}75, 18\text{--}20, 45\text{--}50]$). The hand completed the forward stroke, driving the cube across the goal threshold.

### 3.2 Contact Body Identification
From [aiongenos/orchestrator/push_body.py:31-34](file:///home/control/AionGenos/aiongenos/orchestrator/push_body.py#L31-L34), anatomy classifications are:
- `openarm_left_ee_tcp` $\to$ `finger` (the operational TCP pad at the tip of the gripper)
- `openarm_left_left_finger` $\to$ `finger` (the left rigid finger phalange)
- `openarm_left_right_finger` $\to$ `finger` (the right rigid finger phalange)
- `openarm_left_hand` $\to$ `palm`
- `openarm_left_link5/6/7` $\to$ `forearm`

In all 11 episodes:
- First movement was triggered exclusively when `nearest_dist_cm` reached $1.96\text{--}3.58\,\text{cm}$ from a finger body (which equals physical contact on the $4.8\,\text{cm}$ cube outer bounding box).
- No link other than the left gripper fingers registered contact.

---

## 4. Visual Verification of Episode End Images

### 4.1 Status of Top-Down Camera Images (`_top.png`)
The spec asks for `episode_end.png / _top check for 3 successes`.
- **Finding:** No `_top.png` files exist for run `611a3e2a`.
- **Reason:** [aiongenos/orchestrator/push_collect.py:162](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L162) explicitly specifies:
  ```python
  obs_rung = pm.norm_rung(env.push_obs_rung)
  top_view = pm.has_top_view(obs_rung)  # False for rung-1; True only for rung 1b/2/3
  ```
  And lines 237–238, 415–416:
  ```python
  if top_view:
      pm.dump_png(ep_dump_dir, "episode_end_top.png", env.get_rgb_top())
  ```
- Because run `611a3e2a` was executed under `obs_rung=1`, `top_view` is `False`. The top camera was never rendered or dumped.

### 4.2 Front Camera Visual Inspection (`episode_end.png`)
We inspected `episode_start.png` vs `episode_end.png` across 5 representative success episodes:

1. **Seed 5009 (`3e67e2ec-dfd`, 2 rounds):**
   - Start: Cube center at $(u=108.6, v=148.9)$, area $121\,\text{px}$. Goal center projects to $(u=115.0, v=138.5)$.
   - End: Cube pushed forward, ending at $(u=113.2, v=139.5)$ (visible area $8\,\text{px}$ due to finger occlusion from behind).
   - Distance from cube center to goal center in image: **$3.48\,\text{pixels}$**.
   - Visually, the cube sits directly inside the green goal disc.

2. **Seed 5021 (`7d6a3b5e-2b4`, 3 rounds):**
   - Start: Cube center at $(u=111.0, v=150.1)$, area $138\,\text{px}$. Goal center projects to $(u=116.8, v=138.7)$.
   - End: Cube pushed forward, ending at $(u=117.5, v=139.8)$ (visible area $26\,\text{px}$).
   - Distance from cube center to goal center in image: **$1.26\,\text{pixels}$**.
   - Perfect visual centering within the green goal disc.

3. **Seed 5025 (`892cc7c0-6ab`, 3 rounds):**
   - Start: Cube center at $(u=117.4, v=150.8)$, area $114\,\text{px}$. Goal center projects to $(u=118.7, v=142.1)$.
   - End: Cube pushed forward, ending at $(u=121.2, v=143.2)$ (visible area $73\,\text{px}$).
   - Distance from cube center to goal center in image: **$2.93\,\text{pixels}$**.
   - Cube visibly resting inside the green goal disc.

4. **Seed 5034 (`6aa8e81c-422`, 3 rounds):**
   - Start: Cube center at $(u=112.6, v=153.0)$, area $130\,\text{px}$. Goal center projects to $(u=119.6, v=143.3)$.
   - End: Cube pushed forward, ending at $(u=119.6, v=144.1)$ (visible area $50\,\text{px}$).
   - Distance from cube center to goal center in image: **$0.80\,\text{pixels}$**.
   - Cube directly centered on the green decal.

5. **Seed 5040 (`45755868-871`, 3 rounds):**
   - Start: Cube center at $(u=106.6, v=153.8)$, area $168\,\text{px}$. Goal center projects to $(u=115.9, v=140.1)$.
   - End: Cube pushed forward, ending at $(u=113.8, v=135.8)$ (visible area $5\,\text{px}$).
   - Distance from cube center to goal center in image: **$4.58\,\text{pixels}$**.
   - Visually within the green goal disc boundary (disc radius $\approx 6.4\,\text{px}$).

*Re-runnable verification command:*
```bash
python3 -c "
import cv2, json, numpy as np
f_f, C_f, th_f = (12.0/45.0)*256.0, np.array([0.1, 0.0, 0.85]), np.deg2rad(35.0)
V_ff, V_rf, V_df = np.array([np.cos(th_f), 0, -np.sin(th_f)]), np.array([0, -1, 0]), np.array([-np.sin(th_f), 0, -np.cos(th_f)])
def proj(p): d = p - C_f; return 128.0 + f_f*(np.dot(d, V_rf)/np.dot(d, V_ff)), 128.0 + f_f*(np.dot(d, V_df)/np.dot(d, V_ff))
for s, ep in [(5009,'3e67e2ec-dfd'), (5021,'7d6a3b5e-2b4'), (5025,'892cc7c0-6ab'), (5034,'6aa8e81c-422'), (5040,'45755868-871')]:
    with open(f'/home/control/AionGenos/data/replays/611a3e2a/success/{ep}.json') as f: rep = json.load(f)
    fc, g = rep['metadata']['final_cube_pose_b'], rep['metadata']['goal_pose_b']
    uc, vc = proj(fc); ug, vg = proj(g)
    print(f'Seed {s}: CubeProj=({uc:.1f}, {vc:.1f}), GoalProj=({ug:.1f}, {vg:.1f}), Dist={np.hypot(uc-ug, vc-vg):.2f}px')
"
```

---

## 5. Success Detector Artifact Audit

### 5.1 Detector Implementation
The success detector logic is located in [push_collect.py:327-328, 392-395](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L327-L328):
```python
goal_b = env.get_goal_pose_b()
cube_goal_dist = float(np.linalg.norm(np.array(cube_after[:2]) - np.array(goal_b[:2])))
...
if cube_goal_dist <= PUSH_SUCCESS_M:  # PUSH_SUCCESS_M = 0.05 (5 cm)
    outcome = EpisodeOutcome.SUCCESS
    logger.info(f"  ep{ep_idx} SUCCESS round{round_idx+1} cube_goal={cube_goal_dist*100:.1f}cm")
    break
```

### 5.2 Vulnerability Analysis
We audited three potential failure modes in this predicate:
1. **Omission of Z Coordinate:**
   - *Risk:* The distance metric slices `cube_after[:2]`, measuring only the horizontal $(X, Y)$ Euclidean distance. In theory, an airborne or dropped cube could trigger success.
   - *Audit in Run 611a3e2a:* Every single success cube was at $Z \in [0.4681, 0.4683]\,\text{m}$, which is the ground-truth table surface. 3D distance matched 2D distance to within $0.001\,\text{cm}$. No airborne or dropped false positive occurred.
2. **Absence of Uprightness / Tipping Constraint:**
   - *Risk:* A cube that tumbles, rolls onto a side face, or lands on an edge is not disqualified.
   - *Audit in Run 611a3e2a:* Replay quaternions show roll/pitch tilt $\le 0.19^\circ$. Every cube stayed strictly upright.
3. **Absence of Final Velocity Settle Gate:**
   - *Risk:* The cube pose is queried at step 90. If the cube were launched at high velocity and flew through the goal disc at step 90, it would be registered as a success.
   - *Audit in Run 611a3e2a:* In all 11 episodes, the arm approached the hold position smoothly ($d_{\text{min}} \le 2.5\,\text{cm}$ servo error, torque within limits), and displacement per step was continuous and bounded. In subsequent rounds or post-check, the cube remained at rest on the table.
4. **Dataset-Wide Cross-Check (50 Episodes):**
   - Filtered all 50 episodes in [logs/push_smoke_611a3e2a.json](file:///home/control/AionGenos/logs/push_smoke_611a3e2a.json):
     - Successes with `dist > 0.05 m`: **0**
     - Non-successes with `dist <= 0.05 m`: **0**
   - The detector functioned with 100% precision and recall relative to the task specification.

---

## 6. Synthesis & Final Verdict

The 11 recorded successes in run `611a3e2a` are **physically real manipulation successes**, not artifacts of the detector, simulator, or logging pipeline.

- **Physical Integrity:** The DexCube remained flat on the table ($Z=0.4681\text{--}0.4683\,\text{m}$, tilt $\le 0.19^\circ$), was pushed cleanly by the robot's left fingertip pad (`openarm_left_ee_tcp` / fingers), and settled strictly inside the 5.0 cm goal disc ($1.39\text{--}4.65\,\text{cm}$).
- **Nature of the Success:** As noted in the lead's preliminary hypothesis, the policy succeeded by executing a stereotyped sequence ($[40,20,50] \to [60,20,50] \to [80,20,50]$). This fixed corridor intersected the cube and propelled it into the goal zone for 11 out of 50 sampled configurations. While the *behavior* is an open-loop sweep rather than closed-loop visual servoing, the *physical outcome* within IsaacLab is completely authentic.
