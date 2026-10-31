import copy
import base64
from pathlib import Path
from uuid import uuid4

import pytest

from backend.engine import Engine
from backend.protocol import Message
from backend.storage import Store


@pytest.fixture
def engine():
    store = Store(":memory:")
    yield Engine(store)
    store.close()


def send(engine, kind, payload=None, source="ui", **extra):
    return engine.apply(Message(source=source, type=kind, session_id=engine.state["session"]["id"], payload=payload or {}, **extra))


def prepare(engine):
    engine.worker_status("vision", True)
    send(engine, "TRACKING_STATUS", {"status": "ready"}, "vision")
    send(engine, "VISION_STATUS", {"calibrated": True}, "vision")


def test_pose_preview_is_ephemeral_not_history_or_workspace(engine):
    send(engine, "vision_hand", {"hand": "left"})
    before = copy.deepcopy(engine.state["events"])
    checkpoint = engine.store.load_workspace()
    image = {"data": base64.b64encode((Path(__file__).parent / "fixtures/preview-synthetic.jpg").read_bytes()).decode(), "width": 320, "height": 180}
    for _ in range(30):
        ack = send(engine, "POSE_FRAME", {"landmarks": [{"x": 0.5, "y": 0.3, "visibility": 1}] * 33, "image": image}, "vision")
        assert ack["status"] == "preview"
    assert len(engine.state["vision"]["pose"]["landmarks"]) == 33
    assert engine.state["events"] == before
    assert engine.store.load_workspace() == checkpoint
    send(engine, "vision_hand", {"hand": "right"})
    assert image["data"] not in str(engine.store.load_workspace())
    assert engine.state["vision"]["pose"]["image"] == image
    assert "pose" not in str(checkpoint)
    with pytest.raises(ValueError, match="another session"):
        engine.apply(Message(source="vision", type="POSE_FRAME", session_id=str(uuid4()), payload={"landmarks": []}))
    with pytest.raises(ValueError, match="finite"):
        send(engine, "POSE_FRAME", {"landmarks": [{"x": float("nan"), "y": 0, "visibility": 1}] * 33}, "vision")


def test_hand_and_calibration_changes_invalidate_old_gesture(engine):
    prepare(engine)
    send(engine, "set_mode", {"mode": "gesture"})
    old_epoch = engine.state["session"]["gesture_epoch"]
    send(engine, "vision_hand", {"hand": "left"})
    assert not engine.state["vision"]["calibrated"]
    assert engine.state["session"]["paused"]
    with pytest.raises(ValueError, match="predates"):
        send(engine, "GESTURE_RECOGNIZED", {"name": "Z", "score": 0.9, "epoch": old_epoch}, "vision")
    send(engine, "vision_calibrate", {"hand": "left"})
    assert engine.state["vision"]["calibration_status"] == "collecting"


def test_double_record_is_rejected_until_worker_reports_capture(engine):
    prepare(engine)
    send(engine, "template_record", {"name": "V"})
    with pytest.raises(ValueError, match="Finish or cancel"):
        send(engine, "template_record", {"name": "circle"})
    send(engine, "VISION_STATUS", {"capturing": True, "capture_name": "V"}, "vision")
    assert not engine.state["vision"]["pending_capture"]
    assert engine.state["vision"]["capture_name"] == "V"
    with pytest.raises(ValueError, match="Finish or cancel"):
        send(engine, "template_record", {"name": "circle"})


def test_stopping_vision_switches_to_manual_and_invalidates_readiness(engine):
    prepare(engine)
    send(engine, "set_mode", {"mode": "gesture"})
    send(engine, "vision_stop")
    assert engine.state["session"]["mode"] == "manual"
    assert not engine.state["vision"]["calibrated"]
    assert engine.state["services"]["vision"]["status"] == "stopping"
    engine.worker_status("vision", False)
    with pytest.raises(ValueError, match="camera index"):
        send(engine, "vision_start", {"camera": "0; arbitrary"})
