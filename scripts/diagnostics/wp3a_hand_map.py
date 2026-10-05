"""Measure EXACTLY: (1) the standby LEFT hand + both fingers + tcp resting
(x,y) on the table plane (so we know the keep-out zone), (2) the cube's natural
settle when placed at a grid of (x,y) with NO goal/arm interaction, to map where
it stays put. Removes all guessing about hand position."""
import argparse
from isaaclab.app import AppLauncher
p=argparse.ArgumentParser(); AppLauncher.add_app_launcher_args(p)
a=p.parse_args(); a.enable_cameras=True
app=AppLauncher(a); sim_app=app.app
import numpy as np, torch
from isaaclab.utils.math import subtract_frame_transforms, combine_frame_transforms
import gymnasium as gym, aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
GID="Isaac-AionGenos-WP1-Push-v0"
env=gym.make(GID,cfg=parse_env_cfg(GID,num_envs=1),render_mode=None)
iface=IsaacLabEnvInterface(env); robot=iface.robot; u=env.unwrapped
obj=u.scene["object"]
def body_b(name):
    idx=robot.data.body_names.index(name)
    rp=robot.data.root_pos_w[0:1,:3]; rq=robot.data.root_quat_w[0:1,:4]
    bw=robot.data.body_pos_w[0:1, idx,:3]
    pb,_=subtract_frame_transforms(rp,rq,bw); return pb[0].cpu().numpy()
env.reset(seed=4700)
for _ in range(30): env.step(torch.zeros((1,env.action_space.shape[-1]),device=u.device))
print("[HM] standby LEFT-arm body positions (base frame x,y,z):",flush=True)
lbodies=[n for n in robot.data.body_names if 'left' in n.lower() and ('hand' in n.lower() or 'finger' in n.lower() or 'tcp' in n.lower())]
hand_xy=[]
for n in lbodies:
    b=body_b(n); hand_xy.append(b[:2])
    print(f"[HM]   {n:28s} = ({b[0]:.3f},{b[1]:.3f},{b[2]:.3f})",flush=True)
hand_xy=np.array(hand_xy)
print(f"[HM] left-hand cluster xy bbox: x[{hand_xy[:,0].min():.3f},{hand_xy[:,0].max():.3f}] y[{hand_xy[:,1].min():.3f},{hand_xy[:,1].max():.3f}]",flush=True)

# cube settle map: place at grid, settle 40 steps NO arm cmd, record stay/drift
print("[HM] cube settle map (place → settle, drift<2cm = STAYS):",flush=True)
rp=robot.data.root_pos_w[0:1,:3]; rq=robot.data.root_quat_w[0:1,:4]
for x in [0.30,0.34,0.38,0.42]:
    row=f"[HM]  x={x:.2f}: "
    for y in [0.02,0.06,0.10,0.14,0.18]:
        env.reset(seed=4700)
        pw,_=combine_frame_transforms(rp,rq,torch.tensor([[x,y,0.468]],device=u.device))
        obj.write_root_pose_to_sim(torch.cat([pw,obj.data.root_quat_w],dim=-1))
        obj.write_root_velocity_to_sim(torch.zeros_like(obj.data.root_vel_w))
        c0=np.array(iface.get_cube_pose_b())
        for _ in range(40): env.step(torch.zeros((1,env.action_space.shape[-1]),device=u.device))
        c1=np.array(iface.get_cube_pose_b())
        drift=np.linalg.norm(c1[:2]-c0[:2])*100
        row += f"y{y:.2f}:{'STAY' if drift<2 else f'{drift:3.0f}cm'} "
    print(row,flush=True)
print("[HM] DONE",flush=True)
env.close(); sim_app.close()
