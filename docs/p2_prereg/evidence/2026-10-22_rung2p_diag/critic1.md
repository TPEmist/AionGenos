# Critic Diagnosis: Run 71134939 (Rung-2′) Instrument Audit

**Author**: `critic1` (Critic, fresh)  
**Date**: 2026-10-22  
**Target Run**: `71134939` (rung-2′, seeds 5000–5049, memory ON, 50 episodes, 597 rounds)  
**Primary Question**: Is the 0/50 success rate real, or an instrument/measurement artifact? What does `/home/control/audit/rung2p_diag/validate.py` fail to check?

---

## 1. Executive Verdict

1. **The 0/50 outcome is physically real, NOT an execution or measurement artifact.**
   - The robot arm genuinely failed to move the cube into the goal zone (success requires cube-to-goal distance $\le 5.0\text{ cm}$; the minimum distance achieved across all 50 episodes was $7.27\text{ cm}$, identical to the initial minimum of $7.27\text{ cm}$).
   - In 48 of 50 episodes (96%), the cube never moved more than $0.1\text{ mm}$.
   - The primary driver was a **height-anchoring trap**: initial TCP height was $Z=53$ ($0.5356\text{ m}$), while the top surface of the cube was at $Z=0.4923\text{ m}$ ($4.33\text{ cm}$ lower). In 509 of 597 rounds (85.3%), the VLM commanded $Z=53$, sweeping in mid-air $4.3\text{ cm}$ above the cube without making contact.

2. **However, `validate.py` has serious blind spots, unchecked failure modes, and flawed assumptions.**
   While its reported numbers are technically correct for run `71134939`, `validate.py` failed to test critical dimensions of the execution pipeline:
   - **Cube yaw ignored in box distance**: `validate.py` assumes an axis-aligned bounding box and ignores cube yaw. It passed (547/547) only because the cube was barely touched ($<1\text{ mm}$ displacement in 593 rounds). On any run where pushing rotates the cube, `validate.py` would throw false mismatches up to $1.0\text{ cm}$. Furthermore, `meta.json` does not even record cube quaternion, making exact offline box distance validation impossible.
   - **Success predicate uses XY only**: `validate.py` does not check whether 2D projection masked a 3D success (ruled out: 2D is more permissive, and minimum achieved was $7.27\text{ cm}$).
   - **Premature plateau termination under Pin-12**: `validate.py` treats `push_plateau` as a normal outcome without noting that Pin-12 terminated the *only two episodes* that made contact (`79681177-225` at round 11 and `cdf29531-513` at round 10).
   - **Mid-episode auto-resets unmonitored**: `validate.py` does not check `e["flags"]` for `"env_auto_reset"`, which leaves `outcome="timeout"` while prematurely ending episodes.
   - **Scene guard clamps and reach error misinterpretation**: `validate.py` reports `tcp_reach_err_cm max=9.23 cm` without diagnosing that this occurred because reach error was computed against the raw VLM target ($Z=0.385\text{ m}$) rather than the scene-guarded target ($Z=0.4541\text{ m}$). `validate.py` also ignored intermediate `setpoint_clamp_steps` (82 steps in that round).
   - **Orientation (ORI) tracking completely unmonitored**: `validate.py` contains zero lines checking orientation. In 86 rounds (14.4%), orientation tracking error exceeded $5.0^\circ$, reaching up to $38.75^\circ$ due to softened wrist stiffness.
   - **Torque saturation unmonitored**: `validate.py` ignored torque limits; 60 rounds (10.1%) experienced actuator torque saturation (`tau_flag_steps > 0`), with several rounds saturated for 88–90 steps.
   - **Feedback semantic ambiguity**: `validate.py` confirmed syntactic matching of feedback text, but did not analyze that reporting a 1D scalar distance (`tip_to_cube`) without axis-decomposed errors $(\Delta X, \Delta Y, \Delta Z)$ geometrically trapped the teacher into planar wandering.

---

## 2. Review of `validate.py` Baseline Execution

Running `validate.py` directly on run `71134939`:
```bash
python3 /home/control/audit/rung2p_diag/validate.py 71134939
```

Output:
```text
episodes=50 rounds=597 outcomes={'timeout': 48, 'push_plateau': 2}
[exec] tcp_reach_err_cm median=0.05 p95=0.33 max=9.23; target_clamps=1
[exec] rounds with target z<0.52m: 45; achieved z for those (target,achieved) sample: [(0.518, 0.518), (0.518, 0.5179), (0.518, 0.518), (0.518, 0.5179), (0.518, 0.5179), (0.5075, 0.5075), (0.5075, 0.5074), (0.5075, 0.507)]
[z] target z-int histogram top: [(53, 509), (50, 41), (45, 21), (48, 10), (37, 4), (30, 4)]
[thought] rounds whose thought mentions height/Z/descend: 521/597
[task] initial cube->goal cm: min=7.3 median=8.8 max=10.2; success needs <= 5 cm
[task] best cube->goal reached per episode: min=7.3 cm
[image] consecutive round_pre PNG identical: 0/547; missing=0
[feedback] {'fb_cg_end_OK': 547, 'fb_cg_start_OK': 547, 'fb_move_from==prev_start_OK': 547, 'fb_move_to==this_start_OK': 547, 'fb_target==prev_target_OK': 547, 'fb_tip_end_OK': 547, 'fb_tip_start_OK': 547, 'fb_verdict_matches_cg_OK': 547}
```

What `validate.py` checked:
1. File counts and outcome distribution.
2. Summary statistics of `tcp_reach_err_cm` (median, p95, max).
3. `table_guard.target_clamp` presence.
4. Achieved Z for target $Z < 0.52\text{ m}$.
5. Histogram of emitted Z integer targets.
6. Regex presence of Z-related words in `vlm_thought`.
7. MD5 hashes of consecutive pre-action PNGs (ruling out camera freezing).
8. Text regex and arithmetic consistency of 8 fields in `round_feedback`.

---

## 3. Systematic Audit: What `validate.py` Does NOT Check

### 3.1. Cube Yaw Ignored in Box Distance Calculation
- **Code Path**:
  - `validate.py:6-7`:
    ```python
    def box(p, c):  # axis-aligned approx (cube yaw ignored; flagged if mismatch)
        return math.sqrt(sum(max(abs(a - b) - H, 0) ** 2 for a, b in zip(p, c)))
    ```
  - Runtime true calculation: [`aiongenos/orchestrator/push_body.py:103-108`](file:///home/control/AionGenos/aiongenos/orchestrator/push_body.py#L103-L108) and [`aiongenos/orchestrator/isaaclab_env_interface.py:506-508`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L506-L508):
    ```python
    local = quat_rotate(quat_conj(box_quat_w), p_w - box_pos_w)
    excess = (local.abs() - half).clamp(min=0.0)
    return float(torch.norm(excess))
    ```
- **Flaw / Blind Spot**:
  `validate.py` approximates distance to an axis-aligned box. If a cube with half-width $H=0.024\text{ m}$ rotates by $45^\circ$, the actual distance to its face changes by up to $(\sqrt{2}-1) \times 0.024\text{ m} \approx 0.010\text{ m} = 1.0\text{ cm}$. `validate.py` uses a tight tolerance of $0.25\text{ cm}$ in line 44–45. Any rotated cube would fail `validate.py`.
  Furthermore, [`aiongenos/orchestrator/push_memory.py:147-166`](file:///home/control/AionGenos/aiongenos/orchestrator/push_memory.py#L147-L166) only logs `cube_b_pre` as `[x, y, z]`. The offline metadata does not store cube orientation (`cube_quat_b`), making exact offline reconstruction impossible.
- **Why `validate.py` reported 547/547 OK**:
  In run `71134939`, only 4 rounds had cube displacement $> 1\text{ mm}$ (maximum $9.4\text{ mm}$). Cube yaw was virtually zero. The check passed purely because the robot never pushed the cube.
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  has_quat = any('cube_quat' in r for e in eps for r in e['rounds'])
  disps = [r.get('cube_disp_m', 0) for e in eps for r in e['rounds']]
  print(f'cube_quat recorded: {has_quat}')
  print(f'rounds disp > 1mm: {sum(1 for d in disps if d > 0.001)}/597; max disp: {max(disps)*100:.2f} cm')
  "
  ```
  *Output*: `cube_quat recorded: False`, `rounds disp > 1mm: 4/597; max disp: 0.94 cm`.

---

### 3.2. Success Predicate Uses XY Only
- **Code Path**:
  - [`aiongenos/orchestrator/push_collect.py:310-312, 371-374`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L310-L312):
    ```python
    goal_b = env.get_goal_pose_b()
    cube_goal_dist = float(np.linalg.norm(np.array(cube_after[:2]) - np.array(goal_b[:2])))
    ...
    if cube_goal_dist <= PUSH_SUCCESS_M:
        outcome = EpisodeOutcome.SUCCESS
    ```
  - [`aiongenos/orchestrator/push_memory.py:133-134`](file:///home/control/AionGenos/aiongenos/orchestrator/push_memory.py#L133-L134):
    ```python
    @property
    def cube_goal_dist_cm(self) -> float:
        return float(np.linalg.norm(np.array(self.cube_b[:2]) - np.array(self.goal_b[:2]))) * 100.0
    ```
- **Flaw / Blind Spot**:
  `validate.py` does not check whether success requires 3D positioning, nor does it check whether the cube was knocked off the table. If the cube fell to the floor ($Z < 0$) under the goal $(X, Y)$, it would be falsely counted as a SUCCESS.
- **Artifact Verdict**:
  Ruled out. 2D Euclidean distance on the table plane is strictly less than or equal to 3D distance ($d_{2D} \le d_{3D}$). Across all 597 rounds, the minimum 2D distance achieved was $7.27\text{ cm}$, which never satisfied the $5.0\text{ cm}$ threshold. The 0/50 is not an artifact of 2D vs 3D evaluation.
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  min_2d = min(r['cube_goal_dist_m'] for e in eps for r in e['rounds'])
  print(f'min 2D distance achieved across all episodes: {min_2d*100:.2f} cm (threshold: 5.0 cm)')
  "
  ```
  *Output*: `min 2D distance achieved across all episodes: 7.27 cm (threshold: 5.0 cm)`.

---

### 3.3. Round Cap and Premature Plateau Termination (Pin-11 & Pin-12)
- **Code Path**:
  - [`aiongenos/orchestrator/push_collect.py:63-65, 79-84, 375-385`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L63-L65):
    ```python
    PUSH_ROUND_CAP = 12
    PUSH_PLATEAU_ROUNDS = 3
    PUSH_PLATEAU_MIN_DISP_M = 0.01  # 1 cm
    ...
    # Pin-12 arming: armed only after first contact
    if plateau_armed_round is None and _round_touched(contact, cube_disp):
        plateau_armed_round = round_idx + 1
    ...
    if plateau_armed_round is None:
        pass  # Pin-12: no contact yet -> only PUSH_ROUND_CAP applies
    elif cube_disp < PUSH_PLATEAU_MIN_DISP_M:
        plateau_count += 1
        if plateau_count >= PUSH_PLATEAU_ROUNDS:
            outcome = EpisodeOutcome.PUSH_PLATEAU
            break
    ```
- **Flaw / Blind Spot**:
  `validate.py` reports `outcomes={'timeout': 48, 'push_plateau': 2}` without checking why those two episodes terminated or what happened in them.
  - In 48 episodes, the robot never touched the cube. `plateau_armed_round` was `None`, so they ran for all 12 rounds and timed out.
  - In exactly 2 episodes (`79681177-225` and `cdf29531-513`), contact occurred (`first_cube_move` detected), arming the plateau counter. Because subsequent movement was $<1\text{ cm}$ for 3 rounds, they were terminated at rounds 11 and 10 respectively.
  - In episode `cdf29531-513`, round 8 moved the cube $9.4\text{ mm}$ (just $0.6\text{ mm}$ short of the $10\text{ mm}$ reset threshold!). Rounds 8, 9, 10 counted towards the plateau cutoff, terminating the episode prematurely at round 10.
- **Artifact Verdict**:
  While the plateau rule terminated the only two episodes that made contact, in both cases the cube was still $>8.2\text{ cm}$ from the goal at termination (and round 10 commanded a movement away from the cube). Thus, 0/50 was not caused by premature cutoff.
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  for e in eps:
      if e['outcome'] == 'push_plateau':
          print(f\"ep={e['episode_id']} rounds={len(e['rounds'])} final_dist={e['rounds'][-1]['cube_goal_dist_m']*100:.1f}cm\")
          for r in e['rounds']:
              if r.get('cube_disp_m', 0) > 0.001:
                  print(f\"  round {r['round']}: disp={r['cube_disp_m']*100:.2f}cm contact={r['contact']['first_cube_move']}\")
  "
  ```
  *Output*:
  - `ep=79681177-225 rounds=11 final_dist=8.8cm; round 9: disp=0.81cm`
  - `ep=cdf29531-513 rounds=10 final_dist=8.2cm; round 6: disp=0.12cm; round 8: disp=0.94cm; round 9: disp=0.36cm`

---

### 3.4. Mid-Episode Auto-Reset Detection (`flags: ['env_auto_reset']`)
- **Code Path**:
  - [`aiongenos/orchestrator/push_collect.py:299-305`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L299-L305):
    ```python
    step_count = _episode_step_count(env)
    if last_step_count is not None and step_count is not None and step_count < last_step_count:
        auto_reset = True
        flags.append("env_auto_reset")
        logger.warning(...)
        break
    ```
- **Flaw / Blind Spot**:
  If IsaacLab's internal `max_episode_length` triggers an auto-reset inside `env.step()`, `flags` receives `"env_auto_reset"`, but `outcome` remains `TIMEOUT` (initialized at line 203).
  `validate.py` line 10–12 inspects only `e["outcome"]`. It never inspects `e.get("flags")` or verifies that `len(e["rounds"]) == 12` on timeout episodes.
- **Artifact Verdict**:
  Ruled out for run `71134939`. Scanning all 50 episode files reveals zero `"env_auto_reset"` occurrences (`flags` contains only `label:pilot` and `push_plateau`). However, `validate.py` has an unhandled blind spot for this failure mode.
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json, collections
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  flags_counter = collections.Counter(f for e in eps for f in e.get('flags', []))
  print('All episode flags across run:', flags_counter)
  "
  ```
  *Output*: `All episode flags across run: Counter({'label:pilot': 50, 'push_plateau': 2})`.

---

### 3.5. Scene Guard Clamps and Reach Error Misinterpretation
- **Code Path**:
  - Scene guard definition: [`aiongenos/orchestrator/push_body.py:175-183`](file:///home/control/AionGenos/aiongenos/orchestrator/push_body.py#L175-L183) (`TABLE_GUARD_MARGIN_M = 0.010` m).
  - Target clamp & setpoint clamping: [`aiongenos/orchestrator/isaaclab_env_interface.py:587-599, 638-642, 704-705`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L587-L599):
    ```python
    tb, hits = _pb.scene_guard(tb, self._static_scene_b)
    ...
    # Carrot setpoint clamping:
    sp_g, c = _pb.scene_guard(sp_tcp, self._static_scene_b)
    if c:
        setpoint = sp_g - _pb.quat_rotate(qb, tcp_off)
        setpoint_clamps += 1
    ```
  - Reach error computation: [`aiongenos/orchestrator/push_collect.py:325`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L325):
    ```python
    tcp_reach_err_cm = (round(float(np.linalg.norm(np.array(tcp_final) - np.array([tx, ty, tz]))) * 100, 2))
    ```
- **Flaw / Blind Spot**:
  1. `validate.py` line 18–19 checks only `tg.get("target_clamp")` and reports `target_clamps=1`. It completely ignores `setpoint_clamp_steps`. In round 12 of `d42e7d92-c9c`, 82 out of 90 steps were clamped!
  2. `validate.py` line 54 reports `tcp_reach_err_cm max=9.23 cm`. It does not realize that `push_collect.py` computed reach error against the RAW VLM target ($Z=0.385\text{ m}$), which was clamped by `scene_guard` to the table safety plane ($Z=0.4541\text{ m}$). The arm reached $Z=0.4767\text{ m}$ (within $2.26\text{ cm}$ of the clamped target, but $9.23\text{ cm}$ away from the unclamped target). The $9.23\text{ cm}$ error was an artifact of the metric definition under scene guarding, not an untamed OSC controller.
  3. `validate.py` did not check the height of the table guard ($0.4541\text{ m}$) relative to the cube ($0.4683\text{ m}$). Because $0.4541 < 0.4683$, the scene guard never prevented the robot from reaching or pushing the cube.
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  for e in eps:
      for r in e['rounds']:
          tg = r.get('table_guard') or {}
          if tg.get('target_clamp'):
              print(f\"ep={e['episode_id']} r={r['round']}\")
              print(f\"  clamp info: {tg['target_clamp']}\")
              print(f\"  setpoint_clamps: {tg.get('setpoint_clamp_steps')}\")
              print(f\"  raw target_m: {r['eef_target_m']}\")
              print(f\"  tcp_final_b: {r['tcp_final_b']}\")
              print(f\"  reported reach_err: {r['tcp_reach_err_cm']} cm\")
  "
  ```
  *Output*:
  - `ep=d42e7d92-c9c r=12`
  - `clamp info: {'raw_tcp_target_b': [0.339, 0.12, 0.385], 'guarded_tcp_target_b': [0.339, 0.12, 0.4541], 'colliders': ['table']}`
  - `setpoint_clamps: 82`
  - `raw target_m: [0.339, 0.12, 0.385]`
  - `tcp_final_b: [0.3424, 0.13, 0.4767]`
  - `reported reach_err: 9.23 cm`

---

### 3.6. Orientation (ORI) Offsets and Severe Wrist Tracking Error
- **Code Path**:
  - Parsing and applying ORI: [`aiongenos/orchestrator/push_collect.py:289-290, 338-345`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L289-L290).
  - Variable stiffness controller: [`aiongenos/orchestrator/isaaclab_env_interface.py:616-620`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L616-L620):
    ```python
    action[:, 7:10] = 300.0   # position stiffness (firm)
    action[:, 10:13] = 60.0   # orientation stiffness (soft, ~1/5)
    ```
- **Flaw / Blind Spot**:
  `validate.py` contains **zero** lines checking orientation.
  1. **VLM behavior**: In 549 of 597 rounds (92%), `ori_applied` was True, but in **100% of these rounds**, the emitted offset was `[0, 0, 0]`. The VLM never exercised wrist orientation.
  2. **Controller tracking degradation**: Because orientation stiffness was reduced to $60.0$ to prevent torque saturation, whenever the arm moved towards workspace edges, the wrist experienced severe angular lag.
  3. In **86 rounds (14.4%)**, `ori_err_deg_final` exceeded $5.0^\circ$, reaching a maximum error of **$38.75^\circ$**!
- **Artifact Verdict**:
  Orientation lag did not cause the 0/50 because the arm was hovering $4.3\text{ cm}$ too high anyway. However, this is a significant unmonitored tracking degradation completely missed by `validate.py`.
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  non_zero_ori = sum(1 for e in eps for r in e['rounds'] if r.get('ori_offset_deg') and any(v != 0 for v in r['ori_offset_deg']))
  errs = [r['ori_err_deg_final'] for e in eps for r in e['rounds'] if r.get('ori_err_deg_final') is not None]
  print(f'non-zero VLM ori offsets: {non_zero_ori}/597')
  print(f'rounds with ori_err > 5 deg: {sum(1 for x in errs if x > 5)}/597; max: {max(errs):.2f} deg')
  "
  ```
  *Output*: `non-zero VLM ori offsets: 0/597`, `rounds with ori_err > 5 deg: 86/597; max: 38.75 deg`.

---

### 3.7. Torque Saturation and Controller Stalls (`tau_flag_steps`)
- **Code Path**:
  - [`aiongenos/orchestrator/isaaclab_env_interface.py:647-660, 693-694`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L647-L660):
    ```python
    if pre >= 1.0:
        flag += 1
    ...
    "tau_flag_steps": flag,  # steps with pre-clip tau/limit >= 1.0
    ```
- **Flaw / Blind Spot**:
  `validate.py` has no checks on joint torque saturation.
  - In **60 rounds (10.1%)**, `tau_flag_steps > 0`.
  - In several rounds (e.g. `b28b9d77-8ff` rounds 5, 7, 10, 11), `tau_flag_steps` reached **88 to 90 steps**—meaning the arm was pegged at maximum torque for the entire 90-step trajectory segment!
  - In these saturated rounds, position tracking error ballooned to $4.5 - 6.3\text{ cm}$.
  - `validate.py` claims "controller tracking median 0.05 cm" while ignoring that 10% of rounds suffered joint torque saturation.
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  flagged = [(e['episode_id'], r['round'], r['tau_flag_steps'], r['tcp_reach_err_cm']) for e in eps for r in e['rounds'] if r.get('tau_flag_steps', 0) > 0]
  print(f'rounds with torque saturation (tau_flag_steps > 0): {len(flagged)}/597')
  severe = [x for x in flagged if x[2] > 50]
  print(f'severe saturation (>50 steps saturated): {len(severe)} rounds; sample: {severe[:3]}')
  "
  ```
  *Output*: `rounds with torque saturation (tau_flag_steps > 0): 60/597`, `severe saturation (>50 steps saturated): 8 rounds; sample: [('296b6151-283', 9, 82, 3.94), ('392894c5-f4a', 12, 85, 3.94), ('b28b9d77-8ff', 5, 89, 5.69)]`.

---

### 3.8. Semantic Feedback Ambiguity: 1D Scalar vs 3D Spatial Geometry
- **Code Path**:
  - Feedback template: [`aiongenos/orchestrator/push_feedback.py:40-44`](file:///home/control/AionGenos/aiongenos/orchestrator/push_feedback.py#L40-L44).
  - Runtime scalar computation: [`aiongenos/orchestrator/isaaclab_env_interface.py:496-511`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L496-L511).
- **The Core Cognitive Trap Explained**:
  1. **Proprioceptive Z initialization**: Every episode starts with TCP at $Z=53$ ($0.5356\text{ m}$).
  2. **Cube vertical dimension**: The cube center is at $Z=0.4683\text{ m}$. With half-height $H=0.024\text{ m}$, the top surface is at $Z=0.4923\text{ m}$.
  3. **The 4.3 cm gap**: $0.5356\text{ m} - 0.4923\text{ m} = 0.0433\text{ m} = \mathbf{4.33\text{ cm}}$.
  4. **The feedback format**:
     ```text
     Fingertip-to-cube distance: started at 7.1 cm, ended at 7.9 cm
     Cube-to-goal distance: started at 8.8 cm, ended at 8.8 cm
     Result: No significant progress (still 8.8 cm from target). Try a different direction or larger step size.
     ```
  5. **The unresolvable ambiguity**: The scalar distance is a single 3D box distance. At $Z=53$, no matter what $(X, Y)$ coordinate the VLM chooses, the Euclidean distance can **never drop below $4.33\text{ cm}$**.
  6. **Prompt guidance misleads**: The text explicitly urges `"Try a different direction or larger step size."`
  7. **Visual collapse**: The VLM is provided an orthographic top-down camera view where Z is completely collapsed, and a 256×256 front camera view where the fingertip pad is black and a 4.3 cm height difference against a black table surface is visually ambiguous.
  8. **Behavioral outcome**: The VLM concludes that its planar direction in $(X, Y)$ is wrong, exploring various $(X, Y)$ approach angles while anchoring firmly to $Z=53$ (commanded in 509/597 rounds, 85.3%).
- **Verification Command**:
  ```bash
  python3 -c "
  import glob, json
  eps = [json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]
  r0 = eps[0]['rounds'][0]
  z_tcp = r0['ee_start_b'][2]
  z_cube = r0['cube_b_pre'][2]
  gap_cm = (z_tcp - (z_cube + 0.024)) * 100
  z53_count = sum(1 for e in eps for r in e['rounds'] if r['eef_target_int'][2] == 53)
  print(f'Initial TCP Z: {z_tcp:.4f} m (int={r0[\"ee_start_int\"][2]})')
  print(f'Cube Center Z: {z_cube:.4f} m, Cube Top Z: {z_cube+0.024:.4f} m')
  print(f'Vertical gap: {gap_cm:.2f} cm')
  print(f'Rounds where VLM kept Z=53: {z53_count}/597 ({z53_count/597*100:.1f}%)')
  "
  ```
  *Output*:
  - `Initial TCP Z: 0.5356 m (int=53)`
  - `Cube Center Z: 0.4683 m, Cube Top Z: 0.4923 m`
  - `Vertical gap: 4.33 cm`
  - `Rounds where VLM kept Z=53: 509/597 (85.3%)`

---

## 4. Summary Table of Pipeline Elements and Audit Coverage

| Pipeline Element / Hypothesis | Checked by `validate.py`? | Actual Status in Run `71134939` | Could it cause a 0/50 artifact? | Evidence Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Cube Yaw in Box Distance** | ❌ (Approximated as axis-aligned; ignores yaw) | Negligible yaw (cube moved $>1\text{ mm}$ in only 4 rounds) | No for this run; but would fail on any active push run | `validate.py:6-7`; [`push_body.py:103`](file:///home/control/AionGenos/aiongenos/orchestrator/push_body.py#L103) |
| **Success Uses XY Only** | ❌ (Reports numbers without checking 2D vs 3D) | 2D min distance achieved was $7.27\text{ cm} > 5.0\text{ cm}$ | No (2D check is more permissive; no false negatives) | [`push_collect.py:311`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L311); `min_cg=7.3cm` |
| **Round Cap (12 rounds)** | ❌ (Only counts total rounds) | 48 timeouts, 2 plateau exits | No (12 rounds is plenty; scripted pushes succeed in 2) | [`push_collect.py:63`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L63); `logs/wp3a_reach_real.log` |
| **Pin-12 Plateau Premature Cutoff** | ❌ (Unexamined) | Terminated the only 2 contact episodes at rounds 10 & 11 | Minor impact, but cube was still $>8\text{ cm}$ away | [`push_collect.py:377-385`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L377-L385); `ep=cdf29531-513` |
| **IsaacLab Mid-Episode Auto-Reset** | ❌ (Never checks `flags` on timeouts) | 0 auto-resets occurred (`flags` clean) | No for this run; but an unhandled blind spot | [`push_collect.py:299-305`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L299-L305) |
| **Scene Guard Target Clamp** | ⚠️ Partial (counts target clamp only; ignores setpoints) | 1 target clamp (table), 82 setpoint clamps in that round | No (table guard floor is $0.4541\text{ m} < 0.4683\text{ m}$ cube center) | [`isaaclab_env_interface.py:591, 642`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L591); `ep=d42e7d92-c9c` |
| **Reach Error Max (9.23 cm)** | ⚠️ Misleading (reported raw without diagnosis) | Caused by comparing to raw target rather than guarded target | No (controller tracked guarded target within 2.2 cm) | [`push_collect.py:325`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L325) |
| **Orientation (ORI) Offsets** | ❌ Zero checks | VLM emitted `[0, 0, 0]` in 100% of rounds | No (VLM never commanded rotation) | `collect_dumps/71134939/*/meta.json` |
| **Orientation Tracking Error** | ❌ Zero checks | 86 rounds had error $>5^\circ$, up to $38.75^\circ$ | No (arm was hovering too high anyway) | [`isaaclab_env_interface.py:618`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L618); `max=38.75 deg` |
| **Torque Saturation (`tau_flag_steps`)**| ❌ Zero checks | 60 rounds saturated ($\tau \ge 1.0$), up to 90 steps | No (saturation occurred mainly at extreme reaches) | [`isaaclab_env_interface.py:659`](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L659); 60 rounds |
| **1D Scalar Feedback Ambiguity** | ❌ (Only verified string regex matching) | Reports 1D distance without $(\Delta X, \Delta Y, \Delta Z)$ | **YES: Principal driver of teacher cognitive failure** | [`push_feedback.py:40-44`](file:///home/control/AionGenos/aiongenos/orchestrator/push_feedback.py#L40-L44); 85.3% rounds at $Z=53$ |

---

## 5. Conclusion & Recommendations

1. **The 0/50 is REAL**: The zero success rate is not a hardware error, controller fault, or simulation artifact. The robot arm physically executed the VLM's commands with high fidelity (median error $0.05\text{ cm}$).
2. **The failure is a Perceptual & Informational Deficit**:
   - The teacher is initialized hovering $4.3\text{ cm}$ above the cube.
   - The teacher is fed a 1D scalar distance report that fails to separate planar error from height error.
   - The top-down image eliminates vertical disparity, while the low-resolution front image renders the 4.3 cm gap imperceptible to the model.
   - The teacher misattributes the persistent $\ge 4.3\text{ cm}$ distance to planar misdirection and endlessly searches in $(X, Y)$ at $Z=53$.
3. **Recommended Fixes for the Pipeline & Instrument**:
   - In `validate.py`: Add validation for `flags` (`env_auto_reset`), `setpoint_clamp_steps`, `ori_err_deg_final`, `tau_flag_steps`, and compute reach error against guarded targets.
   - In `meta.json`: Record `cube_quat_b` so that true oriented bounding-box distances can be verified offline.
   - In `push_feedback.py`: Decompose the scalar distance into planar and vertical components (e.g. `Horizontal: ... cm, Height: ... cm`) or provide 3D offsets $(\Delta X, \Delta Y, \Delta Z)$ to break the 1D observability trap.
