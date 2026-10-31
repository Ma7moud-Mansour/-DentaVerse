import copy

import pytest

from backend.engine import Engine
from backend.protocol import Message
from backend.storage import Store


def action(engine, name, payload=None):
    engine.apply(Message(source="ui", type=name, payload=payload or {}, session_id=engine.state["session"]["id"]))


def test_unsaved_scene_and_note_survive_coordinator_restart(tmp_path):
    path = tmp_path / "workspace.db"
    store = Store(path)
    first = Engine(store)
    action(first, "preview_profile", {"user_id": "DV-STUDENT-02"})
    action(first, "select_tooth", {"tooth": 16})
    action(first, "isolate")
    action(first, "rotate", {"yaw": 67, "pitch": -13})
    action(first, "layer", {"layer": "dentin"})
    action(first, "tool", {"tool": "mirror"})
    action(first, "move_tool", {"x": -0.2, "y": 0.4})
    action(first, "edit_note", {"note": "An unsaved observation"})
    expected = copy.deepcopy(first.state["session"])
    store.close()
    second_store = Store(path)
    second = Engine(second_store)
    actual = second.state["session"]
    assert actual == {**expected, "gesture_epoch": expected["gesture_epoch"] + 1}
    assert second.state["profile"]["id"] == "DV-STUDENT-02"
    assert second.state["identity_source"] == "restored_session"
    assert second.snapshot()["journal"] == []  # Draft recovery never manufactures a saved journal entry.
    second_store.close()


def test_gesture_restart_does_not_restore_sensor_readiness(tmp_path):
    store = Store(tmp_path / "workspace.db")
    first = Engine(store)
    first.state["session"]["mode"] = "gesture"
    first.state["tracking"] = "ready"
    first.state["vision"]["calibrated"] = True
    first.state["workers"]["vision"] = True
    first.checkpoint()
    second = Engine(store)
    assert second.state["session"]["paused"]
    assert second.state["session"]["pause_reason"] == "tracking"
    assert second.state["tracking"] == "offline"
    assert not second.state["vision"]["calibrated"]
    assert not second.state["workers"]["vision"]
    assert set(store.load_workspace()) == {"version", "profile_id", "session", "hand"}
    store.close()


@pytest.mark.parametrize("change", [{"zoom": float("nan")}, {"selected_tooth": True}, {"tool": "unknown"}, {"id": "not-a-session"}])
def test_invalid_checkpoint_falls_back_without_losing_saved_journal(tmp_path, change):
    store = Store(tmp_path / "workspace.db")
    first = Engine(store)
    action(first, "save_session", {"note": "Keep this journal entry"})
    saved = {**first.state["session"], **change}
    # JSON itself excludes NaN; corrupt persisted text can still be inspected safely.
    import json
    store.db.execute("UPDATE workspace SET data=? WHERE id=1", (json.dumps({"version": 1, "profile_id": "guest", "session": saved}),))
    store.db.commit()
    second = Engine(store)
    assert second.state["session"]["id"] != first.state["session"]["id"]
    assert second.snapshot()["journal"][0]["note"] == "Keep this journal entry"
    store.close()
