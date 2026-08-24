"""Step 1 — new table USD health check (Table_sor_1.usd).

Props often ship WITHOUT a collision mesh; push physics IS friction, so we
must confirm: (a) a collider exists on some prim, (b) physics material /
friction coefficients (or note their absence), (c) the table-top world z at
the layout the PI specified. Headless; reads only.

Layout (PI-defined): table at (0.55,0,0); expected table-top z≈1.0197 world.
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--usd", type=str, default="/home/control/AionGenos/localProps/Table_sor_1.usd")
parser.add_argument("--table-pos", type=float, nargs=3, default=[0.55, 0.0, 0.0])
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import isaaclab.sim as sim_utils
from isaaclab.sim import SimulationContext
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade


def _p(m): print(f"[TCHK] {m}", flush=True)


def main():
    sim = SimulationContext(sim_utils.SimulationCfg(dt=1 / 60))
    # ground + light so the stage is valid
    sim_utils.GroundPlaneCfg().func("/World/ground", sim_utils.GroundPlaneCfg())
    cfg = sim_utils.UsdFileCfg(usd_path=args_cli.usd)
    cfg.func("/World/Table", cfg, translation=tuple(args_cli.table_pos))
    sim.reset()
    for _ in range(5):
        sim.step()

    stage = sim.stage
    root = stage.GetPrimAtPath("/World/Table")
    _p(f"loaded {args_cli.usd} at {args_cli.table_pos}")
    _p(f"root prim valid={root.IsValid()} type={root.GetTypeName() if root.IsValid() else '-'}")

    # walk the subtree; collect colliders, physics materials, geom bbox
    n_prims = 0; colliders = []; phys_mats = []; geoms = []
    frictions = []
    for prim in Usd.PrimRange(root):
        n_prims += 1
        path = prim.GetPath().pathString
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            colliders.append(path)
        if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Gprim):
            geoms.append(path)
        if prim.IsA(UsdPhysics.MaterialAPI) or prim.HasAPI(UsdPhysics.MaterialAPI):
            phys_mats.append(path)
        # physics material friction attrs
        mat = UsdPhysics.MaterialAPI(prim) if prim.HasAPI(UsdPhysics.MaterialAPI) else None
        if mat:
            sf = mat.GetStaticFrictionAttr().Get() if mat.GetStaticFrictionAttr() else None
            df = mat.GetDynamicFrictionAttr().Get() if mat.GetDynamicFrictionAttr() else None
            frictions.append((path, sf, df))

    _p(f"subtree prims={n_prims} geoms={len(geoms)} colliders={len(colliders)} phys_materials={len(phys_mats)}")
    _p(f"COLLIDER present: {'YES' if colliders else 'NO — props often lack one; push needs a collider!'}")
    for c in colliders[:5]:
        _p(f"  collider: {c}")
    if frictions:
        for p, sf, df in frictions:
            _p(f"  friction @ {p}: static={sf} dynamic={df}")
    else:
        _p("  NO physics-material friction attrs found → will inherit sim default "
           "(must PIN the effective friction in provenance Pin-10)")

    # table-top world z via bbox
    c = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"], useExtentsHint=True)
    try:
        rng = c.ComputeWorldBound(root).ComputeAlignedRange()
        _p(f"TABLE world bbox z=[{rng.GetMin()[2]:.4f}, {rng.GetMax()[2]:.4f}] "
           f"→ TOP z ≈ {rng.GetMax()[2]:.4f} (PI expected ≈1.0197)")
        _p(f"  bbox x=[{rng.GetMin()[0]:.3f},{rng.GetMax()[0]:.3f}] "
           f"y=[{rng.GetMin()[1]:.3f},{rng.GetMax()[1]:.3f}]")
    except Exception as e:
        _p(f"bbox failed: {e}")
    _p("=== DONE ===")
    simulation_app.close()


if __name__ == "__main__":
    main()
