# WP1-① OSC bisection — s2: s1 + CAMERA. s0 (single arm) and s1 (dual arm,
# two OSC terms) both PASSED, so assets/OSC/bimanual are fine. s2 adds the
# RGB camera (the AionGenos base's for-VLM camera, verbatim) to isolate the
# camera×OSC-reset interaction — the prime remaining suspect, since our full
# test-bed differs from the (green) s1 exactly by having a camera base.
#
# Requires --enable_cameras at launch (a camera cfg without it raises at
# reset — a loud error, not a hang).

import isaaclab.sim as sim_utils
from isaaclab.sensors import CameraCfg
from isaaclab.utils import configclass

from aiongenos.tasks.WP1_contact_testbed.osc_bisect_s1_cfg import OscBisectS1EnvCfg


@configclass
class OscBisectS2EnvCfg(OscBisectS1EnvCfg):
    """s1 (dual-arm OSC) + the AionGenos base RGB camera, verbatim."""

    def __post_init__(self):
        super().__post_init__()

        # Same camera the AionGenos reach base adds (reach_env_base_cfg.py:33)
        # — identical settings so s2 isolates exactly "camera present or not".
        self.scene.camera = CameraCfg(
            prim_path="{ENV_REGEX_NS}/Robot/Camera",
            update_period=0.0,
            height=256,
            width=256,
            data_types=["rgb"],
            spawn=sim_utils.PinholeCameraCfg(
                focal_length=12.0,
                focus_distance=400.0,
                horizontal_aperture=45.0,
                clipping_range=(0.1, 1.0e5),
            ),
            offset=CameraCfg.OffsetCfg(
                pos=(0.1, 0.0, 0.85),
                rot=(0.95372, 0.0, 0.30071, 0.0),
                convention="world",
            ),
        )
        self.sim.render_interval = self.decimation
