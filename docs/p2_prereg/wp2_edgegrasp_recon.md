# WP1-② Edge-Grasp recon (2026-08-11) — parallel, no ③ dependency

Delegated recon; **isaac to program-verify the two decision-critical claims
before any WP1-② work starts** (see ⚠ below). Not yet actioned — this is
scouting for a future go/no-go.

## Findings (agent)
1. **Install — cost MEDIUM.** `HaojHuang/Edge-Grasp-Network` (ICRA2023).
   Pretrained weights ship with the repo; inference needs no dataset/train.
   Deps: PyTorch + **torch-geometric (PyG)** + open3d + pybullet(2.7.9) +
   opencv/scipy. NO MinkowskiEngine (PointNet++ + Vector Neurons) — kills
   the biggest prior install risk. Author targets Python 3.7; IsaacLab is
   3.11 → recommend NOT cloning whole repo, extract model + `orthognal_grasps`
   + weights only, reinstall PyG matched to IsaacLab's torch ABI (drop
   pybullet/open3d harness → smaller dep surface). Real risk = PyG's
   CUDA/torch ABI pin.
2. **Output format — cost LOW.** `model.act(data)` → score/approaches/
   sample_pos/normals; `orthognal_grasps(...)` → (N,4,4) SE(3); split to
   quat+translation. 3 steps to our interface (topk by score → pos → quat).
   ⚠ **quat convention trap**: Edge-Grasp uses scipy `(x,y,z,w)`, our action
   interface uses `(w,x,y,z)` — must reorder or poses silently rotate wrong.
3. **camera→base transform — cost MEDIUM (the one real work item, confirmed).**
   Left-multiply `T_base←cam`. Runtime query `camera.data.pos_w/quat_w_world`
   + `robot.data.root_pos_w/root_quat_w`. ⚠ camera convention (world/ros/
   opengl) must match between extrinsic + pointcloud gen or all grasps skew.
4. **MIT license — cost LOW, clear.** MIT (c) 2023 Haojie Huang; commercial
   + fine-tune OK; weights in-repo, no separate terms → MIT-covered. Paper 2
   end-to-end reproducibility claim OK.

## ⚠ Two claims isaac must program-verify before WP1-② go (not done yet)
- **Camera has RGB only, no depth/pointcloud.** `reach_env_base_cfg.py`
  CameraCfg `data_types=["rgb"]` — Edge-Grasp needs depth/pointcloud. Adding
  `distance_to_image_plane`/`pointcloud` data_type + confirming Isaac Sim
  5.1 outputs it is a HIDDEN work item, not previously named. Verify before
  committing to Edge-Grasp.
- **PyG × IsaacLab-torch ABI** is the gate-smoke life/death point — verify a
  matched-wheel import + a forward pass with the pretrained weights before
  any integration.

## Gate-smoke plan (when WP1-② is greenlit)
env-compat (PyG import + weights load + forward) → output bridge (quat
reorder + topk, unit-tested) → offline frame-transform check (grasp lands on
a known cube pose, <2cm) → synthetic pointcloud → grasp → action → nonzero
grasp success.

**Status: recon filed, NOT started. Zero dependency on WP1-③. Revisit after
③a is running.**
