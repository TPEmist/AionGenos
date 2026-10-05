"""Pure-kinematics reachability of the TABLE PLANE for BOTH arms (PI's math
question: intersection of table-top with each arm's working envelope).

Instrument rule: drive the VALIDATED L2 DiffIK servo via IsaacLabEnvInterface
(same path the reach-envelope saga settled on), NOT hand-rolled IK. Base-frame
kinematics is invariant to the base's WORLD height, so the L2 env's DiffIK
envelope at a given base-frame (x,y,z) is identical to the push env's — we just
sweep at the push table height z_B and over the push goal/cube (x,y) region.

Table contact height (base frame) = _CUBE_REST_Z_B ≈ 0.468 (from push_s3a_cfg).
Sweep x ∈ [0.28..0.60], y ∈ [-0.30..0.30] at that z, for LEFT and RIGHT.
A cell is REACHABLE if the arm servos to within REACH_TOL_CM (hold-orient,
pure position — same convention as wp3a_reach_envelope).
Report per-arm reachable region + the union/overlap, so cube+goal sampling can
be gated to reachable-by-SOME-arm cells (embodied: agent picks the hand)."""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=120)
parser.add_argument("--tol", type=float, default=4.0)   # cm servo bar
parser.add_argument("--arms", default="left,right")
parser.add_argument("--xs", default="0.28,0.34,0.40,0.46,0.52,0.58")
parser.add_argument("--ys", default="-0.30,-0.20,-0.10,0.0,0.10,0.20,0.30")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli); simulation_app = app_launcher.app

import numpy as np, torch
from isaaclab.utils.math import subtract_frame_transforms
from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.pipeline.stage2_attempt import BimanualCommand, MetricCommand

Z_TABLE_B = 0.468          # base-frame table contact height (push_s3a _CUBE_REST_Z_B)
XS = [float(v) for v in args_cli.xs.split(",")]
YS = [float(v) for v in args_cli.ys.split(",")]
TOL = args_cli.tol

def _p(m): print(f"[RTB] {m}", flush=True)

def main():
    env = ArenaEnvBuilder.build_env(level=2, num_envs=1)
    iface = IsaacLabEnvInterface(env)
    robot = iface.robot; u = env.unwrapped

    def ee_b(idx):
        root_p = robot.data.root_pos_w[0:1,:3]; root_q = robot.data.root_quat_w[0:1,:4]
        ee_w = robot.data.body_pos_w[0:1, idx, :3]
        pb,_ = subtract_frame_transforms(root_p, root_q, ee_w)
        return pb[0].cpu().numpy()

    def servo(arm, x, y, z):
        iface.reset(seed=4700)
        lb, rb, lqw, rqw = iface._get_ee_poses()
        if arm=="left":
            lq=(float(lqw[0]),float(lqw[1]),float(lqw[2]),float(lqw[3]))
            left=MetricCommand(position=(x,y,z),quaternion=lq)
            right=MetricCommand(position=tuple(float(v) for v in rb),
                                quaternion=(float(rqw[0]),float(rqw[1]),float(rqw[2]),float(rqw[3])))
            idx=iface.left_body_idx
        else:
            rq=(float(rqw[0]),float(rqw[1]),float(rqw[2]),float(rqw[3]))
            right=MetricCommand(position=(x,y,z),quaternion=rq)
            left=MetricCommand(position=tuple(float(v) for v in lb),
                               quaternion=(float(lqw[0]),float(lqw[1]),float(lqw[2]),float(lqw[3])))
            idx=iface.right_body_idx
        cmd=BimanualCommand(left=left,right=right)
        tgt=np.array([x,y,z]); dmin=1e9
        for _ in range(args_cli.steps//10):
            iface.execute_command(cmd, steps=10, active_arm=arm)
            d=float(np.linalg.norm(ee_b(idx)-tgt))*100
            dmin=min(dmin,d)
        return dmin

    for arm in args_cli.arms.split(","):
        _p(f"===== {arm.upper()} arm — table plane z_B={Z_TABLE_B} =====")
        header="      " + "".join(f"x={x:.2f} " for x in XS)
        _p(header)
        grid={}
        for y in YS:
            row=f"y={y:+.2f}"
            for x in XS:
                d=servo(arm,x,y,Z_TABLE_B)
                grid[(x,y)]=d
                row += f"  {('OK ' if d<=TOL else '-- ')}{d:4.1f}"
            _p(row)
    _p("legend: OK = reachable (servo ≤%.1fcm), -- = not; number is min servo err cm" % TOL)
    _p("DONE")
    env.close()

if __name__=="__main__":
    main(); simulation_app.close()
