import time

import pytest

from backend.engine import Engine
from backend.protocol import Message
from backend.storage import Store


@pytest.fixture
def engine():
    store = Store(":memory:")
    yield Engine(store)
    store.close()


def send(engine, kind, payload=None, source="ui", **kwargs):
    if source == "vision" and kind == "GESTURE_RECOGNIZED":
        payload = {"epoch": engine.state["session"]["gesture_epoch"], **(payload or {})}
    return engine.apply(Message(source=source, type=kind, payload=payload or {}, session_id=engine.state["session"]["id"], **kwargs))


def test_manual_journey_persists_and_users_are_isolated(engine):
    send(engine, "preview_profile", {"user_id": "DV-STUDENT-01"})
    send(engine, "select_tooth", {"tooth": 16})
    send(engine, "isolate")
    send(engine, "rotate", {"yaw": 30, "pitch": 10})
    send(engine, "tool", {"tool": "mirror"})
    send(engine, "move_tool", {"x": 0.5, "y": 0.3})
    send(engine, "place_tool")
    send(engine, "save_session", {"note": "A real interaction observation"})
    assert set(engine.state["session"]["checkpoints"]) == {"located", "inspected", "mirror_placed"}
    assert engine.snapshot()["journal"][0]["note"] == "A real interaction observation"
    send(engine, "preview_profile", {"user_id": "DV-STUDENT-02"})
    assert engine.snapshot()["journal"] == []
    send(engine, "preview_profile", {"user_id": "DV-STUDENT-01"})
    assert len(engine.snapshot()["journal"]) == 1


def test_context_content_changes_by_identity_layer_and_tool(engine):
    beginner = engine.snapshot()["content"]
    send(engine, "preview_profile", {"user_id": "DV-TEACHER-01"})
    assert beginner["prompts"] != engine.snapshot()["content"]["prompts"]
    send(engine, "select_tooth", {"tooth": 16})
    send(engine, "isolate")
    send(engine, "layer", {"layer": "pulp"})
    assert engine.snapshot()["content"]["layer_title"] == "Pulp"
    send(engine, "tool", {"tool": "mirror"})
    assert "virtual mirror" in engine.snapshot()["content"]["tool_help"]


def test_ble_identity_switch_requires_explicit_confirmation(engine):
    send(engine, "select_tooth", {"tooth": 16})
    send(engine, "USER_IDENTIFIED", {"user_id": "DV-STUDENT-02"}, source="bluetooth")
    assert engine.state["profile"]["id"] == "guest"
    assert engine.state["pending_identity"]["id"] == "DV-STUDENT-02"
    send(engine, "confirm_identity", {"discard": True})
    assert engine.state["identity_source"] == "bluetooth"


def test_duplicate_old_and_wrong_session_commands_are_rejected(engine):
    msg = Message(source="ui", type="pause", session_id=engine.state["session"]["id"])
    assert engine.apply(msg)["status"] == "applied"
    send(engine, "resume")
    assert engine.apply(msg)["status"] == "duplicate"
    assert not engine.state["session"]["paused"]
    with pytest.raises(ValueError, match="stale"):
        send(engine, "pause", timestamp=time.time() - 60)
    with pytest.raises(ValueError, match="Session changed"):
        engine.apply(Message(source="ui", type="pause", session_id="old-session"))


def test_tracking_loss_freezes_and_requires_resume(engine):
    engine.worker_status("vision", True)
    send(engine, "TRACKING_STATUS", {"status": "ready"}, source="vision")
    send(engine, "VISION_STATUS", {"calibrated": True}, source="vision")
    send(engine, "set_mode", {"mode": "gesture"})
    send(engine, "select_tooth", {"tooth": 16})
    send(engine, "GESTURE_RECOGNIZED", {"name": "V", "score": 0.9}, source="vision")
    send(engine, "TRACKING_STATUS", {"status": "lost"}, source="vision")
    with pytest.raises(ValueError, match="Resume"):
        send(engine, "rotate", {"yaw": 30, "pitch": 0})
    send(engine, "TRACKING_STATUS", {"status": "ready"}, source="vision")
    assert engine.state["session"]["paused"]
    send(engine, "resume")
    assert not engine.state["session"]["paused"]
    engine.worker_status("vision", False)
    assert engine.state["session"]["paused"]


def test_invalid_numbers_and_unknown_users_do_not_mutate_state(engine):
    send(engine, "select_tooth", {"tooth": 16})
    send(engine, "isolate")
    previous = engine.snapshot()
    with pytest.raises(ValueError):
        send(engine, "rotate", {"yaw": 40, "pitch": float("nan")})
    assert engine.snapshot() == previous
    with pytest.raises(ValueError, match="Unknown application"):
        send(engine, "USER_IDENTIFIED", {"user_id": "unregistered"}, source="bluetooth")
    assert engine.snapshot() == previous


def test_saved_session_survives_database_reopen(tmp_path):
    path = tmp_path / "sessions.db"
    first = Store(path)
    engine = Engine(first)
    send(engine, "save_session", {"note": "Retain after restart"})
    first.close()
    second = Store(path)
    assert second.journal("guest")[0]["note"] == "Retain after restart"
    second.close()


def test_gesture_captured_before_pause_cannot_execute_after_resume(engine):
    engine.worker_status("vision", True)
    send(engine, "TRACKING_STATUS", {"status": "ready"}, source="vision")
    send(engine, "VISION_STATUS", {"calibrated": True}, source="vision")
    send(engine, "set_mode", {"mode": "gesture"})
    old_epoch = engine.state["session"]["gesture_epoch"]
    send(engine, "pause")
    send(engine, "resume")
    with pytest.raises(ValueError, match="predates"):
        send(engine, "GESTURE_RECOGNIZED", {"name": "Z", "score": 0.9, "epoch": old_epoch}, source="vision")
    assert not engine.state["session"]["paused"]
