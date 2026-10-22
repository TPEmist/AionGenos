# Verification Report: Google DeepMind "Gemini 4 Argon" Robotics Claims

**Role**: researcher (Source verifier)  
**Task Definition**: `/home/control/audit/rung2p_diag/spec.md` (lines 35–39)  
**Date**: 2026-10-22  
**Target Output**: `/home/control/audit/rung2p_diag/researcher.md`  
**Scratch Directory**: `/home/control/audit/rung2p_diag/scratch_researcher/`

---

## 1. Executive Summary

All five claims regarding Google DeepMind's "Gemini 4 Argon" robotics workflows are **CONFIRMED** directly by the three primary sources.

| # | Claim | Status | Primary Source | Key Evidence / Quote |
|---|---|---|---|---|
| 1 | Argon acts as reasoner/coder over action primitives, not a VLA | **CONFIRMED** | Developers Blog & DeepMind VLA Model Page | *"Argon reasons with a visual coordinate harness and action primitives"* (Code-as-Policies: `robot.grasp`, `robot.place`, etc.); while DeepMind's dedicated VLA model is **Gemini Robotics 2** (Input: Text, Image; Output: Actions). |
| 2 | Harness supplies calibrated camera + projected world coordinates + axis convention in prompt | **CONFIRMED** | Developers Blog (Zero-shot control) | *"calibrated wrist camera with projected 2 cm world coordinates and jaw-closing reticle"*; prompt contains explicit *Visual Coordinate Reference* defining `+X (UP)`, `+Y (LEFT)`, `+Z (Height)`, and yellow coordinate numbers. |
| 3 | Contact skills practised in MuJoCo twins with "no sim cheating" rules | **CONFIRMED** | Developers Blog (Spot mobile manipulation & Real2Sim) | Spot foot-pedal practice in MuJoCo twin; Real2Sim explicitly enforces *"No sim cheating: task objects may move only through real MuJoCo contact with the robot hands and the environment (mj_step)"* banning kinematic welds, external forces, and state teleports. |
| 4 | 56%→75% from VLA fine-tune on 4,500+ sim episodes | **CONFIRMED** | Developers Blog (Action improvement via simulation) | Argon synthesizes MuJoCo twin and trajectory generator to *"collect 4,500+ domain-randomized episodes in simulation—boosting real-world physical robot Success Rate from 56% to 75%"*. |
| 5 | Cornhole video-to-sim-to-real 7 shots | **CONFIRMED** | Google Blog (The Keyword) | Video-to-Sim-to-Real: Argon watched human cornhole video, generated simulation code, and transferred to Apptronik Apollo humanoid which *"quickly sank seven consecutive shots in a real-world trial"*. |

---

## 2. Primary Sources & Verification Artifacts

The three authoritative primary sources were downloaded to local disk under `/home/control/audit/rung2p_diag/scratch_researcher/` without modifying any repository files:

1. **Source 1 (Developers Blog)**:
   - **URL**: `https://developers.googleblog.com/gemini-4-argon-for-robotics`
   - **Title**: *Gemini 4 Argon for Robotics* (Author: Kanishka Rao, Oct 13, 2026)
   - **Disk Cache**: `/home/control/audit/rung2p_diag/scratch_researcher/url1.html` (text: `url1.txt`)
2. **Source 2 (Google Blog / The Keyword)**:
   - **URL**: `https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/`
   - **Title**: *Gemini 4 Argon is now available for everyone* (Author: Koray Kavukcuoglu, Oct 13, 2026)
   - **Disk Cache**: `/home/control/audit/rung2p_diag/scratch_researcher/url2.html` (text: `url2.txt`)
3. **Source 3 (DeepMind VLA Landing Page)**:
   - **URL**: `https://deepmind.google/models/gemini-robotics/vla/`
   - **Title**: *Gemini Robotics 2 — Google DeepMind*
   - **Disk Cache**: `/home/control/audit/rung2p_diag/scratch_researcher/url3.html` (text: `url3.txt`)

---

## 3. Detailed Verification of Claims

### Claim 1: Argon acts as reasoner/coder over action primitives, not a VLA

- **Status**: **CONFIRMED**
- **Data Path & Citation**:
  - `/home/control/audit/rung2p_diag/scratch_researcher/url1.txt:15,41-42,71-82,217`
  - `/home/control/audit/rung2p_diag/scratch_researcher/url3.txt:6-10,41-45`
  - `/home/control/audit/rung2p_diag/scratch_researcher/url2.txt:134-136`
- **Primary Source Verbatim Quotes**:
  - `https://developers.googleblog.com/gemini-4-argon-for-robotics`:
    > *"Gemini 4 Argon marks a step change in physical understanding, code generation, and visual-semantic reasoning—unlocking new workflows across the robotics stack..."* (`url1.txt:15`)
    > *"Argon controls a simple robotic arm to place a fallen mug upright and put the crumpled napkin inside. Argon reasons with a visual coordinate harness and action primitives to perform this task over several turns."* (`url1.txt:42`)
    > *"## Code-as-Policies Primitives (`POST http://127.0.0.1:8081/plan`)*  
    > `robot.look_at(x=0.35, y=0.13, z=0.14, grid_z=0.015)`  
    > `x, y = robot.deproject(u=0.52, v=0.48, z_plane=0.015)`  
    > `robot.grasp(x=x, y=y, z=0.015, yaw_deg=-35, pitch_deg=90)`  
    > `robot.place(x=0.24, y=0.06, z=0.075)`  
    > `robot.place_until_contact(x=0.24, y=0.06, z=0.015, max_lag=0.012, relief=0.002)`  
    > `robot.goto(x=0.28, y=0.05, z=0.04, arc_z=0.14, pitch_deg=25, azimuth_deg=90, roll_deg=0, speed=0.10)`  
    > `robot.move_by(forward=0.025, dz=-0.002, dpitch_deg=-3, droll_deg=5, speed=0.04)`  
    > `robot.move_until_contact(dz=-0.06, speed=0.03, max_lag=0.012, relief=0.002)`  
    > `robot.open_gripper() / robot.close_gripper() / robot.home() / robot.done()`" (`url1.txt:71-82`)
    > *"Argon can generate new data in simulation to improve performance of generalist vision-language-action (VLA) models."* (`url1.txt:217`)
  - `https://deepmind.google/models/gemini-robotics/vla/`:
    > *"Gemini Robotics 2"*  
    > *"Our most advanced VLA model: capable of intelligently controlling any type of robot, from tabletop robots to full humanoids"*  
    > *"Input: Text, Image"*  
    > *"Output: Actions (stabilization_action)"* (`url3.txt:6-10,41-45`)
- **Re-runnable Verification Commands**:
  ```bash
  # Check Argon as reasoner/coder over action primitives:
  curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -A 2 -i "visual coordinate harness and action primitives"
  
  # Check DeepMind dedicated VLA model designation (Gemini Robotics 2 vs Argon):
  curl -sL https://deepmind.google/models/gemini-robotics/vla/ | grep -o -E "Gemini Robotics 2|Our most advanced VLA model|stabilization_action" | head -n 5
  
  # Check local scratch lines:
  sed -n '41,43p' /home/control/audit/rung2p_diag/scratch_researcher/url1.txt
  sed -n '71,82p' /home/control/audit/rung2p_diag/scratch_researcher/url1.txt
  ```
- **Analysis**:
  Argon is a generalist multimodal reasoning and code generation foundation model (text/image/video in, code/text out). When applied to robotic control, Argon operates as a high-level visual reasoner issuing Code-as-Policies action primitives (`robot.grasp`, `robot.goto`, `curl http://.../plan`) or synthesizing simulation twins. It is explicitly distinguished from Google DeepMind's direct end-to-end VLA model, **Gemini Robotics 2**, whose native output is low-level robot actions. In fact, Argon is used as an offline generator to produce training rollouts for fine-tuning generalist VLA models.

---

### Claim 2: Harness supplies calibrated camera + projected world coordinates + axis convention in prompt

- **Status**: **CONFIRMED**
- **Data Path & Citation**:
  - `/home/control/audit/rung2p_diag/scratch_researcher/url1.txt:44,51-60`
- **Primary Source Verbatim Quotes**:
  - `https://developers.googleblog.com/gemini-4-argon-for-robotics`:
    > *"Left: 3rd-person real robot view; Right: calibrated wrist camera with projected 2 cm world coordinates and jaw-closing reticle."* (`url1.txt:44`)
    > *"## Execution Discipline  
    > - Simply output 1 sentence observation followed immediately by your `curl` command (with `# Plan:` on Turn 1 and `# Thought:` on every turn). Everything needed is in `obs.json` and the calibrated reticle/grid drawn on `wrist_cam.png`."* (`url1.txt:51`)
    > *"## Visual Coordinate Reference (Annotated on wrist_cam.png)  
    > - `+X` (UP in image): Away from robot base | `-X` (DOWN): Towards robot base  
    > - `+Y` (LEFT in image): World left         | `-Y` (RIGHT): World right  
    > - `+Z`: Height above table                | `Yellow numbers`: World (X, Y) in centimetres (2 cm grid at `grid_z`)  
    > - `Cyan + crosshair`: Current 3D pinch center  
    > - `Cyan [ + ] brackets`: Current jaw opening and closing line  
    > - `Green line`: Current object long-axis orientation (`yaw_deg`: 0° = vertical along +X, 90° = horizontal along +Y)  
    > - `pitch_deg = 90°`: Straight down (-Z) top-down grasp/place; `pitch_deg < 60°`: Tilted coaxial approach along finger axis"* (`url1.txt:53-60`)
- **Re-runnable Verification Commands**:
  ```bash
  # Check camera calibration & projected coordinates in caption:
  curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -i "projected 2 cm world coordinates"
  
  # Check axis convention and visual coordinate reference in prompt:
  curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -A 8 "Visual Coordinate Reference (Annotated on wrist_cam.png)"
  
  # Check local scratch lines:
  sed -n '44,61p' /home/control/audit/rung2p_diag/scratch_researcher/url1.txt
  ```
- **Analysis**:
  The Argon zero-shot control harness eliminates spatial ambiguity by:
  1. Calibrating the camera and projecting a metric 2 cm grid onto the image (`wrist_cam.png`) with yellow numerical coordinate annotations.
  2. Grounding the coordinate frame directly to the 2D image plane in the system prompt (`+X` = UP, `-X` = DOWN, `+Y` = LEFT, `-Y` = RIGHT, `+Z` = Height above table).
  3. Overlaying visual reticles indicating current 3D pinch center (cyan crosshair) and jaw closing boundaries (cyan brackets).

---

### Claim 3: Contact skills practised in MuJoCo twins with "no sim cheating" rules

- **Status**: **CONFIRMED**
- **Data Path & Citation**:
  - `/home/control/audit/rung2p_diag/scratch_researcher/url1.txt:31-34,110-112,126-128`
- **Primary Source Verbatim Quotes**:
  - `https://developers.googleblog.com/gemini-4-argon-for-robotics`:
    > *"Spot mobile manipulation: Putting in the trash bin with MuJoCo practice  
    > Argon controls a Boston Dynamics Spot® quadruped (12-DoF legs + 6-DoF arm) to learn a new skill: stepping on a foot-pedal trash bin to throw away soda cans. Argon creates an articulated MuJoCo digital twin of a foot-pedal trash bin to practice its moves before stepping on the physical pedal and dropping soda cans into the open bin."* (`url1.txt:31-32`)
    > *"Spot Mobile Manipulation — Real-to-Sim-to-Real foot-pedal trash bin disposal: Spot picking up the soda can, checking its wrist camera, practicing 3-leg tripod balance in MuJoCo, stepping on the foot pedal, verifying hand centering in the open bin, and dropping the can inside."* (`url1.txt:34`)
    > *"Argon views a real robot teleoperation episode and develops a digital twin; it obtains or creates simulation assets that look and behave like the real objects upon contact with the dexterous hands. Argon tunes the assets and scenes to match sim visuals and contact events with those in the real recorded data in an iterative visual-reasoning loop."* (`url1.txt:110`)
    > *"No sim cheating: task objects may move only through real MuJoCo contact with the robot hands and the environment (mj_step).  
    > Not allowed after t = 0: changing MjModel parameters; applying external forces or torques to objects; welds or equality constraints; feedforward torques beyond joint-space PD; setting or rolling back object qpos/qvel; disabling or excluding collisions; reporting contact forces that don't come from the MuJoCo solver (for example, copying the logged tactile readings)."* (`url1.txt:126-128`)
- **Re-runnable Verification Commands**:
  ```bash
  # Check Spot mobile manipulation with MuJoCo practice:
  curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -A 2 -i "with MuJoCo practice"
  
  # Check "No sim cheating" rules verbatim:
  curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -A 3 -i "No sim cheating"
  
  # Check local scratch lines:
  sed -n '31,35p' /home/control/audit/rung2p_diag/scratch_researcher/url1.txt
  sed -n '126,128p' /home/control/audit/rung2p_diag/scratch_researcher/url1.txt
  ```
- **Analysis**:
  Argon uses physically accurate digital twins in MuJoCo to practice complex dynamic contact interactions (e.g. tripod balance while stepping on a sprung pedal). Critically, the prompt forbids "sim cheating" via explicit negative constraints: all object displacements must result exclusively from solver-evaluated contacts (`mj_step`), strictly prohibiting equality welds, artificial external forces, collision disabling, or state rollbacks (`qpos`/`qvel`).

---

### Claim 4: 56%→75% from VLA fine-tune on 4,500+ sim episodes

- **Status**: **CONFIRMED**
- **Data Path & Citation**:
  - `/home/control/audit/rung2p_diag/scratch_researcher/url1.txt:217-223,230`
- **Primary Source Verbatim Quotes**:
  - `https://developers.googleblog.com/gemini-4-argon-for-robotics`:
    > *"Argon can generate new data in simulation to improve performance of generalist vision-language-action (VLA) models. Starting from a single RGB photo of the real tabletop, Argon autonomously builds a calibrated MuJoCo simulation twin, defines new tasks, and synthesizes a closed-loop motion generator to collect 4,500+ domain-randomized episodes in simulation—boosting real-world physical robot Success Rate from 56% to 75% and reducing completion time from 35s to 24s."* (`url1.txt:217-219`)
    > *"Action Improvement via Simulation: improves the real-world evaluation benchmark (56% → 75% Success Rate and 35s → 24s Completion Time)."* (`url1.txt:223`)
    > *"3. Synthesize a closed-loop IK trajectory generator across ±10 cm pose randomization, verify `reward == 1.0` in MuJoCo physics, and export 4,500+ episodes for VLA fine-tuning."* (`url1.txt:230`)
- **Re-runnable Verification Commands**:
  ```bash
  # Check 56% to 75% benchmark improvement from sim VLA fine-tuning:
  curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -C 2 -i "56% to 75%"
  
  # Check 4,500+ episodes export for VLA fine-tuning:
  curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -i "4,500+ episodes for VLA fine-tuning"
  
  # Check local scratch lines:
  sed -n '217,231p' /home/control/audit/rung2p_diag/scratch_researcher/url1.txt
  ```
- **Analysis**:
  The primary source confirms that starting from a single photo of a real setup, Argon constructed a procedural MuJoCo twin, synthesized 4,500+ domain-randomized rollout episodes with inverse kinematics, and exported them to fine-tune a generalist VLA policy. This fine-tuning elevated physical real-robot benchmark success from 56% to 75% and decreased execution time from 35s to 24s.

---

### Claim 5: Cornhole video-to-sim-to-real 7 shots

- **Status**: **CONFIRMED**
- **Data Path & Citation**:
  - `/home/control/audit/rung2p_diag/scratch_researcher/url2.txt:138-142`
- **Primary Source Verbatim Quotes**:
  - `https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/`:
    > *"To demonstrate these capabilities in action, we tested Argon’s ability to learn an out-of-distribution physical skill simply by watching. In an internal test, Argon watched a raw video of a human playing cornhole, mapped the spatial coordinates of the environment, and calculated the required whole-body joint movements. It then autonomously built the simulation code. When transferred onto Apptronik’s Apollo humanoid, the robot quickly sank seven consecutive shots in a real-world trial.*  
    > *This "Video-to-Sim-to-Real" pipeline compresses weeks of manual simulation modeling into a few hours, transforming ordinary videos into a scalable, infinite training ground for robotics."* (`url2.txt:138-142`)
- **Re-runnable Verification Commands**:
  ```bash
  # Check cornhole video-to-sim-to-real and 7 consecutive shots on Apollo humanoid:
  curl -sL https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/ | grep -A 4 -i "playing cornhole"
  
  # Check local scratch lines:
  sed -n '138,142p' /home/control/audit/rung2p_diag/scratch_researcher/url2.txt
  ```
- **Analysis**:
  The primary announcement from Google DeepMind confirms that Argon observed a human cornhole video, mapped 3D coordinates, computed whole-body joint motions, and generated simulation code. When the resulting policy was transferred to the Apptronik Apollo humanoid, it made 7 consecutive cornhole shots on physical hardware.

---

## 4. Synthesis & Relevance to AionGenos Rung-2′ Diagnosis

The verification of these five claims highlights key architectural differences between Argon's robotics paradigm and the current AionGenos rung-2′ configuration (`run 71134939`):

1. **Visual-Spatial Grounding (Argon vs AionGenos Rung-2′)**:
   - **Argon**: Harness projects calibrated 2 cm metric grid overlays and reticles directly onto images, and specifies explicit image-to-base axis alignments (`+X`: UP, `+Y`: LEFT).
   - **AionGenos**: In `aiongenos/vlm/prompts.py:154-155`:
     ```python
     "The yellow cube and the green zone (flat green disc on the table) are seen in\n"
     "the image; their positions are not given as numbers.\n"
     ```
     The teacher receives raw 256×256 pixels without visual grid projection, yet is expected to command discrete unprojected millimeter-scale Cartesian base-frame coordinates (`LEFT_TARGET_POS: X=<int> Y=<int> Z=<int>`). Without a visual coordinate harness, the VLM suffers from severe coordinate frame ambiguity and height anchoring.

2. **Primitive Abstraction**:
   - **Argon**: Emits structured action primitives (`goto`, `move_until_contact`, `place_until_contact`, `grasp`) with closed-loop visual checks.
   - **AionGenos**: Rung-2′ forces the teacher to discover raw Cartesian trajectories point-by-point, causing failure modes where the model repeatedly targets incorrect Z planes without contact feedback.

3. **Physics Integrity ("No Sim Cheating")**:
   - Argon's strict ban on simulation cheating aligns with AionGenos's founding charter (`docs/aiongenos_founding_intent.md`): knowledge must be earned conditionally via unassisted physics, and marginal grants must be transparently tracked (`docs/harness_grant_ledger.md`).

---

## 5. Verification Command Summary

All findings can be reproduced with a single bash execution:

```bash
# 1. Reasoner/coder vs VLA
curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -A 2 -i "visual coordinate harness and action primitives"
curl -sL https://deepmind.google/models/gemini-robotics/vla/ | grep -o -E "Gemini Robotics 2|Our most advanced VLA model|stabilization_action" | head -n 3

# 2. Visual coordinate harness & prompt conventions
curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -A 7 "Visual Coordinate Reference (Annotated on wrist_cam.png)"

# 3. MuJoCo twins & no sim cheating
curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -A 3 -i "No sim cheating"

# 4. 56% to 75% via 4,500+ sim episodes
curl -sL https://developers.googleblog.com/gemini-4-argon-for-robotics | grep -C 2 -i "56% to 75%"

# 5. Cornhole video-to-sim-to-real 7 shots
curl -sL https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/ | grep -A 4 -i "playing cornhole"
```
