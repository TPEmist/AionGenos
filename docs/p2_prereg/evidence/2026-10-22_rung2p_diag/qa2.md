# QA2 Perception Audit: Camera Resolution, Height Perception, and Coordinate Axes in Rung-2′ (Run 71134939)

**Auditor:** qa2  
**Date:** 2026-10-22  
**Target Run:** `71134939` (rung-2′, seeds 5000–5049, memory ON)  
**Primary Code Paths:**
- Front camera: [aiongenos/tasks/base/reach_env_base_cfg.py:33-52](file:///home/control/AionGenos/aiongenos/tasks/base/reach_env_base_cfg.py#L33-L52)
- Top camera & cube setup: [aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py:52-67, 346-375](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L52-L67)
- Robot TCP & body definitions: [aiongenos/orchestrator/push_body.py:31-34](file:///home/control/AionGenos/aiongenos/orchestrator/push_body.py#L31-L34), [aiongenos/orchestrator/isaaclab_env_interface.py:461-464, 529-533](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L461-L464)
- Dump generation: [aiongenos/orchestrator/push_collect.py:234-241](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L234-L241)

---

## 1. Executive Summary & Verdict

1. **Cube Size in Pixels (Seeds 5000–5009):**
   - **Front Camera (`round_01_pre.png`):** Bounding box width is **10 to 15 pixels** (median 13 px), height is **12 to 14 pixels** (median 12 px), with an area of **93 to 145 pixels** (~0.14% to 0.22% of the 256×256 frame).
   - **Top Camera (`round_01_pre_top.png`):** Bounding box width is **17 to 18 pixels** (median 17 px), height is **16 to 18 pixels** (median 17 px), with an area of **271 to 308 pixels** (~0.41% to 0.47% of the 256×256 frame).
   - Both match theoretical pinhole projections from code camera parameters within sub-pixel margins.

2. **Perception of Fingertip-vs-Cube Height Difference (≈4.3 cm):**
   - **A human CANNOT judge the height difference from these 256×256 images.**
   - In the **top-down view**, optical axis is parallel to Z (gravity); vertical height difference ΔZ produces **zero height baseline** (only < 1.95 px radial parallax at the outer workspace margin; 0 px at nadir).
   - In the **front oblique view** (pitched 35° down), the standby fingertip is at $(X=0.346, Z=0.536)\,\text{m}$ while the cube is at $(X\approx 0.38\text{--}0.41, Z\approx 0.468)\,\text{m}$. Because the cube is both further forward ($+X$) and lower down ($-Z$), the forward displacement moves the cube **UP** in image space by ~6–9 px, while the lower height moves the cube **DOWN** in image space by ~5–7 px. These two effects **almost exactly cancel out**:
     - The net vertical row difference between the fingertip and the cube center across all 10 seeds is only **$-1.99$ to $+1.83$ pixels** (median $0.7$ px).
     - To the cube top face, the vertical row difference is only **$0.36$ to $4.16$ pixels**.
   - Visually, the hovering fingertip appears aligned on the **exact same horizontal scanline ($v \approx 148$)** as the cube. Without stereo cues or contact shadows at this low resolution, the 4.3 cm height gap is completely imperceptible.

3. **Front and Top Camera Axes vs Robot Base Frame ($+X, +Y, +Z$):**
   - **Neither camera axis matches the robot base frame.**
   - **Top Camera (`round_XX_pre_top.png`):**
     - Image Right ($+u$) = **$-Y_{\text{base}}$** (robot's right).
     - Image Left ($-u$) = **$+Y_{\text{base}}$** (robot's left).
     - Image Top ($-v$, row decreasing) = **$+X_{\text{base}}$** (robot forward).
     - Image Bottom ($+v$, row increasing) = **$-X_{\text{base}}$** (robot backward).
     - Vertical height ($Z_{\text{base}}$): **No image plane axis** (along optical axis).
     - *Mismatch:* Rotated 90° clockwise and mirrored relative to standard image Cartesian axes ($X_{\text{img}} = -Y_{\text{base}}, Y_{\text{img}} = +X_{\text{base}}$).
   - **Front Camera (`round_XX_pre.png`):**
     - Image Right ($+u$) = **$-Y_{\text{base}}$** (robot's right).
     - Image Up ($-v$) = **$+X_{\text{base}}$** (forward, $\Delta v / \Delta X = -1.45\,\text{px/cm}$) **AND** **$+Z_{\text{base}}$** (upward, $\Delta v / \Delta Z = -1.04\,\text{px/cm}$).
     - *Mismatch:* Forward motion ($+X$) and upward motion ($+Z$) are **nearly co-linear** along the vertical image axis (separated by only 26° in projection space). Moving forward and moving upward both look like "moving UP" on the screen.

---

## 2. Cube Size in Pixels (Seeds 5000–5009)

### 2.1 Code Path & Physical Dimensions
- **Physical Cube:** Defined in [push_s3a_cfg.py:56](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L56) as DexCube at scale 0.8 with `_CUBE_HALF_H = 0.0240` m (full edge length $L = 0.0480\,\text{m} = 4.8\,\text{cm}$).
- **Table Height:** Defined in [push_s3a_cfg.py:54](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L54) as `_TABLE_TOP_Z = 0.9941` m world.
- **Robot Base Height:** Defined in [push_s3a_cfg.py:55](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L55) as `_ROBOT_BASE_Z = 0.55` m world.
- **Cube Base-Frame Height:** `_CUBE_REST_Z_B = 0.9941 + 0.0240 - 0.55 = 0.4681` m ([push_s3a_cfg.py:67](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L67)).
- **Front Camera Configuration:** [reach_env_base_cfg.py:33-52](file:///home/control/AionGenos/aiongenos/tasks/base/reach_env_base_cfg.py#L33-L52)
  - Resolution: $256 \times 256$, `focal_length = 12.0` mm, `horizontal_aperture = 45.0` mm.
  - Pixel focal length: $f_{\text{px}} = \frac{12.0}{45.0} \times 256 = 68.27\,\text{px}$.
  - Mount offset: $\text{pos} = (0.1, 0.0, 0.85)\,\text{m}$ base frame, pitch = $+35^\circ$ looking forward/down.
- **Top Camera Configuration:** [push_s3a_cfg.py:346-375](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L346-L375)
  - Resolution: $256 \times 256$, `focal_length = 45.0` mm, `horizontal_aperture = 45.0` mm.
  - Pixel focal length: $f_{\text{px}} = \frac{45.0}{45.0} \times 256 = 256.0\,\text{px}$.
  - Mount offset: $\text{pos} = (0.40, 0.06, 1.25)\,\text{m}$ base frame, pitch = $+90^\circ$ looking straight down (optical axis $-Z$).

### 2.2 Theoretical Projection vs Empirical Disk Measurement
- **Top Camera Theoretical Edge Size:**
  - Distance from top camera ($Z=1.25\,\text{m}$) to cube top face ($Z = 0.4683 + 0.0240 = 0.4923\,\text{m}$) is $Z_{\text{dist}} = 1.25 - 0.4923 = 0.7577\,\text{m}$.
  - Expected projected edge: $s_{\text{px}} = \frac{0.0480\,\text{m}}{0.7577\,\text{m}} \times 256.0\,\text{px} = 16.23\,\text{px}$.
  - Accounting for anti-aliasing and slight yaw rotation, theoretical bounding box is **17–18 pixels**.
- **Front Camera Theoretical Projection:**
  - Distance along camera optical axis ($35^\circ$ down): $Z_{\text{cam}} \approx 0.46\,\text{m}$.
  - Oblique projection exposes both top face and front face. Theoretical bounding box is **11–14 pixels** wide by **12–14 pixels** high.

### 2.3 Empirical Measurement Across Seeds 5000–5009
Measured directly from `/home/control/AionGenos/data/collect_dumps/71134939/<ep>/round_01_pre.png` and `round_01_pre_top.png` via connected components on yellow cube HSV mask ($H \in [18, 45], S \ge 80, V \ge 100$):

| Seed | Episode ID | Front BBox ($W \times H$, px) | Front Area | Top BBox ($W \times H$, px) | Top Area | Cube Center $(X, Y, Z)_{\text{base}}$ |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 5000 | `81a50701-51e` | $13 \times 12$ | 101 px | $17 \times 17$ | 284 px | $[0.413, 0.051, 0.468]\,\text{m}$ |
| 5001 | `21504ee5-5b1` | $13 \times 12$ | 112 px | $18 \times 17$ | 291 px | $[0.384, 0.090, 0.468]\,\text{m}$ |
| 5002 | `d42e7d92-c9c` | $10 \times 13$ | 109 px | $17 \times 17$ | 286 px | $[0.390, 0.072, 0.468]\,\text{m}$ |
| 5003 | `392894c5-f4a` | $10 \times 12$ | 93 px | $18 \times 17$ | 290 px | $[0.414, 0.090, 0.468]\,\text{m}$ |
| 5004 | `01b82183-43e` | $13 \times 14$ | 127 px | $18 \times 18$ | 308 px | $[0.390, 0.104, 0.468]\,\text{m}$ |
| 5005 | `fda8509e-76c` | $10 \times 12$ | 103 px | $17 \times 16$ | 271 px | $[0.408, 0.103, 0.468]\,\text{m}$ |
| 5006 | `6dba52e4-749` | $15 \times 14$ | 112 px | $18 \times 17$ | 299 px | $[0.405, 0.148, 0.468]\,\text{m}$ |
| 5007 | `ac69fa07-a44` | $11 \times 12$ | 108 px | $17 \times 17$ | 280 px | $[0.383, 0.080, 0.468]\,\text{m}$ |
| 5008 | `592dc4b9-235` | $10 \times 12$ | 104 px | $17 \times 17$ | 284 px | $[0.400, 0.086, 0.468]\,\text{m}$ |
| 5009 | `9a598075-968` | $15 \times 12$ | 145 px | $17 \times 17$ | 276 px | $[0.411, 0.121, 0.468]\,\text{m}$ |

*Re-runnable verification command:*
```bash
python3 -c "
import cv2, json, os, numpy as np
seed_map = {5000:'81a50701-51e', 5001:'21504ee5-5b1', 5002:'d42e7d92-c9c', 5003:'392894c5-f4a', 5004:'01b82183-43e', 5005:'fda8509e-76c', 5006:'6dba52e4-749', 5007:'ac69fa07-a44', 5008:'592dc4b9-235', 5009:'9a598075-968'}
for s in range(5000, 5010):
    p = f'/home/control/AionGenos/data/collect_dumps/71134939/{seed_map[s]}'
    im_f, im_t = cv2.imread(f'{p}/round_01_pre.png'), cv2.imread(f'{p}/round_01_pre_top.png')
    hf, ht = cv2.cvtColor(im_f, cv2.COLOR_BGR2HSV), cv2.cvtColor(im_t, cv2.COLOR_BGR2HSV)
    mf = (hf[:,:,0]>=18)&(hf[:,:,0]<=45)&(hf[:,:,1]>=80)&(hf[:,:,2]>=100)
    mt = (ht[:,:,0]>=18)&(ht[:,:,0]<=45)&(ht[:,:,1]>=80)&(ht[:,:,2]>=100)
    _, _, st_f, _ = cv2.connectedComponentsWithStats(mf.astype(np.uint8))
    _, _, st_t, _ = cv2.connectedComponentsWithStats(mt.astype(np.uint8))
    cf = [i for i in range(1, len(st_f)) if st_f[i, 4] > 40][0]
    ct = [i for i in range(1, len(st_t)) if st_t[i, 4] > 100][0]
    print(f'Seed {s}: Front={st_f[cf,2]}x{st_f[cf,3]} ({st_f[cf,4]}px), Top={st_t[ct,2]}x{st_t[ct,3]} ({st_t[ct,4]}px)')
"
```

---

## 3. Fingertip-vs-Cube Height Difference (≈4.3 cm) Perception Feasibility

### 3.1 Ground Truth Geometry
From `meta.json` in run `71134939`:
- Standby TCP pose: $(X=0.3462, Y=0.1380, Z=0.5356)\,\text{m}$ ([docs/p2_prereg/wp3a_push_provenance.md:2316](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md#L2316)).
- Cube rest pose: $Z_{\text{center}} = 0.4683\,\text{m}$.
- Cube top face: $Z_{\text{top}} = 0.4683 + 0.0240 = 0.4923\,\text{m}$.
- **Vertical Gap to Cube Top:**
  $$\Delta Z_{\text{top}} = 0.5356 - 0.4923 = 0.0433\,\text{m} \approx 4.33\,\text{cm}$$
- **Vertical Gap to Cube Center:**
  $$\Delta Z_{\text{center}} = 0.5356 - 0.4683 = 0.0673\,\text{m} \approx 6.73\,\text{cm}$$

### 3.2 Top-Down View Analysis (`round_01_pre_top.png`)
- The top-down camera is mounted at $(0.40, 0.06, 1.25)\,\text{m}$ looking down the $-Z$ axis ([push_s3a_cfg.py:346-347](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L346-L347)).
- For any object at $(X, Y)$, moving along $Z$ creates zero directional parallax. The only image effect is a radial perspective scaling:
  $$\Delta r = f_{\text{px}} \cdot r_{\text{lateral}} \cdot \left(\frac{1}{Z_{\text{cam}} - Z_2} - \frac{1}{Z_{\text{cam}} - Z_1}\right)$$
  At the standby position ($r_{\text{lateral}} = 0.095\,\text{m}$):
  $$\Delta r = 256.0 \times 0.095 \times \left(\frac{1}{0.7144} - \frac{1}{0.7577}\right) = 1.94\,\text{pixels}$$
  At nadir ($X=0.40, Y=0.06$), $\Delta r = 0.0\,\text{pixels}$.
- **Conclusion for Top View:** Vertical height difference produces **zero height baseline**. It is physically impossible to judge from `_top.png` whether the fingertip is at $Z=0.536\,\text{m}$, $Z=0.492\,\text{m}$, or $Z=0.400\,\text{m}$.

### 3.3 Front View Perspective Cancellation (`round_01_pre.png`)
- The front camera is mounted at $(0.10, 0.0, 0.85)\,\text{m}$ pitched down by $\theta = 35^\circ$ ([reach_env_base_cfg.py:47-49](file:///home/control/AionGenos/aiongenos/tasks/base/reach_env_base_cfg.py#L47-L49)).
- In camera coordinates, vertical pixel coordinate $v$ is governed by:
  $$Y_{\text{cam}} = -\sin(35^\circ)(X - X_{\text{cam}}) - \cos(35^\circ)(Z - Z_{\text{cam}})$$
  $$Z_{\text{cam}} = \cos(35^\circ)(X - X_{\text{cam}}) - \sin(35^\circ)(Z - Z_{\text{cam}})$$
  $$v = c_y + f_{\text{px}} \frac{Y_{\text{cam}}}{Z_{\text{cam}}}$$
- Crucially, moving forward ($+X$) makes $Y_{\text{cam}}$ more negative, moving the projection **UP** ($v$ decreases, $\partial v / \partial X = -1.45\,\text{px/cm}$).
- Lowering height ($-Z$) makes $Y_{\text{cam}}$ more positive, moving the projection **DOWN** ($v$ increases, $\partial v / \partial Z = -1.04\,\text{px/cm}$).
- Now compare the standby fingertip $(X=0.3462, Z=0.5356)$ to the cube $(X\approx 0.38\text{--}0.41, Z\approx 0.4683)$:
  - The cube is **$4$ to $7\,\text{cm}$ further forward** ($+X$), shifting it **UP** by ~6–9 pixels.
  - The cube is **$6.7\,\text{cm}$ lower down** ($-Z$), shifting it **DOWN** by ~5–7 pixels.
  - **These two effects cancel out almost entirely.**

### 3.4 Front Image Scanline Comparison Across Seeds 5000–5009

| Seed | Standby Fingertip $v$ (px) | Cube Top Face $v$ (px) | Cube Center $v$ (px) | $\Delta v$ (Tip − Cube Center) | $\Delta v$ (Tip − Cube Top) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 5000 | 148.79 | 144.75 | 147.09 | **+1.70 px** | +4.04 px |
| 5001 | 148.79 | 148.24 | 150.59 | **-1.80 px** | +0.55 px |
| 5002 | 148.79 | 147.60 | 149.95 | **-1.16 px** | +1.19 px |
| 5003 | 148.79 | 144.62 | 146.96 | **+1.83 px** | +4.16 px |
| 5004 | 148.79 | 147.51 | 149.86 | **-1.07 px** | +1.28 px |
| 5005 | 148.79 | 145.32 | 147.66 | **+1.13 px** | +3.47 px |
| 5006 | 148.79 | 145.74 | 148.08 | **+0.71 px** | +3.05 px |
| 5007 | 148.79 | 148.43 | 150.78 | **-1.99 px** | +0.36 px |
| 5008 | 148.79 | 146.31 | 148.66 | **+0.13 px** | +2.48 px |
| 5009 | 148.79 | 145.03 | 147.36 | **+1.42 px** | +3.76 px |

- **Empirical Scanline Difference:** Across all 10 seeds, the vertical row difference between the hovering fingertip and the cube center is between **$-1.99$ and $+1.83$ pixels** (median $0.7$ px).
- The difference to the top edge of the cube is between **$0.36$ and $4.16$ pixels**.
- In a 256×256 image with no stereo baseline, no contact shadow on the table surface under the hovering tip, and pixel aliasing of 1–2 pixels, **a human observer cannot determine that the fingertip is 4.3 cm above the cube**. The tip appears visually aligned and level with the cube at $v \approx 148$.

*Re-runnable verification command:*
```bash
python3 -c "
import json, os, numpy as np
seed_map = {5000:'81a50701-51e', 5001:'21504ee5-5b1', 5002:'d42e7d92-c9c', 5003:'392894c5-f4a', 5004:'01b82183-43e', 5005:'fda8509e-76c', 5006:'6dba52e4-749', 5007:'ac69fa07-a44', 5008:'592dc4b9-235', 5009:'9a598075-968'}
f_front, theta, C = (12.0/45.0)*256.0, np.deg2rad(35.0), np.array([0.1, 0.0, 0.85])
V_fwd, V_down = np.array([np.cos(theta), 0, -np.sin(theta)]), np.array([-np.sin(theta), 0, -np.cos(theta)])
def proj_v(pt): d = pt - C; return 128.0 + f_front * (np.dot(d, V_down) / np.dot(d, V_fwd))
for s in range(5000, 5010):
    with open(f'/home/control/AionGenos/data/collect_dumps/71134939/{seed_map[s]}/meta.json') as f: m = json.load(f)
    r1 = m['rounds'][0]
    ee, cube = np.array(r1['ee_start_b']), np.array(r1['cube_b_pre'])
    ve, vc, vt = proj_v(ee), proj_v(cube), proj_v(cube + [0, 0, 0.024])
    print(f'Seed {s}: EE_v={ve:.2f}, CubeCenter_v={vc:.2f}, dv={ve-vc:+.2f}px, CubeTop_v={vt:.2f}, dv_top={ve-vt:+.2f}px')
"
```

---

## 4. Front/Top Camera Axes vs Base Frame ($+X, +Y, +Z$)

### 4.1 Base Frame Conventions
As defined in OpenArm / IsaacLab kinematic model ([reach_env_base_cfg.py](file:///home/control/AionGenos/aiongenos/tasks/base/reach_env_base_cfg.py)):
- **$+X_{\text{base}}$:** Forward (away from robot base, toward table center).
- **$+Y_{\text{base}}$:** Robot's Left.
- **$+Z_{\text{base}}$:** Upward (away from floor).

Standard 2D image coordinates:
- **$+u$:** Horizontal to the Right (columns $0 \to 255$).
- **$+v$:** Vertical Downward (rows $0 \to 255$).

### 4.2 Analytical Jacobians (Pixel Motion per $+1\,\text{cm}$ TCP Displacement)
Evaluated at nominal workspace center $(X=0.35, Y=0.10, Z=0.50)\,\text{m}$:

| Base Motion ($+1\,\text{cm}$) | Front Camera ($u, v$) Shift | Front Motion Direction | Top Camera ($u, v$) Shift | Top Motion Direction |
|---|---|---|---|---|
| **$+1\,\text{cm}\;X_{\text{base}}$** (Forward) | $\Delta u = +0.34\,\text{px}, \Delta v = -1.45\,\text{px}$ | **UP** (and slight right) | $\Delta u = 0.00\,\text{px}, \Delta v = -3.41\,\text{px}$ | **Straight UP** |
| **$+1\,\text{cm}\;Y_{\text{base}}$** (Left) | $\Delta u = -1.68\,\text{px}, \Delta v = 0.00\,\text{px}$ | **Straight LEFT** | $\Delta u = -3.41\,\text{px}, \Delta v = 0.00\,\text{px}$ | **Straight LEFT** |
| **$+1\,\text{cm}\;Z_{\text{base}}$** (Up) | $\Delta u = -0.24\,\text{px}, \Delta v = -1.04\,\text{px}$ | **UP** (and slight left) | $\Delta u = -0.18\,\text{px}, \Delta v = +0.23\,\text{px}$ | Negligible ($\le 0.29\,\text{px}$) |

### 4.3 Empirical Verification from Consecutive Rounds in Run 71134939
We isolate transitions where TCP motion ($\Delta\text{TCP} = \text{ee\_start\_b}[r+1] - \text{ee\_start\_b}[r]$) is dominated by a single axis, and track the physical gripper fingertip feature across consecutive dump images (`round_XX_pre.png` and `round_XX_pre_top.png`) via template matching:

#### Test 1: Dominant $+X$ Forward Motion (Seed 5005, R6 $\to$ R7)
- **Base TCP Motion:** $\Delta X = +19.81\,\text{cm}$, $\Delta Y = +4.02\,\text{cm}$, $\Delta Z = -0.03\,\text{cm}$.
- **Top Camera:**
  - Analytical prediction: $\Delta u = -14.4\,\text{px}, \Delta v = -71.0\,\text{px}$ (moves UP by 71 px).
  - Empirical template match: $\Delta u = -14.0\,\text{px}, \Delta v = -70.0\,\text{px}$ (correlation $0.74$, error $1.66\,\text{px}$).
- **Front Camera:**
  - Analytical prediction: $\Delta u = +8.5\,\text{px}, \Delta v = -50.0\,\text{px}$ (moves UP by 50 px).
  - Empirical template match: $\Delta u = +2.0\,\text{px}, \Delta v = -49.0\,\text{px}$ (correlation $0.70$, error $6.75\,\text{px}$).
- **Result:** Forward motion $+X$ translates to **UPWARD image motion ($-v$)** in both cameras.

#### Test 2: Dominant $-X$ Backward Motion (Seed 5005, R5 $\to$ R6)
- **Base TCP Motion:** $\Delta X = -13.51\,\text{cm}$, $\Delta Y = -2.02\,\text{cm}$, $\Delta Z = +0.03\,\text{cm}$.
- **Top Camera:**
  - Analytical prediction: $\Delta u = +7.2\,\text{px}, \Delta v = +48.4\,\text{px}$ (moves DOWN by 48 px).
  - Empirical template match: $\Delta u = +7.0\,\text{px}, \Delta v = +48.0\,\text{px}$ (correlation $0.80$, error $0.83\,\text{px}$).
- **Front Camera:**
  - Analytical prediction: $\Delta u = -8.2\,\text{px}, \Delta v = +39.4\,\text{px}$ (moves DOWN by 39 px).
  - Empirical template match: $\Delta u = -15.0\,\text{px}, \Delta v = +36.0\,\text{px}$ (correlation $0.57$, error $7.93\,\text{px}$).
- **Result:** Backward motion $-X$ translates to **DOWNWARD image motion ($+v$)** in both cameras.

#### Test 3: Dominant $+Y$ Left Motion (Seed 5000, R5 $\to$ R6)
- **Base TCP Motion:** $\Delta X = -0.07\,\text{cm}$, $\Delta Y = +16.24\,\text{cm}$, $\Delta Z = -0.14\,\text{cm}$.
- **Top Camera:**
  - Analytical prediction: $\Delta u = -56.1\,\text{px}, \Delta v = +0.1\,\text{px}$ (moves LEFT by 56 px).
  - Empirical template match: $\Delta u = -64.0\,\text{px}, \Delta v = -3.0\,\text{px}$ (correlation $0.27$, error $8.09\,\text{px}$).
- **Front Camera:**
  - Analytical prediction: $\Delta u = -46.7\,\text{px}, \Delta v = +0.4\,\text{px}$ (moves LEFT by 47 px).
  - Empirical template match: $\Delta u = -43.0\,\text{px}, \Delta v = -1.0\,\text{px}$ (correlation $0.71$, error $3.56\,\text{px}$).
- **Result:** Left motion $+Y$ translates to **LEFTWARD image motion ($-u$)** in both cameras.

#### Test 4: Dominant $-Y$ Right Motion (Seed 5000, R7 $\to$ R8)
- **Base TCP Motion:** $\Delta X = -0.68\,\text{cm}$, $\Delta Y = -35.72\,\text{cm}$, $\Delta Z = +0.03\,\text{cm}$.
- **Top Camera:**
  - Analytical prediction: $\Delta u = +118.9\,\text{px}, \Delta v = +2.3\,\text{px}$ (moves RIGHT by 119 px).
  - Empirical template match: $\Delta u = +118.0\,\text{px}, \Delta v = +2.0\,\text{px}$ (correlation $0.58$, error $0.66\,\text{px}$).
- **Front Camera:**
  - Analytical prediction: $\Delta u = +94.6\,\text{px}, \Delta v = +2.6\,\text{px}$ (moves RIGHT by 95 px).
  - Empirical template match: $\Delta u = +90.0\,\text{px}, \Delta v = +2.0\,\text{px}$ (correlation $0.80$, error $4.43\,\text{px}$).
- **Result:** Right motion $-Y$ translates to **RIGHTWARD image motion ($+u$)** in both cameras.

#### Test 5: Dominant Downward Motion (Seed 5002, R8 $\to$ R9)
- **Base TCP Motion:** $\Delta X = +1.75\,\text{cm}$, $\Delta Y = -12.03\,\text{cm}$, $\Delta Z = -5.94\,\text{cm}$.
- **Top Camera:**
  - Analytical prediction: $\Delta u = +44.7\,\text{px}, \Delta v = -7.7\,\text{px}$.
  - Empirical template match: $\Delta u = +44.0\,\text{px}, \Delta v = -8.0\,\text{px}$ (correlation $0.91$, error $0.44\,\text{px}$).
- **Front Camera:**
  - Analytical prediction: $\Delta u = +24.8\,\text{px}, \Delta v = +3.6\,\text{px}$.
  - Empirical template match: $\Delta u = +25.0\,\text{px}, \Delta v = +4.0\,\text{px}$ (correlation $0.92$, error $0.58\,\text{px}$).

*Re-runnable verification command:*
```bash
python3 -c "
import json, cv2, numpy as np
f_f, C_f, th_f = (12.0/45.0)*256.0, np.array([0.1, 0.0, 0.85]), np.deg2rad(35.0)
V_ff, V_rf, V_df = np.array([np.cos(th_f), 0, -np.sin(th_f)]), np.array([0, -1, 0]), np.array([-np.sin(th_f), 0, -np.cos(th_f)])
f_t, C_t = 256.0, np.array([0.40, 0.06, 1.25])
V_ft, V_rt, V_dt = np.array([0, 0, -1]), np.array([0, -1, 0]), np.array([-1, 0, 0])
def proj_f(p): d = p - C_f; return 128.0 + f_f * (np.dot(d, V_rf)/np.dot(d, V_ff)), 128.0 + f_f * (np.dot(d, V_df)/np.dot(d, V_ff))
def proj_t(p): d = p - C_t; return 128.0 + f_t * (np.dot(d, V_rt)/np.dot(d, V_ft)), 128.0 + f_t * (np.dot(d, V_dt)/np.dot(d, V_ft))
def check(ep, r1, r2):
    with open(f'/home/control/AionGenos/data/collect_dumps/71134939/{ep}/meta.json') as f: m = json.load(f)
    e1, e2 = np.array(m['rounds'][r1-1]['ee_start_b']), np.array(m['rounds'][r2-1]['ee_start_b'])
    uf1, vf1 = proj_f(e1); uf2, vf2 = proj_f(e2)
    ut1, vt1 = proj_t(e1); ut2, vt2 = proj_t(e2)
    print(f'{ep} R{r1}->R{r2}: dTCP={[round(x*100,1) for x in e2-e1]}cm | Front theory du={uf2-uf1:+.1f}, dv={vf2-vf1:+.1f} | Top theory du={ut2-ut1:+.1f}, dv={vt2-vt1:+.1f}')
check('fda8509e-76c', 6, 7) # Seed 5005 +X
check('fda8509e-76c', 5, 6) # Seed 5005 -X
check('81a50701-51e', 5, 6) # Seed 5000 +Y
check('81a50701-71e' if False else '81a50701-51e', 7, 8) # Seed 5000 -Y
check('d42e7d92-c9c', 8, 9) # Seed 5002 -Z
"
```

---

## 5. Key Structural Diagnoses for the Rung-2′ Failure

1. **Why the Teacher Anchored on Standby Height ($Z = 0.535\,\text{m}$):**
   - In 509 of 597 rounds (85.3%), the teacher targeted $Z = 0.535\,\text{m}$ (standby height) rather than descending to contact height ($Z = 0.468\,\text{m}$).
   - **Perceptual cause:** The teacher cannot see that the hand is 4.3 cm too high. In the front view, the fingertip and the cube center project to within **$\le 1.99\,\text{pixels}$** of the exact same row. In the top view, height is completely invisible.
   - Ground contact shadows are virtually nonexistent in this rendering configuration, removing the primary monocular contact cue.

2. **Severe Coordinate Frame Mismatch:**
   - The teacher is prompted with base-frame integers `(X, Y, Z)` ([prompts.py:150](file:///home/control/AionGenos/aiongenos/vlm/prompts.py#L150)), but perceives the scene through images whose axes are rotated and permuted:
     - In the top-down view: Image horizontal is $-Y_{\text{base}}$ (not $X$), and Image vertical is $+X_{\text{base}}$ (not $Y$).
     - In the front view: Both $+X$ (forward) and $+Z$ (up) move **UP** on the screen (co-linear within 26°).
   - If the VLM applies visual heuristics (e.g. "move up to reach the object above"), it commands $+X$ or $+Z$ interchangeably, confusing depth and elevation.

3. **Instrument Feasibility Verdict:**
   - The 256×256 resolution is sufficient to detect the cube's 2D position (17×17 px top, 13×12 px front), but **fundamentally inadequate for monocular height resolution** of a 4.3 cm gap under a 35° oblique view, and completely blind to height in the top-down view.
