"""Synthetic geometry tests; these are not measured human recognition accuracy."""
import copy
import json
import math
from pathlib import Path

import pytest

from backend.hands import HandTracker, validate_hands, finger_features
from backend.engine import Engine
from backend.protocol import Message, encode_frame, MAX_FRAME
from backend.storage import Store

RAW = json.loads((Path(__file__).parent / "fixtures/hands-synthetic.json").read_text())
SIGNALS = json.loads((Path(__file__).parent / "fixtures/hand-signals-synthetic.json").read_text())


def detection(kind="open", side="right"):
    return {"handedness": side, "score": 0.99, "landmarks": copy.deepcopy(RAW[kind])}


@pytest.mark.parametrize("kind,expected", [("open","open_palm"),("fist","fist"),("pinch","pinch")])
def test_finger_geometry_and_time_debounce(kind, expected):
    tracker = HandTracker()
    assert tracker.update([detection(kind)], 0)[0]["gesture"] == "stabilizing"
    tracker.update([detection(kind)], 0.08)
    hand = tracker.update([detection(kind)], 0.16)[0]
    assert hand["gesture"] == expected
    assert hand["extended_fingers"] == sum(hand["fingers"].values())
    assert validate_hands([hand]) == [hand]


def test_two_hands_survive_detection_order_and_partial_loss_without_ghosts():
    tracker = HandTracker()
    left, right = detection(side="left"), detection(side="right")
    for p in left["landmarks"]:
        p["x"] *= 0.5
    for p in right["landmarks"]:
        p["x"] = p["x"] * 0.5 + 0.5
    first = tracker.update([left,right], 0)
    swapped = tracker.update([right,left], 0.1)
    assert [h["id"] for h in swapped] == ["left","right"]
    assert all(abs(h["motion"]["x"]) < 1e-5 for h in swapped)
    assert [h["id"] for h in tracker.update([right], 0.2)] == ["right"]
    assert tracker.update([], 0.3) == []
    reacquired = tracker.update([left,right], 0.4)
    assert all(h["gesture"] == "stabilizing" and h["motion"]["x"] == 0 for h in reacquired)
    assert len(first) == 2


def test_duplicate_handedness_does_not_drop_second_hand():
    tracker = HandTracker()
    first, second = detection(side="left"), detection(side="left")
    for p in first["landmarks"]:
        p["x"] *= 0.5
    for p in second["landmarks"]:
        p["x"] = p["x"] * 0.5 + 0.5
    hands = tracker.update([first,second], 0)
    assert len(hands) == 2 and {h["id"] for h in hands} == {"left","right"}


def test_weak_handedness_flip_does_not_rename_an_existing_hand():
    tracker = HandTracker()
    tracker.update([detection(side="right")],0)
    uncertain = detection(side="left")
    uncertain["score"] = 0.51
    assert tracker.update([uncertain],0.1)[0]["id"] == "right"


def test_partial_hand_cannot_keep_a_previous_stable_pinch():
    tracker = HandTracker()
    for now in (0,0.08,0.16):
        hand = tracker.update([detection("pinch")],now)[0]
    assert hand["gesture"] == "pinch"
    partial = detection("pinch")
    partial["landmarks"][8]["x"] = -0.1
    hand = tracker.update([partial], 0.24)[0]
    assert not hand["in_frame"] and hand["gesture"] == "partial"


def test_fist_releases_pinch_and_roll_movement_is_available_for_bindings():
    tracker = HandTracker()
    for now in (0,0.08,0.16):
        tracker.update([detection("pinch")],now)
    for now in (0.24,0.32,0.4):
        hand = tracker.update([detection("fist")],now)[0]
    assert hand["gesture"] == "fist"
    start = detection()
    for p in start["landmarks"]:
        p["x"], p["y"] = (p["x"]-.5)*.5+.5, (p["y"]-.5)*.5+.5
    rotated = copy.deepcopy(start)
    for p in rotated["landmarks"]:
        p["x"], p["y"] = 1-p["y"], p["x"]
    tracker = HandTracker()
    tracker.update([start],0)
    hand = tracker.update([rotated],0.2)[0]
    assert abs(hand["motion"]["roll"]) > 20


def test_world_geometry_keeps_finger_features_under_3d_rotation():
    geometry = [(p["x"],p["y"],p["z"]) for p in RAW["open"]]
    rotated = [(z,y,-x) for x,y,z in geometry]
    assert finger_features(geometry)[0] == finger_features(rotated)[0]


def test_open_fingers_allow_natural_joint_bend_and_depth_estimation_noise():
    geometry = [(p["x"],p["y"],p["z"]) for p in RAW["open"]]
    geometry[8] = (*geometry[8][:2], 0.11)
    geometry[11] = (*geometry[11][:2], 0.1)
    geometry[12] = (*geometry[12][:2], 0.18)
    states, _ = finger_features(geometry)
    assert states["index"] and states["middle"]


def test_hands_and_full_video_stay_within_transport_and_out_of_storage():
    image = {"data": "/9j/" + "A" * 41992 + "/9k=", "width": 640, "height": 480}
    payload = {"image": image, "hands": SIGNALS["open"], "hand_tracking": True,
        "landmarks": [{"x": .12345678901234567, "y": .8765432109876543, "visibility": .9876543210987654}] * 33,
        "trail": [[.12345678901234567,.8765432109876543]] * 200}
    message = Message(source="vision",type="POSE_FRAME",payload=payload)
    assert len(encode_frame(message))-4 < MAX_FRAME
    store = Store(":memory:")
    engine = Engine(store)
    message.session_id = engine.state["session"]["id"]
    engine.apply(message)
    engine.checkpoint()
    assert engine.state["vision"]["pose"]["hands"] == SIGNALS["open"]
    assert "hands" not in str(store.load_workspace())
    store.close()


@pytest.mark.parametrize("fault", ["missing_point","duplicate_side","nan"])
def test_invalid_hand_packets_are_rejected(fault):
    hands = copy.deepcopy(SIGNALS["open"])
    if fault == "missing_point":
        hands[0]["landmarks"].pop()
    elif fault == "duplicate_side":
        hands[1]["id"] = hands[0]["id"]
    else:
        hands[0]["landmarks"][0]["x"] = math.nan
    with pytest.raises(ValueError):
        validate_hands(hands)
