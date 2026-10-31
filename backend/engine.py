import copy
import math
from collections import deque
from uuid import uuid4

from backend.context import LAYERS, content_for
from backend.protocol import Message, check_fresh
from backend.storage import PROFILES, Store


def new_session() -> dict:
    return {"id": str(uuid4()), "screen": "studio", "selected_tooth": None, "isolated": False,
        "rotation": {"yaw": 0.0, "pitch": 0.0}, "zoom": 1.0, "layer": "surface", "tool": "hand",
        "tool_position": {"x": 0.7, "y": 0.0}, "checkpoints": [], "paused": False,
        "pause_reason": None, "mode": "manual", "gesture_epoch": 0, "note": "", "saved": False}


def number(value, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"Expected a finite number between {lower} and {upper}")
    return float(value)


class Engine:
    def __init__(self, store: Store):
        self.store = store
        self.state = {"profile": copy.deepcopy(PROFILES["guest"]), "identity_source": "manual_guest",
            "pending_identity": None, "session": new_session(), "tracking": "offline",
            "workers": {"vision": False, "bluetooth": False}, "bluetooth": {"status": "offline", "devices": [], "error": None},
            "vision": {"calibrated": False, "dominant_hand": "right", "capturing": False, "template_counts": {}, "error": None},
            "last_gesture": None, "events": []}
        self.seen: set[str] = set()
        self.order: deque[str] = deque()

    def snapshot(self) -> dict:
        return {**copy.deepcopy(self.state), "content": content_for(self.state), "journal": self.store.journal(self.state["profile"]["id"])}

    def worker_status(self, source: str, connected: bool):
        self.state["workers"][source] = connected
        if source == "vision" and not connected:
            self.state["tracking"] = "offline"
            self.state["vision"]["calibrated"] = False
            self.state["vision"]["capturing"] = False
            if self.state["session"]["mode"] == "gesture":
                self._pause("tracking")
        elif source == "bluetooth" and not connected:
            self.state["bluetooth"]["status"] = "offline"

    def _pause(self, reason: str):
        self.state["session"].update(paused=True, pause_reason=reason)
        self.state["session"]["gesture_epoch"] += 1
        self.state["vision"]["capturing"] = False

    def _checkpoint(self, name: str):
        points = self.state["session"]["checkpoints"]
        if name not in points:
            points.append(name)

    def _switch(self, user_id: str, source: str):
        if user_id not in PROFILES:
            raise ValueError("Unknown application UserID; register a profile before connecting")
        self.state["profile"] = copy.deepcopy(PROFILES[user_id])
        self.state["identity_source"] = source
        self.state["pending_identity"] = None
        self.state["session"] = new_session()

    def _identify(self, user_id: str, source: str):
        if user_id not in PROFILES or user_id == "guest":
            raise ValueError("Unknown application UserID")
        if user_id == self.state["profile"]["id"]:
            self.state["identity_source"] = source
            return
        session = self.state["session"]
        if session["selected_tooth"] is not None and not session["saved"]:
            self.state["pending_identity"] = {"id": user_id, "source": source}
        else:
            self._switch(user_id, source)

    def apply(self, message: Message) -> dict:
        check_fresh(message)
        if message.event_id in self.seen:
            return {"type": "ack", "event_id": message.event_id, "status": "duplicate"}
        session = self.state["session"]
        if message.source == "ui" and message.session_id != session["id"]:
            raise ValueError("Session changed; refresh before sending another action")
        if message.source == "vision" and message.type in {"GESTURE_RECOGNIZED", "GESTURE_REJECTED"} and message.session_id != session["id"]:
            raise ValueError("Gesture belongs to a different session")
        if message.source == "bluetooth" and message.type == "USER_IDENTIFIED" and message.session_id != session["id"]:
            raise ValueError("Identity read belongs to a previous workspace; reconnect the peripheral")
        # Reject failed actions transactionally, including partial nested changes.
        previous = copy.deepcopy(self.state)
        try:
            if message.source == "ui":
                self._action(message.type, message.payload)
            elif message.source == "vision":
                self._vision(message)
            elif message.source == "bluetooth":
                self._bluetooth(message.type, message.payload)
            else:
                raise ValueError("Unsupported event source")
        except (ValueError, KeyError, TypeError):
            self.state = previous
            raise
        self.seen.add(message.event_id)
        self.order.append(message.event_id)
        if len(self.order) > 2048:
            self.seen.remove(self.order.popleft())
        self.state["events"] = ([{"id": message.event_id, "source": message.source, "type": message.type, "timestamp": message.timestamp}] + self.state["events"])[:20]
        return {"type": "ack", "event_id": message.event_id, "status": "applied"}

    def _action(self, action: str, payload: dict):
        s = self.state["session"]
        manipulation = {"select_tooth", "isolate", "rotate", "zoom", "layer", "tool", "move_tool", "place_tool"}
        if action in manipulation and s["paused"]:
            raise ValueError("Resume the retained scene before manipulating it")
        if action == "navigate":
            screen = payload.get("screen")
            if screen not in {"studio", "atlas", "setup", "workbench", "review", "journal", "guide", "preferences"}:
                raise ValueError("Unknown screen")
            s["screen"] = screen
        elif action == "select_tooth":
            if payload.get("tooth") != 16:
                raise ValueError("This delivery contains the FDI 16 activity only")
            s["selected_tooth"] = 16
        elif action == "isolate":
            if s["selected_tooth"] != 16:
                raise ValueError("Select tooth 16 first")
            s.update(isolated=True, screen="workbench", saved=False)
            self._checkpoint("located")
        elif action in {"rotate", "zoom", "layer", "tool", "move_tool", "place_tool"}:
            if not s["isolated"]:
                raise ValueError("Isolate the specimen first")
            if action == "rotate":
                s["rotation"] = {"yaw": number(payload.get("yaw"), -180, 180), "pitch": number(payload.get("pitch"), -80, 80)}
                if abs(s["rotation"]["yaw"]) + abs(s["rotation"]["pitch"]) > 5:
                    self._checkpoint("inspected")
            elif action == "zoom":
                s["zoom"] = number(payload.get("value"), 0.6, 1.8)
            elif action == "layer":
                if payload.get("layer") not in LAYERS:
                    raise ValueError("Unknown tissue layer")
                s["layer"] = payload["layer"]
            elif action == "tool":
                if payload.get("tool") not in {"hand", "mirror", "explorer"}:
                    raise ValueError("Unknown tool")
                s["tool"] = payload["tool"]
            elif action == "move_tool":
                if s["tool"] == "hand":
                    raise ValueError("Choose an instrument first")
                s["tool_position"] = {"x": number(payload.get("x"), -1, 1), "y": number(payload.get("y"), -1, 1)}
            elif action == "place_tool":
                if s["tool"] != "mirror":
                    raise ValueError("The activity asks you to place the mirror")
                self._checkpoint("mirror_placed")
            s["saved"] = False
        elif action == "reset":
            if payload.get("confirm") is not True:
                raise ValueError("Confirm before resetting the view")
            s.update(rotation={"yaw": 0.0, "pitch": 0.0}, zoom=1.0, tool_position={"x": 0.7, "y": 0.0})
        elif action == "pause":
            self._pause("manual")
        elif action == "resume":
            if s["mode"] == "gesture" and (self.state["tracking"] != "ready" or not self.state["vision"]["calibrated"] or not self.state["workers"]["vision"]):
                raise ValueError("Restore calibrated tracking before resuming, or choose manual mode")
            s.update(paused=False, pause_reason=None)
            s["gesture_epoch"] += 1
        elif action == "set_mode":
            mode = payload.get("mode")
            if mode not in {"manual", "gesture"}:
                raise ValueError("Unknown input mode")
            if mode == "gesture" and (self.state["tracking"] != "ready" or not self.state["vision"]["calibrated"] or not self.state["workers"]["vision"]):
                raise ValueError("Connect the camera worker and complete calibration first")
            s["mode"] = mode
            s["gesture_epoch"] += 1
        elif action == "save_session":
            note = payload.get("note", "")
            if not isinstance(note, str) or len(note) > 4000:
                raise ValueError("Reflection must be text of at most 4000 characters")
            s["note"] = note
            s["saved"] = True
            self.store.save(s, self.state["profile"]["id"], note)
        elif action == "new_session":
            if s["selected_tooth"] is not None and not s["saved"] and payload.get("discard") is not True:
                raise ValueError("Save the current session or confirm discarding it")
            self.state["session"] = new_session()
        elif action == "preview_profile":
            self._identify(payload.get("user_id"), "manual_preview")
        elif action == "confirm_identity":
            pending = self.state["pending_identity"]
            if not pending or payload.get("discard") is not True:
                raise ValueError("Explicitly confirm switching away from the current session")
            self._switch(pending["id"], pending["source"])
        elif action == "cancel_identity":
            self.state["pending_identity"] = None
        elif action in {"ble_scan", "ble_connect", "ble_disconnect"}:
            if not self.state["workers"]["bluetooth"]:
                raise ValueError("Start the Bluetooth worker first")
            if action == "ble_connect" and payload.get("device_id") not in {d["id"] for d in self.state["bluetooth"]["devices"]}:
                raise ValueError("Choose a device from the latest project-service scan")
        elif action in {"vision_calibrate", "capture_start", "capture_stop", "capture_cancel", "template_record"}:
            if not self.state["workers"]["vision"]:
                raise ValueError("Start the vision worker first")
            if action == "vision_calibrate" and payload.get("hand", "right") not in {"left", "right"}:
                raise ValueError("Choose left or right hand")
            if action in {"capture_start", "template_record"}:
                if self.state["tracking"] != "ready" or not self.state["vision"]["calibrated"]:
                    raise ValueError("Calibrate visible shoulder and wrist before recording")
                if action == "capture_start" and (s["mode"] != "gesture" or s["paused"]):
                    raise ValueError("Enable gesture mode and resume before recording")
            if action == "template_record" and payload.get("name") not in {"V", "circle", "Z"}:
                raise ValueError("Choose V, circle or Z for the template")
        else:
            raise ValueError("Unknown action")

    def _vision(self, message: Message):
        p, kind, s = message.payload, message.type, self.state["session"]
        if kind == "TRACKING_STATUS":
            status = p.get("status")
            if status not in {"ready", "lost", "offline", "camera_unavailable"}:
                raise ValueError("Unknown tracking state")
            self.state["tracking"] = status
            self.state["vision"]["error"] = str(p.get("error", ""))[:300] or None
            if status != "ready" and s["mode"] == "gesture":
                self._pause("tracking")
        elif kind == "VISION_STATUS":
            if "calibrated" in p:
                if not isinstance(p["calibrated"], bool):
                    raise ValueError("Invalid calibration state")
                self.state["vision"]["calibrated"] = p["calibrated"]
            if p.get("dominant_hand") in {"left", "right"}:
                self.state["vision"]["dominant_hand"] = p["dominant_hand"]
            self.state["vision"]["capturing"] = bool(p.get("capturing", False))
            if isinstance(p.get("template_counts"), dict):
                self.state["vision"]["template_counts"] = p["template_counts"]
        elif kind == "GESTURE_REJECTED":
            self.state["last_gesture"] = {"name": "Rejected", "score": p.get("score", 0), "reason": str(p.get("reason", "No reliable match"))[:200]}
        elif kind == "GESTURE_RECOGNIZED":
            if p.get("epoch") != s["gesture_epoch"]:
                raise ValueError("Gesture capture predates the current control state")
            if s["mode"] != "gesture" or s["paused"] or self.state["tracking"] != "ready" or not self.state["vision"]["calibrated"]:
                raise ValueError("Gesture control is not currently active")
            name = p.get("name")
            score = number(p.get("score"), 0, 1)
            if name not in {"V", "circle", "Z"}:
                raise ValueError("Unknown gesture")
            if name == "V":
                if not s["isolated"]:
                    self._action("isolate", {})
                elif s["tool"] == "mirror":
                    self._action("place_tool", {})
                else:
                    raise ValueError("Select a tooth or mirror before confirming")
            elif name == "circle":
                self._action("layer", {"layer": "enamel"})
            else:
                self._pause("manual")
            self.state["last_gesture"] = {"name": name, "score": score, "reason": None}
        else:
            raise ValueError("Unsupported vision event")

    def _bluetooth(self, kind: str, p: dict):
        if kind == "BLE_STATUS":
            if p.get("status") not in {"idle", "scanning", "connecting", "connected", "disconnected", "error"}:
                raise ValueError("Unknown Bluetooth state")
            self.state["bluetooth"]["status"] = p["status"]
            self.state["bluetooth"]["error"] = str(p.get("error", ""))[:300] or None
        elif kind == "BLE_DEVICES":
            devices = p.get("devices")
            if not isinstance(devices, list) or len(devices) > 50:
                raise ValueError("Invalid device list")
            if any(not isinstance(d, dict) or not isinstance(d.get("id"), str) or not isinstance(d.get("name"), str) or len(d["id"]) > 100 or len(d["name"]) > 100 for d in devices):
                raise ValueError("Invalid device information")
            self.state["bluetooth"]["devices"] = [{"id": d["id"], "name": d["name"]} for d in devices]
        elif kind == "USER_IDENTIFIED":
            user_id = p.get("user_id")
            if not isinstance(user_id, str):
                raise ValueError("Invalid application UserID")
            self._identify(user_id, "bluetooth")
        else:
            raise ValueError("Unsupported Bluetooth event")
