"""WP1-③a reachability sweep — the SURFACE, not a point (PI spec 2026-08-17).

Over the Pin-4 region (x 0.40-0.60, y ±0.15), a 5×5 grid. For each cell,
drive the LEFT EE down toward a series of world-frame targets (via the
frame gate — base_frame_target_from_world, Rule 5) and measure two z's:
  - z_momentary : lowest EE z that comes within tol of the commanded z
  - z_hold      : lowest commanded z the EE can HOLD within tol for >=30
                  steps (push needs a sustained contact height).
Outputs two heatmaps (text) + each one's max (worst cell). Verdict line:
z_hold <= 0.03 over >= 90% of cells = PASS.

Rule 6 sanity: this drives a per-limb NON-ZERO target and checks real
motion; not a zero-action green. Frame gate: all targets built via the
sanctioned util. Optional --dump-cell writes per-step frames of one cell's
descent for the human-eye GIF gate.

Flushed; caller reads [SWEEP] lines + the final grids.
"""
from __future__ import annotations

import argparse
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--grid", type=int, default=5)
parser.add_argument("--tol-cm", type=float, default=5.0)
parser.add_argument("--hold-steps", type=int, default=30)
parser.add_argument("--settle-steps", type=int, default=60)   # per-z servo before reading
parser.add_argument("--z-hi", type=float, default=0.30)
parser.add_argument("--z-lo", type=float, default=0.02)
parser.add_argument("--z-step", type=float, default=0.02)
parser.add_argument("--dump-cell", type=str, default="")      # "r,c" to frame-dump that cell
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import os
import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import base_frame_target_from_world


def _p(m):
    print(f"[SWEEP] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    act_dim = env.action_space.shape[-1]
    _p(f"env made; grid={args_cli.grid}x{args_cli.grid} tol={args_cli.tol_cm}cm")

    xs = [0.40 + (0.60 - 0.40) * i / (args_cli.grid - 1) for i in range(args_cli.grid)]
    ys = [-0.15 + (0.15 - (-0.15)) * j / (args_cli.grid - 1) for j in range(args_cli.grid)]
    zs = []
    z = args_cli.z_hi
    while z >= args_cli.z_lo - 1e-9:
        zs.append(round(z, 3)); z -= args_cli.z_step

    dump_rc = None
    if args_cli.dump_cell:
        dump_rc = tuple(int(v) for v in args_cli.dump_cell.split(","))
        os.makedirs("data/collect_dumps/sweep_descent", exist_ok=True)

    z_mom = [[None] * args_cli.grid for _ in range(args_cli.grid)]
    z_hold = [[None] * args_cli.grid for _ in range(args_cli.grid)]
    tol = args_cli.tol_cm / 100.0

    def drive_to(x, y, z, steps, dump_tag=None):
        """Servo the left EE toward world (x,y,z); return list of EE z each step."""
        tgt_w = torch.tensor([x, y, z], device=u.device)
        tgt_b = base_frame_target_from_world(u, tgt_w)
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 0:3] = tgt_b
        action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)
        half = act_dim // 2
        if half > 7:
            action[:, 7:half] = 300.0
        ee_zs = []
        for s in range(steps):
            env.step(action)
            eez = float(robot.data.body_pos_w[0, ee_idx, 2].item())
            ee_zs.append(eez)
            if dump_tag is not None:
                rgb = u.scene["camera"].data.output["rgb"]
                if rgb is not None:
                    from PIL import Image
                    img = (rgb[0].detach().cpu().numpy()).astype("uint8")
                    Image.fromarray(img[..., :3]).save(
                        f"data/collect_dumps/sweep_descent/{dump_tag}_{s:03d}.png")
        return ee_zs

    for r, x in enumerate(xs):
        for c, y in enumerate(ys):
            env.reset(seed=4700 + r * args_cli.grid + c)
            mom = None
            hold = None
            for z in zs:
                dtag = f"cell{r}_{c}_z{int(z*1000)}" if dump_rc == (r, c) else None
                ee_zs = drive_to(x, y, z, args_cli.settle_steps, dtag)
                # momentary: did EE z ever come within tol of commanded z?
                within = [abs(ez - z) <= tol for ez in ee_zs]
                if any(within):
                    mom = z
                # hold: did EE stay within tol for the last hold_steps?
                tail = ee_zs[-args_cli.hold_steps:]
                if len(tail) >= args_cli.hold_steps and all(abs(ez - z) <= tol for ez in tail):
                    hold = z
            z_mom[r][c] = mom
            z_hold[r][c] = hold
            _p(f"cell(r{r},c{c}) x={x:.2f} y={y:+.2f}: z_mom={mom} z_hold={hold}")

    # grids + verdict
    def fmt(grid):
        return "\n".join("  " + " ".join(f"{(v if v is not None else 9.99):.2f}" for v in row) for row in grid)
    _p("z_momentary grid (rows=x, cols=y; 9.99=never reached):")
    print(fmt(z_mom), flush=True)
    _p("z_hold grid:")
    print(fmt(z_hold), flush=True)

    flat_hold = [v for row in z_hold for v in row]
    reached = [v for v in flat_hold if v is not None]
    ok_cells = [v for v in reached if v <= 0.03]
    n = args_cli.grid * args_cli.grid
    worst_mom = max((v for row in z_mom for v in row if v is not None), default=None)
    worst_hold = max((v for row in z_hold for v in row if v is not None), default=None)
    _p(f"worst-cell z_momentary={worst_mom}  z_hold={worst_hold}")
    _p(f"cells with z_hold<=0.03: {len(ok_cells)}/{n} ({100*len(ok_cells)/n:.0f}%)")
    _p(f"VERDICT {'PASS' if len(ok_cells) >= 0.9 * n else 'FAIL'} "
       f"(>=90% cells hold at z<=0.03: {len(ok_cells) >= 0.9 * n})")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
