"""Synthetic sensor signals exercise actual authoritative scene bindings."""
import copy
import json
import time
from pathlib import Path

import pytest

from backend.engine import Engine
from backend.protocol import Message
from backend.storage import Store

SIGNALS = json.loads((Path(__file__).parent / "fixtures/hand-signals-synthetic.json").read_text())


def hand(side="right", pose="open", x=0.7, y=0.5, roll=0):
    value = copy.deepcopy(next(h for h in SIGNALS[pose] if h["id"] == side))
    dx,dy = x-value["center"]["x"], y-value["center"]["y"]
    value["center"] = {"x": x, "y": y}
    value["roll"] = roll
    for p in value["landmarks"]:
        p["x"] += dx
        p["y"] += dy
    return value


def send(engine, action, payload=None, source="ui"):
    return engine.apply(Message(source=source,type=action,payload=payload or {},session_id=engine.state["session"]["id"]))


def frame(engine, hands, epoch=None, timestamp=None):
    return engine.apply(Message(source="vision",type="POSE_FRAME",session_id=engine.state["session"]["id"],timestamp=time.time()-0.01 if timestamp is None else timestamp,
        payload={"landmarks": [], "hands": hands, "hand_tracking": True, "control_epoch": engine.state["session"]["gesture_epoch"] if epoch is None else epoch}))


@pytest.fixture
def engine():
    store = Store(":memory:")
    engine = Engine(store)
    send(engine,"select_tooth",{"tooth":16})
    send(engine,"isolate")
    engine.worker_status("vision",True)
    frame(engine,[hand()])
    send(engine,"set_mode",{"mode":"hand"})
    send(engine,"hand_response",{"value":1})
    yield engine
    store.close()


def test_fist_grab_rotates_without_jumping_and_release_persists(engine):
    frame(engine,[hand(pose="fist",x=.8)])
    assert engine.state["session"]["rotation"] == {"yaw":0,"pitch":0,"roll":0}
    frame(engine,[hand()])
    frame(engine,[hand(pose="fist")])
    assert engine.state["session"]["rotation"]["yaw"] == 0
    frame(engine,[hand(pose="fist",x=.8,y=.55,roll=20)])
    moved = copy.deepcopy(engine.state["session"]["rotation"])
    assert moved["yaw"] > 25 and moved["pitch"] > 0
    frame(engine,[hand(x=.8)])
    assert engine.store.load_workspace()["session"]["rotation"] == moved
    assert engine.snapshot()["journal"] == []
    assert "inspected" in engine.state["session"]["checkpoints"]


def test_open_hand_can_arm_when_natural_finger_bend_has_a_neutral_label(engine):
    opened = hand()
    opened["gesture"] = "neutral"
    opened["fingers"].update(thumb=False,pinky=False)
    opened["extended_fingers"] = 3
    frame(engine,[opened])
    assert engine.state["hand_control"]["phase"] == "ready"
    frame(engine,[hand(pose="fist")]); frame(engine,[hand(pose="fist",x=.8)])
    assert engine.state["session"]["rotation"]["yaw"] > 10


def test_one_open_hand_can_take_control_while_other_hand_is_already_closed(engine):
    frame(engine,[hand("left","fist",x=.3),hand("right","open",x=.7)])
    assert engine.state["hand_control"]["phase"] == "ready"
    frame(engine,[hand("left","fist",x=.3),hand("right","fist",x=.7)])
    frame(engine,[hand("left","fist",x=.2),hand("right","fist",x=.8)])
    assert engine.state["session"]["rotation"]["yaw"] > 10
    assert engine.state["hand_control"]["hands"] == ["right"]


def test_pinch_moves_instrument_and_hand_tool_pinch_rotates(engine):
    frame(engine,[hand()])
    frame(engine,[hand(pose="pinch")])
    frame(engine,[hand(pose="pinch",x=.8)])
    assert engine.state["session"]["rotation"]["yaw"] > 10
    send(engine,"tool",{"tool":"mirror"})
    rotation = copy.deepcopy(engine.state["session"]["rotation"])
    frame(engine,[hand()])
    frame(engine,[hand(pose="pinch")])
    frame(engine,[hand(pose="pinch",x=.8,y=.6)])
    assert engine.state["session"]["tool_position"]["x"] > .9
    assert engine.state["session"]["tool_position"]["y"] < -.2
    assert engine.state["session"]["rotation"] == rotation


def test_two_pinch_zoom_has_priority_and_does_not_fall_into_instrument_drag(engine):
    frame(engine,[hand("left",x=.3),hand("right",x=.7)])
    frame(engine,[hand("left","pinch",x=.3),hand("right","pinch",x=.7)])
    frame(engine,[hand("right","pinch",x=.8),hand("left","pinch",x=.2)])
    assert 1.4 < engine.state["session"]["zoom"] < 1.6
    assert engine.state["session"]["tool_position"] == {"x":.7,"y":0,"z":0}
    before = copy.deepcopy(engine.state["session"])
    frame(engine,[hand("left",x=.2),hand("right","pinch",x=.8)])
    frame(engine,[hand("left",x=.2),hand("right","pinch",x=.9)])
    assert engine.state["session"]["tool_position"] == before["tool_position"]
    assert engine.state["session"]["zoom"] == before["zoom"]


def test_hand_loss_and_reentry_with_held_grip_require_open_palm(engine):
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")])
    frame(engine,[hand(pose="fist",x=.8)])
    rotation = copy.deepcopy(engine.state["session"]["rotation"])
    frame(engine,[])
    frame(engine,[hand(pose="fist",x=.3)])
    frame(engine,[hand(pose="fist",x=.4)])
    assert engine.state["session"]["rotation"] == rotation
    frame(engine,[hand(x=.4)])
    frame(engine,[hand(pose="fist",x=.4)])
    assert engine.state["session"]["rotation"] == rotation
    frame(engine,[hand(pose="fist",x=.5)])
    assert engine.state["session"]["rotation"]["yaw"] > rotation["yaw"]


def test_raw_finger_release_stops_motion_before_pose_label_debounce(engine):
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")]); frame(engine,[hand(pose="fist",x=.8)])
    retained = copy.deepcopy(engine.state["session"]["rotation"])
    opening = hand(pose="open",x=.9)
    opening["gesture"] = "fist"  # The old stable label can last another 0.12 seconds.
    frame(engine,[opening])
    assert engine.state["session"]["rotation"] == retained
    assert engine.state["hand_control"]["phase"] == "release"


def test_pause_reset_and_old_epoch_never_replay_a_grab(engine):
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")])
    epoch = engine.state["session"]["gesture_epoch"]
    send(engine,"pause")
    frame(engine,[hand(pose="fist",x=.8)])
    assert engine.state["session"]["rotation"]["yaw"] == 0
    send(engine,"resume")
    frame(engine,[hand(),hand("left",x=.3)],epoch=epoch)
    frame(engine,[hand(pose="fist",x=.8)])
    assert engine.state["session"]["rotation"]["yaw"] == 0
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")]); frame(engine,[hand(pose="fist",x=.8)])
    send(engine,"reset",{"confirm":True})
    frame(engine,[hand(pose="fist",x=.9)])
    assert engine.state["session"]["rotation"] == {"yaw":0,"pitch":0,"roll":0}


def test_stale_video_pauses_and_body_visibility_does_not_gate_hands(engine,monkeypatch):
    send(engine,"TRACKING_STATUS",{"status":"lost"},source="vision")
    assert not engine.state["session"]["paused"]
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")]); frame(engine,[hand(pose="fist",x=.8)])
    now = time.time()
    with monkeypatch.context() as patch:
        patch.setattr("backend.engine.time.time",lambda:now+2)
        assert engine.expire_hand_tracking()
    assert engine.state["session"]["paused"]
    assert engine.state["hand_control"]["phase"] == "paused"
    frame(engine,[hand(pose="fist",x=.3)])
    retained = copy.deepcopy(engine.state["session"]["rotation"])
    send(engine,"resume")
    frame(engine,[hand(pose="fist",x=.9)])
    assert engine.state["session"]["rotation"] == retained


def test_manual_mode_and_other_screens_ignore_hand_motion(engine):
    send(engine,"set_mode",{"mode":"manual"})
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")]); frame(engine,[hand(pose="fist",x=.8)])
    assert engine.state["session"]["rotation"]["yaw"] == 0
    send(engine,"set_mode",{"mode":"hand"})
    send(engine,"navigate",{"screen":"review"})
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")]); frame(engine,[hand(pose="fist",x=.8)])
    assert engine.state["session"]["rotation"]["yaw"] == 0


def test_duplicate_and_out_of_order_frames_cannot_change_scene(engine):
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")])
    previous = engine.state["vision"]["pose"]["timestamp"]
    assert frame(engine,[hand(pose="fist",x=.8)],timestamp=previous-.1)["status"] == "preview_stale"
    assert engine.state["session"]["rotation"]["yaw"] == 0
    event = Message(source="vision",type="POSE_FRAME",session_id=engine.state["session"]["id"],payload={"landmarks":[],"hands":[hand(pose="fist",x=.8)],"hand_tracking":True,"control_epoch":engine.state["session"]["gesture_epoch"]})
    engine.apply(event)
    retained = copy.deepcopy(engine.state["session"]["rotation"])
    assert engine.apply(event)["status"] == "preview_stale"
    assert engine.state["session"]["rotation"] == retained


def test_worker_loss_flushes_and_restart_restores_paused_hand_mode(engine):
    frame(engine,[hand()]); frame(engine,[hand(pose="fist")]); frame(engine,[hand(pose="fist",x=.8)])
    retained = copy.deepcopy(engine.state["session"]["rotation"])
    engine.worker_status("vision",False)
    assert engine.state["session"]["paused"]
    restored = Engine(engine.store)
    assert restored.state["session"]["rotation"] == retained
    assert restored.state["session"]["paused"] and restored.state["session"]["mode"] == "hand"
    assert restored.state["vision"]["pose"] is None


def test_both_hands_move_independent_targets_in_the_same_frame(engine):
    send(engine,"tool",{"tool":"mirror"})
    frame(engine,[hand("left",x=.3),hand("right",x=.7)])
    frame(engine,[hand("right","pinch",x=.7),hand("left","fist",x=.3)])
    frame(engine,[hand("left","fist",x=.4,y=.56,roll=25),hand("right","pinch",x=.65,y=.56,roll=-20)])
    s = engine.state["session"]
    assert s["rotation"]["yaw"] > 35 and s["rotation"]["pitch"] > 15 and s["rotation"]["roll"] > 15
    assert s["tool_position"]["x"] < .6 and s["tool_position"]["y"] < -.15
    assert s["tool_rotation"]["roll"] < -15
    assert engine.state["hand_control"]["phase"] == "bimanual"
    assert engine.state["hand_control"]["hands"] == ["left","right"]


def test_two_pinches_override_both_targets_for_span_zoom(engine):
    send(engine,"tool",{"tool":"explorer"})
    frame(engine,[hand("left",x=.3),hand("right")])
    frame(engine,[hand("left","fist",x=.3),hand("right","pinch")])
    frame(engine,[hand("left","fist",x=.35),hand("right","pinch",x=.75)])
    retained=copy.deepcopy(engine.state["session"])
    frame(engine,[hand("left","pinch",x=.35),hand("right","pinch",x=.75)])
    assert engine.state["hand_control"]["phase"] == "zooming"
    frame(engine,[hand("left","pinch",x=.2),hand("right","pinch",x=.9)])
    assert engine.state["session"]["zoom"] > 1.6
    assert engine.state["session"]["rotation"] == retained["rotation"]
    assert engine.state["session"]["tool_position"] == retained["tool_position"]
    frame(engine,[hand("left","pinch",x=.4),hand("right","pinch",x=.6)])
    assert engine.state["session"]["zoom"] < .7
    frame(engine,[hand("left",x=.4),hand("right","pinch",x=.6)])
    frame(engine,[hand("left",x=.4),hand("right","pinch",x=.8)])
    assert engine.state["session"]["tool_position"] == retained["tool_position"]
    assert engine.state["hand_control"]["phase"] == "release"


def test_left_depth_never_zooms_while_right_depth_moves_instrument(engine):
    send(engine,"tool",{"tool":"mirror"})
    left, right = hand("left",x=.3), hand("right")
    frame(engine,[left,right])
    left, right = hand("left","fist",x=.3), hand("right","pinch")
    left["palm_span"] = right["palm_span"] = .12
    frame(engine,[left,right])
    left["palm_span"],right["palm_span"] = .18,.08
    frame(engine,[left,right])
    assert engine.state["session"]["zoom"] == 1
    assert engine.state["session"]["tool_position"]["z"] < -.5


def test_left_pinch_alone_does_not_zoom_or_rotate(engine):
    send(engine,"tool",{"tool":"mirror"})
    frame(engine,[hand("left",x=.3)])
    frame(engine,[hand("left","pinch",x=.3)])
    frame(engine,[hand("left","pinch",x=.4,y=.35,roll=25)])
    assert engine.state["session"]["zoom"] == 1
    assert engine.state["session"]["rotation"] == {"yaw":0,"pitch":0,"roll":0}


def test_calm_sensitivity_reduces_gain_and_changes_require_rearm(engine):
    assert Engine(Store(":memory:")).state["session"]["hand_response"] == .55
    send(engine,"hand_response",{"value":.5})
    frame(engine,[hand()]);frame(engine,[hand(pose="fist")]);frame(engine,[hand(pose="fist",x=.8)])
    assert 18 < engine.state["session"]["rotation"]["yaw"] < 23
    before=copy.deepcopy(engine.state["session"]["rotation"])
    send(engine,"hand_response",{"value":.25})
    frame(engine,[hand(pose="fist",x=.9)])
    assert engine.state["session"]["rotation"] == before
    assert Engine(engine.store).state["session"]["hand_response"] == .25
    with pytest.raises(ValueError):send(engine,"hand_response",{"value":0})


def test_losing_right_hand_does_not_stop_left_and_reentry_needs_release(engine):
    send(engine,"tool",{"tool":"mirror"})
    frame(engine,[hand("left",x=.3),hand("right")])
    frame(engine,[hand("left","fist",x=.3),hand("right","fist")])
    frame(engine,[hand("left","fist",x=.4),hand("right","fist",x=.75)])
    p = copy.deepcopy(engine.state["session"]["tool_position"])
    frame(engine,[hand("left","fist",x=.45)])
    r = copy.deepcopy(engine.state["session"]["rotation"])
    frame(engine,[hand("left","fist",x=.5),hand("right","fist",x=.3)])
    frame(engine,[hand("left","fist",x=.55),hand("right","fist",x=.4)])
    assert engine.state["session"]["tool_position"] == p
    assert engine.state["session"]["rotation"]["yaw"] > r["yaw"]
    frame(engine,[hand("left","fist",x=.55),hand("right",x=.4)])
    frame(engine,[hand("left","fist",x=.55),hand("right","fist",x=.4)])
    assert engine.state["session"]["tool_position"] == p
    frame(engine,[hand("left","fist",x=.55),hand("right","fist",x=.5)])
    assert engine.state["session"]["tool_position"]["x"] > p["x"]


def test_switching_tools_cannot_reuse_held_grabs(engine):
    send(engine,"tool",{"tool":"mirror"})
    frame(engine,[hand("left",x=.3),hand("right")])
    frame(engine,[hand("left","fist",x=.3),hand("right","pinch")])
    frame(engine,[hand("left","fist",x=.4),hand("right","pinch",x=.8)])
    send(engine,"tool",{"tool":"explorer"})
    s = copy.deepcopy(engine.state["session"])
    frame(engine,[hand("left","fist",x=.6),hand("right","pinch",x=.6)])
    assert engine.state["session"]["rotation"] == s["rotation"]
    assert engine.state["session"]["tool_position"] == s["tool_position"]


def test_xyz_orientation_persist_and_legacy_2d_checkpoint_migrates(engine):
    send(engine,"tool",{"tool":"mirror"})
    send(engine,"move_tool",{"x":.2,"y":-.1,"z":-.35,"yaw":30,"pitch":-20,"roll":45})
    send(engine,"rotate",{"yaw":12,"pitch":23,"roll":34})
    restored=Engine(engine.store)
    assert restored.state["session"]["tool_position"] == {"x":.2,"y":-.1,"z":-.35}
    assert restored.state["session"]["tool_rotation"] == {"yaw":30,"pitch":-20,"roll":45}
    assert restored.state["session"]["rotation"]["roll"] == 34
    legacy=copy.deepcopy(engine.state["session"])
    legacy["rotation"].pop("roll"); legacy["tool_position"].pop("z"); legacy.pop("tool_rotation")
    engine.store.save_workspace("guest",legacy,"right")
    restored=Engine(engine.store)
    assert restored.state["session"]["id"] == legacy["id"]
    assert restored.state["session"]["rotation"]["roll"] == 0
    assert restored.state["session"]["tool_position"]["z"] == 0


@pytest.mark.parametrize("payload",[{"z":2},{"z":float("nan")},{"yaw":True},{"pitch":181},{"roll":-181}])
def test_invalid_tool_depth_or_angles_are_transactionally_rejected(engine,payload):
    send(engine,"tool",{"tool":"mirror"})
    retained=copy.deepcopy(engine.state["session"])
    with pytest.raises(ValueError):
        send(engine,"move_tool",{"x":.4,**payload})
    assert engine.state["session"] == retained
