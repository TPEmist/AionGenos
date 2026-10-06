"""push_memory + push_collect wiring: observables-only model inputs (PI ruling
2026-10-05), rung-gated recap/preamble, retrieval through the shared buffer,
recap-record construction, replay augmentation, (c, s) extraction, and the
loop (Option A, TCP targets + rest orientation, budget guard, auto-reset,
GIF strip) — no sim, no teacher (fakes)."""

import importlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

from aiongenos.config import ControlMode, LevelConfig, WorkspaceBounds
from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord
from aiongenos.orchestrator import push_memory as pm
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome, VLMInteraction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))
import push_r_inputs  # noqa: E402

DIM = 8
SUCCESS_CM, MIN_DISP_CM = 5.0, 1.0
BOUNDS = WorkspaceBounds()
TCP_INT = (22, 50, -14)
# GT strings that must never reach a rung-1 model input
GT_MARKERS = ("CUBE_POS", "GOAL_POS", "cube→goal", "CUBE_TO_GOAL", "TCP→cube", "cube moved",
              "cube start", "(disclosed)", "near_miss", "wrong_direction", "push_plateau")


def _png(color=(10, 20, 30), size=(8, 8)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _snap(cube=(0.40, 0.10, 0.02), goal=(0.48, 0.12, 0.02), tcp=(0.25, 0.20, 0.30)):
    cg, gg = pm.grid_xyz(cube, BOUNDS), pm.grid_xyz(goal, BOUNDS)
    return pm.PushStateSnapshot(tcp_b=tcp, tcp_int=TCP_INT, cube_b=cube, goal_b=goal,
                                cube_int=(cg[0], cg[1]), goal_int=(gg[0], gg[1]))


def _round(i, target_int=(45, 8, 48), target_m=(0.3525, 0.032, 0.518), disp=0.02, dist=0.07):
    return {"round": i, "eef_target_int": list(target_int), "eef_target_m": list(target_m),
            "ori_offset_deg": None, "ori_applied": False, "cube_disp_m": disp,
            "cube_goal_dist_m": dist, "tcp_final_b": [0.34, 0.04, 0.50],
            "contact": {"tcp_to_cube_min_cm": 1.5, "first_cube_move": {"anatomy": "finger"}}}


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def _rec(ep_id, success, emb, img_path=None, run_id="r0", rung=1, disclosed=None, task=pm.PUSH_TASK_TAG):
    return RecapRecord(
        ep_id=ep_id, run_id=run_id, outcome="success" if success else "push_plateau",
        is_success=success, image_anchors={"init_pre": str(img_path)} if img_path else {},
        state_anchor={"init_L_EE": list(TCP_INT), "r1_eef_target_int": [45, 8, 48],
                      "r1_tcp_reached_int": [41, 10, 43], "r1_ori_offset_deg": None,
                      "round_count": 4, "outcome_class": "success" if success else "failure",
                      "obs_rung": rung, "disclosed": disclosed or {}},
        text_lesson=f"lesson {ep_id}", image_embedding=[float(x) for x in emb],
        metadata={"task": task, "obs_rung": rung})


# ── retrieval: shared RecapBuffer.retrieve, observables-only key ──

def test_retriever_uses_shared_buffer_image_ranks(tmp_path):
    buf = RecapBuffer(root=tmp_path / "recaps")
    img = tmp_path / "init.png"
    img.write_bytes(_png())
    q = _unit(np.arange(1, DIM + 1))
    buf.add(_rec("close", True, q, img))
    buf.add(_rec("far", True, -q, img))
    buf.add(_rec("noimg", True, q, None))                 # dropped: no init_pre image
    r = pm.PushMemoryRetriever(buf, top_k=3, embed_fn=lambda _b: q)
    pre = r.retrieve_for_episode(_png(), TCP_INT)
    ids = [x.ep_id for x in pre.retrieved_records]
    assert ids == ["close", "far"]
    # same init TCP → state_sim = 1 for both: score gap is the image term alone
    assert pre.similarities[0] - pre.similarities[1] == pytest.approx(0.4 * 2.0, abs=1e-5)
    assert len(pre.past_image_base64_list) == 2


def test_retriever_drops_foreign_and_empty(tmp_path):
    buf = RecapBuffer(root=tmp_path / "recaps")
    img = tmp_path / "i.png"
    img.write_bytes(_png())
    e = _unit(np.ones(DIM))
    buf.add(_rec("reach", True, e, img, task="L0a_left"))
    pre = pm.PushMemoryRetriever(buf, embed_fn=lambda _b: e).retrieve_for_episode(_png(), TCP_INT)
    assert pre.is_empty
    empty = pm.PushMemoryRetriever(RecapBuffer(root=tmp_path / "e"), embed_fn=lambda _b: e)
    assert empty.retrieve_for_episode(_png(), TCP_INT).is_empty


def test_assert_push_only_buffer_rejects_reach_and_other_rung(tmp_path):
    e = _unit(np.ones(DIM))
    b1 = RecapBuffer(root=tmp_path / "a")
    b1.add(_rec("reach", True, e, task="L0a_left"))
    with pytest.raises(ValueError, match="non-push"):
        pm.assert_push_only_buffer(b1, 1)
    b2 = RecapBuffer(root=tmp_path / "b")
    b2.add(_rec("r3", True, e, rung=3))
    with pytest.raises(ValueError, match="obs_rung"):
        pm.assert_push_only_buffer(b2, 1)
    pm.assert_push_only_buffer(b2, 3)


def test_preamble_rung_gating():
    disc = {"init_cube_int": [55, 25], "goal_int": [73, 30], "init_cube_goal_dist_cm": 8.2,
            "round_cube_goal_dist_cm": [7.0, 6.0]}
    recs = [_rec("x", False, np.ones(DIM), rung=3, disclosed=disc)]
    t1 = pm.format_push_preamble_text(recs, [0.9], obs_rung=1)
    assert "start TCP  = (X=22, Y=50, Z=-14)" in t1 and "outcome    = failure" in t1
    assert "lesson     : lesson x" in t1 and "choose your target" in t1
    assert not any(m in t1 for m in GT_MARKERS), t1
    t2 = pm.format_push_preamble_text(recs, [0.9], obs_rung=2)
    assert "cube→goal  = 8.2 cm at start, 6.0 cm at end" in t2 and "CUBE" not in t2
    assert "cube start = (X=55, Y=25)" not in t2
    t3 = pm.format_push_preamble_text(recs, [0.9], obs_rung=3)
    assert "cube start = (X=55, Y=25)   goal = (X=73, Y=30)" in t3


# ── outcome class (offline) + key round ──

@pytest.mark.parametrize("outcome,init,dists,disps,want", [
    ("success", 8.0, [3.0], [5.0], "success"),
    ("push_plateau", 8.0, [8.0, 8.0, 8.0], [0.1, 0.2, 0.0], "cube_not_moved"),
    ("timeout", 8.0, [6.0, 7.2, 9.0], [2.0, 1.5, 2.0], "near_miss"),
    ("push_plateau", 8.0, [10.0, 11.8], [2.0, 2.0], "wrong_direction"),
    ("timeout", 8.0, [8.2, 8.4], [1.5, 1.5], "timeout"),
])
def test_classify_push_outcome(outcome, init, dists, disps, want):
    assert pm.classify_push_outcome(outcome, init, dists, disps, SUCCESS_CM, MIN_DISP_CM) == want


def test_key_round_selection_rung_gated():
    assert pm.select_push_key_round("success", [3.0]) is None
    # rung 1: no GT-driven image choice → middle round
    assert pm.select_push_key_round("near_miss", [9.0, 6.0, 8.0, 9.0], obs_rung=1) == 3
    assert pm.select_push_key_round("near_miss", [9.0, 6.0, 8.0], obs_rung=2) == 2
    assert pm.select_push_key_round("wrong_direction", [9.0, 12.0, 8.0], obs_rung=2) == 2
    assert pm.key_round_post_png(Path("/nonexistent"), 3, 3) is None   # last round → final covers it


# ── recap prompt (model input) + record ──

def _user_prompt(rung, rounds):
    return pm.build_push_recap_user_prompt(
        instruction="Push.", outcome="push_plateau", outcome_class="wrong_direction", init=_snap(),
        round_meta=rounds, bounds=BOUNDS, obs_rung=rung, success_cm=SUCCESS_CM,
        image_labels=["start, front view", "end, front view", "right after round 2, front view"],
        max_words=100)


def test_recap_prompt_rung1_is_proprio_only():
    rounds = [_round(1, dist=0.118), _round(2, dist=0.13)]
    up = _user_prompt(1, rounds)
    assert "OUTCOME: failure" in up and "ROUND_COUNT: 2" in up
    assert "LEFT_TCP_POS = (X=22, Y=50, Z=-14)" in up
    reached = pm.grid_xyz([0.34, 0.04, 0.50], BOUNDS)
    assert f"R1: target (X=45, Y=8, Z=48) ORI rest → TCP reached (X={reached[0]}, Y={reached[1]}, Z={reached[2]})" in up
    assert not any(m in up for m in GT_MARKERS) and " cm" not in up, up
    sp = pm.build_push_recap_system_prompt(100, 1)
    for hint in ("aim point", "push depth", "contact height", "approach direction", "behind the cube"):
        assert hint not in sp
    assert "in your own words" in sp and "'LESSON:'" in sp and "ONLY what you see in the images" in sp


def test_recap_prompt_rung2_and_rung3_disclosure():
    rounds = [_round(1, dist=0.118), _round(2, dist=0.13)]
    up2 = _user_prompt(2, rounds)
    assert "OUTCOME: push_plateau  (class: wrong_direction)" in up2
    assert "CUBE_TO_GOAL = 8.2 cm   (disclosed)" in up2
    assert "closest TCP→cube 1.5 cm; cube→goal after 11.8 cm" in up2
    assert "CUBE_POS" not in up2 and "cube moved" not in up2
    up3 = _user_prompt(3, rounds)
    assert "CUBE_POS     = (X=56, Y=25)   (disclosed)" in up3 and "cube moved 2.0 cm" in up3
    assert "ONLY what you see" not in pm.build_push_recap_system_prompt(100, 3)


def test_emit_push_recap_builds_record_rung1(tmp_path):
    dump = tmp_path / "dump" / "run" / "ep1"
    dump.mkdir(parents=True)
    for n in ("round_01_pre.png", "round_02_pre.png", "round_03_pre.png", "episode_end.png"):
        (dump / n).write_bytes(_png())
    rounds = [_round(1, disp=0.022, dist=0.118), _round(2, disp=0.02, dist=0.13),
              _round(3, disp=0.02, dist=0.12)]
    seen = {}

    def fake_vlm(**kw):
        seen.update(kw)
        return "I aimed short of the cube. " * 40 + "LESSON: aim behind."

    buf = RecapBuffer(root=tmp_path / "recaps")
    rec = pm.emit_push_recap(
        recap_buffer=buf, ep_id="ep1", run_id="run", outcome="push_plateau", obs_rung=1,
        label="pilot", instruction="Push the yellow cube onto the green zone on the table.",
        init=_snap(), final=_snap(cube=(0.41, 0.0, 0.02)), round_meta=rounds, bounds=BOUNDS,
        ep_dump_dir=dump, rgb_start=None, rgb_end=None, teacher_url="http://x",
        success_cm=SUCCESS_CM, min_disp_cm=MIN_DISP_CM, vlm_call=fake_vlm,
        embed_fn=lambda _b: np.ones(DIM, dtype=np.float32))
    assert rec is not None
    assert len(rec.text_lesson.split()) <= 101          # hard cap (+ ellipsis token)
    assert not any(m in seen["user_prompt"] for m in GT_MARKERS)
    assert len(seen["image_base64_list"]) == 3          # init + end + key (middle round 2 → round_03_pre)
    sa = rec.state_anchor
    assert sa["init_L_EE"] == list(TCP_INT) and sa["ee_reference"] == "tcp"
    assert sa["outcome_class"] == "failure" and sa["disclosed"] == {} and sa["obs_rung"] == "1"
    assert "push_situation" not in sa and not any("cube" in k or "goal" in k for k in sa)
    gt = rec.metadata["offline_gt"]
    assert gt["outcome_class"] == "wrong_direction" and gt["situation"] == [0.40, 0.10, 0.48, 0.12]
    assert gt["final_cube_goal_dist_cm"] == 12.0
    assert rec.metadata["label"] == "pilot" and rec.metadata["obs_rung"] == "1"
    assert rec.metadata["key_round_idx"] == 2
    assert rec.image_anchors["key_round_post"].endswith("round_03_pre.png")
    reload = RecapBuffer(root=tmp_path / "recaps")
    reload.load()
    assert reload.all()[0].state_anchor == sa           # round-trips through the SHARED loader


def test_emit_push_recap_no_rounds_skips(tmp_path):
    assert pm.emit_push_recap(
        recap_buffer=RecapBuffer(root=tmp_path / "r"), ep_id="e", run_id="r", outcome="vlm_parse_fail",
        obs_rung=1, label="pilot", instruction="", init=_snap(), final=None, round_meta=[],
        bounds=BOUNDS, ep_dump_dir=None, rgb_start=_png(), rgb_end=None, teacher_url="",
        success_cm=5, min_disp_cm=1, vlm_call=lambda **k: "x", embed_fn=lambda b: np.ones(DIM)) is None


# ── replay augmentation + (c, s) from the replay alone ──

def _lc():
    return LevelConfig(level=99, name="WP1_3a_push", control_mode=ControlMode.PUSH_WAYPOINT,
                       task_instruction_template="Push.", workspace_bounds=WorkspaceBounds())


def test_write_push_episode_and_r_inputs(tmp_path):
    replay = ReplayBuffer(tmp_path / "replays")
    lc = _lc()
    init = _snap()
    rounds = [{**_round(1), **pm.snapshot_to_round_fields(init)}]
    vi = VLMInteraction(stage="stage1_eef", full_response="t", parsed_left_pos=(45, 8, 48),
                        parsed_right_pos=(0, 0, 0))
    b = lc.workspace_bounds
    md = {"label": "pilot", "obs_rung": 1, "ee_reference": "tcp", "goal_pose_b": list(init.goal_b),
          "workspace_bounds": {"x": list(b.x_bounds), "y": list(b.y_bounds), "z": list(b.z_bounds)},
          "rounds_state": pm.replay_rounds_state(rounds)}
    pm.write_push_episode(replay, ("ep1", "run1", lc, {"instruction": "Push."}, EpisodeOutcome.TIMEOUT,
                                   ["label:pilot"], [], [vi], 1.0, _png(), _png(), 0.0),
                          init=init, env_seed=4700, metadata=md)
    ep = json.loads((tmp_path / "replays" / "run1" / "failure" / "ep1.json").read_text())
    assert ep["init_cube_pose"] == {"yellow": [0.40, 0.10, 0.02]}
    assert ep["init_left_ee_pose"] == [0.25, 0.20, 0.30] and ep["env_seed"] == 4700   # init TCP
    assert ep["metadata"]["rounds_state"][0]["ee_start_b"] == [0.25, 0.20, 0.30]
    assert ep["rgb_start_path"] == "run1/failure/ep1_start.png"   # shared writer still ran
    ri = push_r_inputs.r_inputs_from_replay(ep)
    assert ri.obs_rung == 1
    assert ri.c_raw == pytest.approx((0.3525 - 0.25, 0.032 - 0.20))
    assert ri.push_dir == pytest.approx(tuple(_unit([0.08, 0.02])))
    ep2 = {**ep, "metadata": {**ep["metadata"], "rounds_state": []}}   # int-grid fallback
    assert push_r_inputs.r_inputs_from_replay(ep2).r1_target_xy == pytest.approx((0.3525, 0.032))
    loaded = push_r_inputs.load_push_r_inputs(tmp_path / "replays" / "run1")
    assert [x.ep_id for x in loaded] == ["ep1"]
    assert push_r_inputs.load_push_r_inputs(tmp_path / "replays" / "run1", obs_rung=2) == []
    res = push_r_inputs.r_for_candidates(loaded * 4, n_perm=20)
    assert "c_along_push_dir|s_push_angle" in res and all("r" in v for v in res.values())


# ── loop wiring with a fake env (no sim) ──

class _FakeUnwrapped:
    def __init__(self, mel):
        self.max_episode_length = mel
        self.episode_length_buf = [0]


class _FakeGym:
    def __init__(self, mel):
        self.unwrapped = _FakeUnwrapped(mel)


class _FakePushEnv:
    """IsaacLabEnvInterface stand-in for the 2026-10-05 push interface: TCP
    state, rest hand quat, execute_push_segment(target_is_tcp=True) with the
    new keys; cube moves 3 cm toward the goal per segment; optional auto-reset."""

    Q_REST = torch.tensor([0.0, 0.7071, 0.0, 0.7071])

    def __init__(self, mel=2000, reset_at_round=None, frames=False, rung="1", top=None, motion=None):
        self.env = _FakeGym(mel)
        self.push_obs_rung = rung
        self.reset_at_round = reset_at_round
        self.frames = frames
        self.seg_calls = []
        # top camera present iff TopCam env (default: present for 1b/2/3)
        self.top = pm.has_top_view(rung) if top is None else top
        # motion(round) → cube displacement (m) toward the goal; default 3 cm/round
        self.motion = motion or (lambda r: 0.03)

    def reset(self, seed=None):
        self.cube = np.array([0.40, 0.10, 0.02])
        self.goal = np.array([0.48, 0.12, 0.02])
        self.tcp = np.array([0.25, 0.20, 0.30])
        self.env.unwrapped.episode_length_buf[0] = 1
        self.rounds = 0

    def get_rgb(self):
        return _png(size=(32, 24))

    def get_rgb_top(self):
        return _png(color=(200, 0, 0), size=(16, 16)) if self.top else b""

    def get_state(self, lc):
        g = pm.grid_xyz(self.tcp, lc.workspace_bounds)
        return {"left_x": g[0], "left_y": g[1], "left_z": g[2], "right_x": 0, "right_y": 0,
                "right_z": 0, "left_gripper": "closed (locked)", "oracle_block": "",
                "view_block": pm.view_block(self.push_obs_rung)}

    def get_cube_pose_b(self):
        return self.cube.tolist()

    def get_goal_pose_b(self):
        return self.goal.tolist()

    def get_left_tcp_pos_b(self):
        return self.tcp.tolist()

    def get_left_hand_quat_b(self):
        return self.Q_REST.clone()

    def execute_push_segment(self, target, quat, steps, frame_every=0, target_is_tcp=False):
        self.seg_calls.append({"target": target.clone(), "quat": quat.clone(), "tcp": target_is_tcp})
        self.rounds += 1
        if self.rounds == self.reset_at_round:
            self.env.unwrapped.episode_length_buf[0] = 3        # IsaacLab auto-reset
            self.cube = np.array([0.40, 0.10, 0.02])
        else:
            self.env.unwrapped.episode_length_buf[0] += steps
            d = self.goal - self.cube
            self.cube = self.cube + self.motion(self.rounds) * d / np.linalg.norm(d)
            self.tcp = target.numpy().astype(float) + np.array([0.01, 0.0, 0.0])
        moved = self.rounds != self.reset_at_round and self.motion(self.rounds) > 0
        return {"tau_peak_preclip": 0.5, "tau_peak_postclip": 0.5, "tau_warn_steps": 0,
                "tau_flag_steps": 0, "min_err_cm": 1.0, "frames": [self.get_rgb()] if self.frames else [],
                "ori_err_deg": [5.0] * 70 + [2.0] * 19 + [3.0], "ori_err_deg_final": 3.0,
                "tcp_target_b": target.tolist(), "hand_target_b": [0.2, 0.1, 0.6],
                "tcp_final_b": self.tcp.tolist(),
                "contact": {"tcp_to_cube_min_cm": 0.4, "link_to_cube_min_cm": {},
                            "first_cube_move": ({"step": 40, "nearest_link": "openarm_left_finger1",
                                                 "anatomy": "finger", "nearest_dist_cm": 0.3}
                                                if moved else None),
                            "cube_disp_vec_cm": [3.0, 0.7, 0.0]}}


class _Parsed:
    class _P:
        x, y, z = 45, 8, 48
    target_pos, target_ori, grip, stop, thought = _P(), None, None, False, "push it"


def _patch_stage1(monkeypatch, calls):
    pc = importlib.import_module("aiongenos.orchestrator.push_collect")

    def fake(lc, url, rgb, state, conversation=None, memory_preamble_text=None,
             memory_preamble_images_b64=None, **kw):
        calls.append({"conv": conversation is not None, "pre": memory_preamble_text, "state": dict(state),
                      "extra": kw.get("extra_image_bytes")})
        return _Parsed(), 10.0, None
    monkeypatch.setattr(pc, "run_stage1_eef", fake)
    return pc


def test_budget_guard_raises(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    with pytest.raises(RuntimeError, match="max_episode_length"):
        pc.run_push_collect_loop(_FakePushEnv(mel=720), _lc(), "u", ReplayBuffer(tmp_path), 1,
                                 steps_per_segment=90)


def test_rung_mismatch_with_retriever_raises(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    retr = pm.PushMemoryRetriever(RecapBuffer(root=tmp_path / "r"), obs_rung=2,
                                  embed_fn=lambda _b: np.ones(DIM))
    with pytest.raises(RuntimeError, match="obs_rung"):
        pc.run_push_collect_loop(_FakePushEnv(), _lc(), "u", ReplayBuffer(tmp_path), 1,
                                 memory_retriever=retr)


def test_loop_option_a_tcp_rest_orientation_and_recap(tmp_path, monkeypatch):
    calls = []
    pc = _patch_stage1(monkeypatch, calls)
    buf = RecapBuffer(root=tmp_path / "recaps")
    img = tmp_path / "i.png"
    img.write_bytes(_png())
    e = _unit(np.ones(DIM))
    buf.add(_rec("past", True, e, img))
    retr = pm.PushMemoryRetriever(buf, embed_fn=lambda _b: e)
    seen = {}

    def fake_vlm(**kw):
        seen.update(kw)
        return "Aimed short. LESSON: go further."
    real_emit = pm.emit_push_recap
    # fake teacher + embedder injected through a wrapper (defaults bound at def time)
    monkeypatch.setattr(pm, "emit_push_recap", lambda **kw: real_emit(
        **kw, vlm_call=fake_vlm, embed_fn=lambda _b: e))
    env = _FakePushEnv()
    summ = pc.run_push_collect_loop(env, _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                                    env_seed_base=4700, recap_buffer=buf, memory_retriever=retr,
                                    dump_images_root=tmp_path / "dumps")
    # Option A: preamble on round 1 only; no GT in any stage-1 state or preamble
    assert calls[0]["conv"] and "PAST SIMILAR PUSH EPISODES" in calls[0]["pre"]
    assert all(not c["conv"] and c["pre"] is None for c in calls[1:])
    assert not any(m in calls[0]["pre"] for m in GT_MARKERS)
    assert all(not any(k.startswith(("cube", "goal")) for k in c["state"]) for c in calls)
    # TCP target + rest orientation (no ORI → q_rest exactly, every round)
    assert all(sc["tcp"] for sc in env.seg_calls)
    assert all(torch.allclose(sc["quat"], _FakePushEnv.Q_REST) for sc in env.seg_calls)
    ep = summ["episodes"][0]
    assert ep["outcome"] == "success" and ep["label"] == "pilot" and ep["obs_rung"] == "1"
    rm = ep["round_meta"][0]
    assert rm["memory_preamble"] is True and rm["ee_start_b"] == [0.25, 0.20, 0.30]
    assert rm["ori_err_deg_final"] == 3.0 and rm["ori_err_deg_max_last20"] == 3.0
    assert rm["contact"]["first_cube_move"]["anatomy"] == "finger"
    assert rm["tcp_reach_err_cm"] == pytest.approx(1.0, abs=1e-3)
    assert rm["hand_target_b"] == [0.2, 0.1, 0.6] and "neutral_x_n" not in rm
    run = summ["run_id"]
    dd = tmp_path / "dumps" / run / ep["ep_id"]
    assert (dd / "round_01_pre.png").exists() and (dd / "episode_end.png").exists()
    rj = json.loads(next((tmp_path / "rp" / run / "success").glob("*.json")).read_text())
    assert rj["env_seed"] == 4700 and rj["init_cube_pose"]["yellow"] == [0.40, 0.10, 0.02]
    assert rj["metadata"]["obs_rung"] == "1" and rj["metadata"]["ee_reference"] == "tcp"
    assert rj["metadata"]["memory_hits"][0]["ep_id"] == "past"
    assert len(buf) == 2 and buf.all()[-1].metadata["obs_rung"] == "1"
    assert not any(m in seen["user_prompt"] for m in GT_MARKERS)


def test_loop_auto_reset_flags_and_ends(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    buf = RecapBuffer(root=tmp_path / "recaps")
    env = _FakePushEnv(reset_at_round=2)   # R1: 8.2→5.2 cm (no success), R2 resets
    summ = pc.run_push_collect_loop(env, _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                                    recap_buffer=buf, recap_buffer_readonly=False)
    ep = summ["episodes"][0]
    rj = json.loads(next((tmp_path / "rp" / summ["run_id"]).glob("*/*.json")).read_text())
    assert "env_auto_reset" in rj["flags"] and rj["metadata"]["final_cube_pose_b"] is None
    assert ep["rounds"] == 1 and ep["outcome"] == "timeout"       # outcome unchanged, round 2 dropped
    assert len(buf) == 0                                          # no recap from a reset scene


def test_readonly_writes_no_recap(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    buf = RecapBuffer(root=tmp_path / "recaps")
    pc.run_push_collect_loop(_FakePushEnv(), _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                             recap_buffer=buf, recap_buffer_readonly=True)
    assert len(buf) == 0


def test_gif_tag_in_bottom_strip(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    summ = pc.run_push_collect_loop(_FakePushEnv(frames=True), _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                                    gif_frame_every=1)
    import imageio.v2 as imageio
    frames = imageio.mimread(summ["gif_path"])
    h, w = frames[0].shape[:2]
    assert (w, h) == (32, 24 + pc.GIF_STRIP_PX)
    # scene rows untouched (original solid colour), strip rows carry the tag
    assert np.all(frames[0][:24, :, :3] == np.array([10, 20, 30]))
    assert frames[0][24:, :, :3].max() > 0


# ── rung 1b (PI 2026-10-06): top view, byte-identical rung-1 prompt, Pin-12 ──

# sha256 of the rung-1 _S1_EEF_PUSH rendering BEFORE {view_block} was added
# (template at HEAD 816d887), for the fixed state below
_RUNG1_PROMPT_SHA = "9344e121460d2776ab9cd5e91381198b4d99b6506b2f164500b07018b6ba00b2"
_PROMPT_STATE = dict(instruction="Push the yellow cube onto the green zone on the table.",
                     left_x=22, left_y=50, left_z=-14, right_x=1, right_y=-50, right_z=-14,
                     left_gripper="closed (locked)", oracle_block="")


def test_rung1_stage1_prompt_byte_identical():
    import hashlib
    from aiongenos.vlm.prompts import get_stage1_prompt
    txt = get_stage1_prompt(_lc(), {**_PROMPT_STATE, "view_block": pm.view_block("1")})
    assert hashlib.sha256(txt.encode()).hexdigest() == _RUNG1_PROMPT_SHA


def test_rung1b_view_block_and_levels():
    from aiongenos.vlm.prompts import get_stage1_prompt
    assert [pm.oracle_level(r) for r in ("1", "1b", "2", "3")] == [1, 1, 2, 3]
    assert [pm.has_top_view(r) for r in ("1", "1b", "2", "3")] == [False, True, True, True]
    assert pm.norm_rung(1) == "1" and pm.view_block("1") == ""
    with pytest.raises(ValueError):
        pm.norm_rung("4")
    txt = get_stage1_prompt(_lc(), {**_PROMPT_STATE, "view_block": pm.view_block("1b")})
    assert "  LEFT_GRIPPER = closed (locked)\nThe last image is a top-down view of the current scene.\n\n" in txt
    assert not any(m in txt for m in GT_MARKERS)


_EEF_REPLY = "THOUGHT: push.\nLEFT_TARGET_POS: X=45 Y=8 Z=48\nSTOP: false"


def _img_urls(content):
    return [c["image_url"]["url"] for c in content if c["type"] == "image_url"]


def test_run_stage1_eef_image_order_single_turn(monkeypatch):
    from aiongenos.pipeline import stage1_reasoning as s1
    from aiongenos.vlm.client import build_chat_request, encode_image_bytes_base64 as enc
    seen = {}

    def fake_call(**kw):
        seen["payload"] = build_chat_request(**{k: kw[k] for k in (
            "system_prompt", "user_prompt", "image_base64", "image_base64_list")})
        return _EEF_REPLY
    monkeypatch.setattr(s1, "call_vlm_sync", fake_call)
    front, top = _png((1, 1, 1)), _png((2, 2, 2))
    parsed, _, err = s1.run_stage1_eef(_lc(), "u", front, {**_PROMPT_STATE, "view_block": pm.view_block("1b")},
                                       extra_image_bytes=[top])
    assert err is None and parsed.target_pos.x == 45
    urls = _img_urls(seen["payload"]["messages"][0]["content"])
    assert urls == [f"data:image/png;base64,{enc(front)}", f"data:image/png;base64,{enc(top)}"]
    # no extra → exactly the pre-1b payload (image_base64_list None)
    s1.run_stage1_eef(_lc(), "u", front, {**_PROMPT_STATE, "view_block": ""})
    assert _img_urls(seen["payload"]["messages"][0]["content"]) == [f"data:image/png;base64,{enc(front)}"]


def test_run_stage1_eef_image_order_conversation(monkeypatch):
    from aiongenos.pipeline import stage1_reasoning as s1
    from aiongenos.vlm.client import EpisodeConversation, encode_image_bytes_base64 as enc
    from aiongenos.vlm.prompts import get_stage1_system_prompt
    seen = {}

    def fake_hist(**kw):
        seen["content"] = [dict(c) for c in kw["conversation"].messages[-1]["content"]]
        return _EEF_REPLY
    monkeypatch.setattr(s1, "call_vlm_history_sync", fake_hist)
    front, top = _png((1, 1, 1)), _png((2, 2, 2))
    conv = EpisodeConversation(get_stage1_system_prompt())
    s1.run_stage1_eef(_lc(), "u", front, {**_PROMPT_STATE, "view_block": pm.view_block("1b")},
                      conversation=conv, memory_preamble_text="PAST", memory_preamble_images_b64=["P1", "P2"],
                      extra_image_bytes=[top])
    c = seen["content"]
    assert _img_urls(c) == ["data:image/png;base64,P1", "data:image/png;base64,P2",
                            f"data:image/png;base64,{enc(front)}", f"data:image/png;base64,{enc(top)}"]
    assert c[-1]["type"] == "text" and c[-1]["text"].startswith("TASK:")   # prompt text stays last


def test_preamble_names_two_current_images_at_1b():
    recs = [_rec("x", False, np.ones(DIM), rung="1b")]
    assert ("The LAST TWO images below are the CURRENT scene you must act on: front view, then top-down view."
            in pm.format_push_preamble_text(recs, [0.9], obs_rung="1b"))
    assert "The LAST image below is the CURRENT scene you must act on." in pm.format_push_preamble_text(recs, [0.9], "1")


def test_loop_rung1b_top_view_dumps_and_recap(tmp_path, monkeypatch):
    calls = []
    pc = _patch_stage1(monkeypatch, calls)
    buf = RecapBuffer(root=tmp_path / "recaps")
    img = tmp_path / "i.png"
    img.write_bytes(_png())
    e = _unit(np.ones(DIM))
    buf.add(_rec("past", True, e, img, rung="1b"))
    q_seen = []

    def q_embed(b):
        q_seen.append(b)
        return e
    retr = pm.PushMemoryRetriever(buf, obs_rung="1b", embed_fn=q_embed)
    seen = {}

    def fake_vlm(**k):
        seen.update(k)
        return "Saw it. LESSON: x."
    real_emit = pm.emit_push_recap
    monkeypatch.setattr(pm, "emit_push_recap", lambda **kw: real_emit(
        **kw, vlm_call=fake_vlm, embed_fn=lambda _b: e))
    env = _FakePushEnv(rung="1b", motion=lambda r: 0.03 if r == 1 else 0.0)   # contact R1, then stalls
    summ = pc.run_push_collect_loop(env, _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                                    recap_buffer=buf, memory_retriever=retr, dump_images_root=tmp_path / "d")
    top = env.get_rgb_top()
    assert all(c["extra"] == [top] for c in calls)                 # top view every round
    assert all(c["state"]["view_block"] == pm.TOP_VIEW_SENTENCE for c in calls)
    assert "LAST TWO images" in calls[0]["pre"]
    assert q_seen == [env.get_rgb()]                               # retrieval key = FRONT start image
    ep = summ["episodes"][0]
    dd = tmp_path / "d" / summ["run_id"] / ep["ep_id"]
    for n in ("episode_start_top.png", "round_01_pre_top.png", "episode_end_top.png"):
        assert (dd / n).exists(), n
    up = seen["user_prompt"]
    assert "Image 2 = start, top-down view" in up and "end, top-down view" in up
    assert not any(m in up for m in GT_MARKERS) and " cm" not in up       # oracle level 1
    assert summ["obs_rung"] == "1b" and summ["top_view"] is True
    assert buf.all()[-1].metadata["obs_rung"] == "1b"
    assert ep["plateau_armed_round"] == 1 and ep["outcome"] == "push_plateau"   # armed R1, R2-4 stall


def test_loop_rung1b_without_camera_raises(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    with pytest.raises(RuntimeError, match="top-down camera"):
        pc.run_push_collect_loop(_FakePushEnv(rung="1b", top=False), _lc(), "u", ReplayBuffer(tmp_path), 1)


def test_pin12_plateau_arms_only_after_contact(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])

    def contact_at_5(r):   # no contact R1–4, push R5, then stall
        return 0.02 if r == 5 else 0.0
    ep = pc.run_push_collect_loop(_FakePushEnv(rung="1b", motion=contact_at_5), _lc(), "u",
                                  ReplayBuffer(tmp_path / "a"), 1)["episodes"][0]
    assert ep["plateau_armed_round"] == 5 and ep["rounds"] == 8 and ep["outcome"] == "push_plateau"
    assert [r["plateau_armed"] for r in ep["round_meta"]] == [False] * 4 + [True] * 4
    never = pc.run_push_collect_loop(_FakePushEnv(rung="1b", motion=lambda r: 0.0), _lc(), "u",
                                     ReplayBuffer(tmp_path / "b"), 1)["episodes"][0]
    assert never["plateau_armed_round"] is None and never["rounds"] == pc.PUSH_ROUND_CAP
    assert never["outcome"] == "timeout"
    # rung 1 keeps the piloted rule: armed from round 1 → plateau at round 3
    s1 = pc.run_push_collect_loop(_FakePushEnv(rung="1", motion=lambda r: 0.0), _lc(), "u",
                                  ReplayBuffer(tmp_path / "c"), 1)["episodes"][0]
    assert s1["plateau_armed_round"] == 1 and s1["rounds"] == 3 and s1["outcome"] == "push_plateau"


# ── recap confabulation flagger (scripts/analysis/wp3a_pilot_report.py) ──

def test_confabulation_flagger():
    import wp3a_pilot_report as rep_
    f = rep_.confab_flags("The cube was pushed away from the goal. LESSON: aim better.")
    assert f["keyword"] and f["assertive"]
    f = rep_.confab_flags("The cube remained stationary. To move the cube toward the zone, I should aim behind it.")
    assert f["keyword"] and not f["assertive"]
    assert not rep_.confab_flags("I never reached the cube. LESSON: lower Z.")["keyword"]
    eps = [{"ep_id": "a", "round_meta": [{"contact": {"first_cube_move": None}}]},
           {"ep_id": "b", "round_meta": [{"contact": {"first_cube_move": {"anatomy": "finger"}}}]},
           {"ep_id": "c", "round_meta": [{"contact": {}}]}]
    out = rep_.confabulation_check(eps, {"a": "The cube shifted left.", "b": "The cube moved.",
                                         "c": "Nothing happened."})
    assert out["n_recaps_cube_never_moved"] == 2                  # b excluded: cube did move
    assert out["keyword_flagged"] == 1 and out["assertive_rate"] == 0.5
