"""push_memory: scoring, success floor, preamble, recap-record construction,
replay augmentation, and (c, s) extraction — no sim, no teacher (fakes)."""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from aiongenos.config import ControlMode, LevelConfig, WorkspaceBounds
from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord
from aiongenos.orchestrator import push_memory as pm
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome, VLMInteraction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))
import push_r_inputs  # noqa: E402

DIM = 8
SUCCESS_CM, MIN_DISP_CM = 5.0, 1.0


def _png(color=(10, 20, 30)) -> bytes:
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def _snap(cube=(0.40, 0.10, 0.02), goal=(0.48, 0.12, 0.02), ee=(0.25, 0.20, 0.30)):
    return pm.PushStateSnapshot(ee_b=ee, cube_b=cube, goal_b=goal, ee_int=(22, 50, -14),
                                cube_int=(55, 25), goal_int=(73, 30))


def _round(i, target_int=(45, 8, 48), target_m=(0.3525, 0.032, 0.518), disp=0.02, dist=0.07):
    return {"round": i, "eef_target_int": list(target_int), "eef_target_m": list(target_m),
            "ori_offset_deg": None, "ori_applied": False, "cube_disp_m": disp,
            "cube_goal_dist_m": dist, "servo_min_err_cm": 3.8}


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def _rec(ep_id, situation, success, emb, img_path=None, run_id="r0"):
    return RecapRecord(
        ep_id=ep_id, run_id=run_id, outcome="success" if success else "push_plateau",
        is_success=success, image_anchors={"init_pre": str(img_path)} if img_path else {},
        state_anchor={"init_L_EE": [22, 50, -14], "push_situation": list(situation),
                      "init_cube_int": [55, 25], "goal_int": [73, 30],
                      "init_cube_goal_dist_cm": 8.2, "r1_eef_target_int": [45, 8, 48],
                      "r1_cube_disp_cm": 2.2, "final_cube_goal_dist_cm": 6.0,
                      "best_cube_goal_dist_cm": 5.5, "round_count": 4,
                      "outcome_class": "near_miss"},
        text_lesson=f"lesson {ep_id}", image_embedding=[float(x) for x in emb])


# ── scoring ──

def test_score_formula_matches_reach_shape():
    q_sit = [0.40, 0.10, 0.48, 0.12]
    e = _unit(np.arange(1, DIM + 1))
    recs = [_rec("a", q_sit, True, e), _rec("b", [0.40, 0.15, 0.48, 0.12], False, -e)]
    s = pm.score_push_candidates(recs, q_sit, e, image_weight=0.4, state_scale_cm=5.0)
    assert s[0] == pytest.approx(0.4 * 1.0 + 0.6 * 1.0, abs=1e-5)
    assert s[1] == pytest.approx(0.4 * -1.0 + 0.6 * math.exp(-5.0 / 5.0), abs=1e-5)


def test_score_dim_mismatch_drops_image_term():
    q_sit = [0.40, 0.10, 0.48, 0.12]
    recs = [_rec("a", [0.40, 0.12, 0.48, 0.12], True, _unit(np.ones(DIM)))]
    s = pm.score_push_candidates(recs, q_sit, _unit(np.ones(DIM + 1)), 0.4, 5.0)
    assert s[0] == pytest.approx(math.exp(-2.0 / 5.0), abs=1e-5)


def test_success_floor_pulls_in_lower_scored_success():
    e = _unit(np.ones(DIM))
    recs = [_rec(f"f{i}", [0.40, 0.10, 0.48, 0.12], False, e) for i in range(3)]
    recs += [_rec(f"s{i}", [0.42, 0.15, 0.50, 0.18], True, e) for i in range(2)]
    scores = pm.score_push_candidates(recs, [0.40, 0.10, 0.48, 0.12], e, 0.4, 5.0)
    idx = pm.select_with_success_floor(recs, scores, fine_k=3, success_floor_frac=2 / 3)
    chosen = [recs[j].ep_id for j in idx]
    assert sorted(c for c in chosen if c.startswith("s")) == ["s0", "s1"]
    assert len(chosen) == 3
    assert list(scores[idx]) == sorted(scores[idx], reverse=True)


# ── retriever on a real RecapBuffer in tmp ──

def test_retriever_ranks_by_situation_and_skips_foreign(tmp_path):
    buf = RecapBuffer(root=tmp_path / "recaps")
    img = tmp_path / "init.png"
    img.write_bytes(_png())
    e = _unit(np.ones(DIM))
    near, far = [0.40, 0.10, 0.48, 0.12], [0.42, 0.15, 0.50, 0.19]
    buf.add(_rec("near", near, True, e, img))
    buf.add(_rec("far", far, True, e, img))
    buf.add(_rec("noimg", near, True, e, None))          # dropped: no init_pre image
    reach = _rec("reach", near, True, e, img)
    reach.state_anchor.pop("push_situation")               # a reach-shaped record
    buf.add(reach)
    with pytest.raises(ValueError):
        pm.assert_push_only_buffer(buf)
    r = pm.PushMemoryRetriever(buf, top_k=3, embed_fn=lambda _b: e)
    pre = r.retrieve_for_episode(_png(), near)
    ids = [x.ep_id for x in pre.retrieved_records]
    assert "reach" not in ids and "noimg" not in ids
    assert ids == ["near", "far"]
    assert len(pre.past_image_base64_list) == 2
    assert pre.similarities[0] > pre.similarities[1]
    assert "PAST SIMILAR PUSH EPISODES" in pre.prelude_text
    assert _preamble_ok(pre.prelude_text)


def _preamble_ok(text: str) -> bool:
    return ("cube start = (X=55, Y=25)" in text and "round-1 EEF target = (X=45, Y=8, Z=48)" in text
            and "lesson     : lesson near" in text and "choose your push target" in text
            and "L_EE" not in text)


def test_retriever_empty_buffer(tmp_path):
    r = pm.PushMemoryRetriever(RecapBuffer(root=tmp_path / "e"), embed_fn=lambda _b: np.ones(DIM))
    assert r.retrieve_for_episode(_png(), [0.4, 0.1, 0.48, 0.12]).is_empty


# ── outcome class + key round ──

@pytest.mark.parametrize("outcome,init,dists,disps,want", [
    ("success", 8.0, [3.0], [5.0], "success"),
    ("push_plateau", 8.0, [8.0, 8.0, 8.0], [0.1, 0.2, 0.0], "cube_not_moved"),
    ("timeout", 8.0, [6.0, 7.2, 9.0], [2.0, 1.5, 2.0], "near_miss"),
    ("push_plateau", 8.0, [10.0, 11.8], [2.0, 2.0], "wrong_direction"),
    ("timeout", 8.0, [8.2, 8.4], [1.5, 1.5], "timeout"),
])
def test_classify_push_outcome(outcome, init, dists, disps, want):
    assert pm.classify_push_outcome(outcome, init, dists, disps, SUCCESS_CM, MIN_DISP_CM) == want


def test_key_round_selection():
    assert pm.select_push_key_round("success", [3.0]) is None
    assert pm.select_push_key_round("near_miss", [9.0, 6.0, 8.0]) == 2
    assert pm.select_push_key_round("wrong_direction", [9.0, 12.0, 8.0]) == 2
    assert pm.select_push_key_round("timeout", [9.0, 9.0, 9.0, 9.0]) == 3
    assert pm.key_round_post_png(Path("/nonexistent"), 3, 3) is None   # last round → final covers it


# ── recap prompt + record (fake teacher + fake embedder) ──

def test_emit_push_recap_builds_record(tmp_path):
    dump = tmp_path / "dump" / "run" / "ep1"
    dump.mkdir(parents=True)
    for n in ("round_01_pre.png", "round_02_pre.png", "round_03_pre.png", "episode_end.png"):
        (dump / n).write_bytes(_png())
    rounds = [_round(1, disp=0.022, dist=0.118), _round(2, disp=0.02, dist=0.13),
              _round(3, disp=0.02, dist=0.12)]   # argmax = R2 → key scene round_03_pre
    seen = {}

    def fake_vlm(**kw):
        seen.update(kw)
        return "I aimed short of the cube. " * 40 + "LESSON: aim behind."

    buf = RecapBuffer(root=tmp_path / "recaps")
    rec = pm.emit_push_recap(
        recap_buffer=buf, ep_id="ep1", run_id="run", outcome="push_plateau", label="pilot",
        instruction="Push the yellow cube onto the green zone on the table.",
        init=_snap(), final=_snap(cube=(0.41, 0.0, 0.02)), round_meta=rounds,
        ep_dump_dir=dump, rgb_start=None, rgb_end=None, teacher_url="http://x",
        success_cm=SUCCESS_CM, min_disp_cm=MIN_DISP_CM, vlm_call=fake_vlm,
        embed_fn=lambda _b: np.ones(DIM, dtype=np.float32))
    assert rec is not None
    assert len(rec.text_lesson.split()) <= 101          # hard cap (+ ellipsis token)
    up = seen["user_prompt"]
    assert "ROUND 1 — YOUR EEF TARGET vs WHAT HAPPENED" in up
    assert "cube moved 2.2 cm; cube→goal 8.2 → 11.8 cm (further by 3.6 cm)" in up
    assert "R3: EEF→(X=45, Y=8, Z=48)  cube moved 2.0 cm, cube→goal 12.0 cm (-1.0)" in up
    assert "LESSON:" in seen["system_prompt"] and "100 words MAX" in seen["system_prompt"]
    assert len(seen["image_base64_list"]) == 3          # init + end + key
    sa = rec.state_anchor
    assert sa["outcome_class"] == "wrong_direction"
    assert sa["init_L_EE"] == [22, 50, -14]             # honest grid, not (0,0,0)
    assert sa["push_situation"] == [0.40, 0.10, 0.48, 0.12]
    assert sa["final_cube_goal_dist_cm"] == 12.0
    assert sa["r1_eef_disp_m"] == pytest.approx([0.1025, -0.168, 0.218], abs=1e-4)
    assert rec.metadata["label"] == "pilot" and rec.metadata["task"] == pm.PUSH_TASK_TAG
    assert rec.metadata["key_round_idx"] == 2
    assert rec.image_anchors["key_round_post"].endswith("round_03_pre.png")
    # round-trips through the SHARED buffer loader unchanged
    reload = RecapBuffer(root=tmp_path / "recaps")
    reload.load()
    assert reload.all()[0].state_anchor == sa


def test_emit_push_recap_no_rounds_skips(tmp_path):
    assert pm.emit_push_recap(
        recap_buffer=RecapBuffer(root=tmp_path / "r"), ep_id="e", run_id="r", outcome="vlm_parse_fail",
        label="pilot", instruction="", init=_snap(), final=None, round_meta=[], ep_dump_dir=None,
        rgb_start=_png(), rgb_end=None, teacher_url="", success_cm=5, min_disp_cm=1,
        vlm_call=lambda **k: "x", embed_fn=lambda b: np.ones(DIM)) is None


# ── replay augmentation + (c, s) from the replay alone ──

def test_write_push_episode_and_r_inputs(tmp_path):
    replay = ReplayBuffer(tmp_path / "replays")
    lc = LevelConfig(level=99, name="WP1_3a_push", control_mode=ControlMode.PUSH_WAYPOINT,
                     task_instruction_template="Push.", workspace_bounds=WorkspaceBounds())
    init = _snap()
    rounds = [{**_round(1), **pm.snapshot_to_round_fields(init)}]
    vi = VLMInteraction(stage="stage1_eef", full_response="t", parsed_left_pos=(45, 8, 48),
                        parsed_right_pos=(0, 0, 0))
    b = lc.workspace_bounds
    md = {"label": "pilot", "goal_pose_b": list(init.goal_b),
          "workspace_bounds": {"x": list(b.x_bounds), "y": list(b.y_bounds), "z": list(b.z_bounds)},
          "rounds_state": pm.replay_rounds_state(rounds)}
    pm.write_push_episode(replay, ("ep1", "run1", lc, {"instruction": "Push."}, EpisodeOutcome.TIMEOUT,
                                   ["label:pilot"], [], [vi], 1.0, _png(), _png(), 0.0),
                          init=init, env_seed=4700, metadata=md)
    f = tmp_path / "replays" / "run1" / "failure" / "ep1.json"
    ep = json.loads(f.read_text())
    assert ep["init_cube_pose"] == {"yellow": [0.40, 0.10, 0.02]}
    assert ep["init_left_ee_pose"] == [0.25, 0.20, 0.30] and ep["env_seed"] == 4700
    assert ep["metadata"]["rounds_state"][0]["cube_b_pre"] == [0.40, 0.10, 0.02]
    assert ep["rgb_start_path"] == "run1/failure/ep1_start.png"   # shared writer still ran
    ri = push_r_inputs.r_inputs_from_replay(ep)
    assert ri.c_raw == pytest.approx((0.3525 - 0.25, 0.032 - 0.20))
    assert ri.push_dir == pytest.approx(tuple(_unit([0.08, 0.02])))
    # fallback path (no rounds_state): int grid → metric via replay's bounds
    ep2 = {**ep, "metadata": {**ep["metadata"], "rounds_state": []}}
    assert push_r_inputs.r_inputs_from_replay(ep2).r1_target_xy == pytest.approx((0.3525, 0.032))
    loaded = push_r_inputs.load_push_r_inputs(tmp_path / "replays" / "run1")
    assert [x.ep_id for x in loaded] == ["ep1"]
    res = push_r_inputs.r_for_candidates(loaded * 4, n_perm=20)
    assert set(res) >= {"c_along_push_dir|s_push_angle"} and all("r" in v for v in res.values())


# ── loop wiring with a fake env (no sim): Option A, budget guard, auto-reset ──

class _FakeUnwrapped:
    def __init__(self, mel):
        self.max_episode_length = mel
        self.episode_length_buf = [0]


class _FakeGym:
    def __init__(self, mel):
        self.unwrapped = _FakeUnwrapped(mel)


class _FakePushEnv:
    """Minimal IsaacLabEnvInterface stand-in: cube moves 3 cm toward the goal
    per segment; optional auto-reset at a given round."""

    def __init__(self, mel=2000, reset_at_round=None):
        self.env = _FakeGym(mel)
        self.reset_at_round = reset_at_round
        self.rounds = 0

    def reset(self, seed=None):
        self.cube = np.array([0.40, 0.10, 0.02])
        self.goal = np.array([0.48, 0.12, 0.02])
        self.env.unwrapped.episode_length_buf[0] = 1
        self.rounds = 0

    def get_rgb(self):
        return _png()

    def get_state(self, lc):
        return {"left_x": 22, "left_y": 50, "left_z": -14, "cube_x": 55, "cube_y": 25,
                "goal_x": 73, "goal_y": 30}

    def get_cube_pose_b(self):
        return self.cube.tolist()

    def get_goal_pose_b(self):
        return self.goal.tolist()

    def get_left_ee_pose_b(self):
        return [0.25, 0.20, 0.30]

    def execute_push_segment(self, target, quat, steps, frame_every=0):
        self.rounds += 1
        if self.rounds == self.reset_at_round:
            self.env.unwrapped.episode_length_buf[0] = 3        # IsaacLab auto-reset
            self.cube = np.array([0.40, 0.10, 0.02])
        else:
            self.env.unwrapped.episode_length_buf[0] += steps
            d = self.goal - self.cube
            self.cube = self.cube + 0.03 * d / np.linalg.norm(d)
        return {"tau_peak_preclip": 0.5, "tau_peak_postclip": 0.5, "tau_warn_steps": 0,
                "tau_flag_steps": 0, "min_err_cm": 1.0}


class _Parsed:
    class _P:
        x, y, z = 45, 8, 48
    target_pos, target_ori, grip, stop, thought = _P(), None, None, False, "push it"


def _lc():
    return LevelConfig(level=99, name="WP1_3a_push", control_mode=ControlMode.PUSH_WAYPOINT,
                       task_instruction_template="Push.", workspace_bounds=WorkspaceBounds())


def _import_push_collect(monkeypatch):
    """push_collect imports wp1_target_gate → isaaclab → pxr (Kit only). Stub
    the three geometry helpers it uses; the loop wiring is what is tested."""
    import importlib
    import types
    import torch
    gate = "aiongenos.tasks.WP1_contact_testbed.wp1_target_gate"
    try:
        importlib.import_module(gate)
    except Exception:
        stub = types.ModuleType(gate)
        stub.neutral_contact_orientation_b = lambda motion, prev_x_n=None: (
            torch.tensor([1.0, 0.0, 0.0, 0.0]), torch.tensor([1.0, 0.0, 0.0]))
        stub._euler_zyx_to_quat = lambda *a: torch.tensor([1.0, 0.0, 0.0, 0.0])
        stub._quat_mul = lambda q, r: q
        monkeypatch.setitem(sys.modules, gate, stub)
        monkeypatch.delitem(sys.modules, "aiongenos.orchestrator.push_collect", raising=False)
    return importlib.import_module("aiongenos.orchestrator.push_collect")


def _patch_stage1(monkeypatch, calls):
    pc = _import_push_collect(monkeypatch)

    def fake(lc, url, rgb, state, conversation=None, memory_preamble_text=None,
             memory_preamble_images_b64=None, **kw):
        calls.append((conversation is not None, memory_preamble_text))
        return _Parsed(), 10.0, None
    monkeypatch.setattr(pc, "run_stage1_eef", fake)
    return pc


def test_budget_guard_raises(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    with pytest.raises(RuntimeError, match="max_episode_length"):
        pc.run_push_collect_loop(_FakePushEnv(mel=720), _lc(), "u", ReplayBuffer(tmp_path), 1,
                                 steps_per_segment=90)


def test_loop_option_a_memory_r1_only_and_recap(tmp_path, monkeypatch):
    calls = []
    pc = _patch_stage1(monkeypatch, calls)
    buf = RecapBuffer(root=tmp_path / "recaps")
    img = tmp_path / "i.png"
    img.write_bytes(_png())
    buf.add(_rec("past", [0.40, 0.10, 0.48, 0.12], True, _unit(np.ones(DIM)), img))
    retr = pm.PushMemoryRetriever(buf, embed_fn=lambda _b: _unit(np.ones(DIM)))
    # fake teacher + embedder injected through a wrapper (defaults bound at def time)
    real_emit = pm.emit_push_recap
    monkeypatch.setattr(pm, "emit_push_recap", lambda **kw: real_emit(
        **kw, vlm_call=lambda **k: "Aimed behind. LESSON: aim behind the cube.",
        embed_fn=lambda _b: _unit(np.ones(DIM))))
    summ = pc.run_push_collect_loop(_FakePushEnv(), _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                                    env_seed_base=4700, recap_buffer=buf, memory_retriever=retr,
                                    dump_images_root=tmp_path / "dumps")
    assert calls[0][0] is True and "PAST SIMILAR PUSH EPISODES" in calls[0][1]
    assert all(c == (False, None) for c in calls[1:])           # rounds 2+ stateless
    ep = summ["episodes"][0]
    assert ep["outcome"] == "success" and ep["label"] == "pilot" and ep["memory_hits"][0]["ep_id"] == "past"
    assert ep["round_meta"][0]["memory_preamble"] is True and "cube_b_pre" in ep["round_meta"][0]
    run = summ["run_id"]
    dd = tmp_path / "dumps" / run / ep["ep_id"]
    assert (dd / "round_01_pre.png").exists() and (dd / "episode_end.png").exists() and (dd / "meta.json").exists()
    rj = json.loads(next((tmp_path / "rp" / run / "success").glob("*.json")).read_text())
    assert rj["env_seed"] == 4700 and rj["init_cube_pose"]["yellow"] == [0.40, 0.10, 0.02]
    assert rj["metadata"]["label"] == "pilot" and rj["metadata"]["memory_hits"][0]["ep_id"] == "past"
    assert len(buf) == 2                                          # new recap written


def test_loop_auto_reset_flags_and_ends(tmp_path, monkeypatch):
    calls = []
    pc = _patch_stage1(monkeypatch, calls)
    buf = RecapBuffer(root=tmp_path / "recaps")
    env = _FakePushEnv(reset_at_round=2)   # R1: 8.2→5.2 cm (no success), R2 resets
    summ = pc.run_push_collect_loop(env, _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                                    recap_buffer=buf, recap_buffer_readonly=False)
    ep = summ["episodes"][0]
    rj = json.loads(next((tmp_path / "rp" / summ["run_id"]).glob("*/*.json")).read_text())
    assert "env_auto_reset" in rj["flags"]
    assert ep["rounds"] == 1 and ep["outcome"] == "timeout"       # outcome unchanged, round 2 dropped
    assert len(buf) == 0                                          # no recap from a reset scene


def test_readonly_writes_no_recap(tmp_path, monkeypatch):
    pc = _patch_stage1(monkeypatch, [])
    buf = RecapBuffer(root=tmp_path / "recaps")
    pc.run_push_collect_loop(_FakePushEnv(), _lc(), "u", ReplayBuffer(tmp_path / "rp"), 1,
                             recap_buffer=buf, recap_buffer_readonly=True)
    assert len(buf) == 0
