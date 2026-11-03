import copy
import math
from collections import deque
from uuid import UUID, uuid4

from backend.context import LAYERS, content_for
from backend.protocol import Message, check_fresh
from backend.preview import validate_camera_image
from backend.hands import validate_hands
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
            "vision": {"calibrated": False, "dominant_hand": "right", "capturing": False, "template_counts": {}, "error": None,
                "calibration_progress": 0.0, "calibration_status": "idle", "capture_name": None, "pending_capture": False, "pose": None},
            "services": {name: {"status": "stopped", "managed": False, "error": None} for name in ("vision", "bluetooth")},
            "last_gesture": None, "events": []}
        self.seen: set[str] = set()
        self.order: deque[str] = deque()
        self._restore_workspace()

    def checkpoint(self):
        self.store.save_workspace(self.state["profile"]["id"], self.state["session"], self.state["vision"]["dominant_hand"])

    def _restore_workspace(self):
        record = self.store.load_workspace()
        if not record or record.get("version") != 1:
            return
        try:
            profile_id = record.get("profile_id")
            if not isinstance(profile_id, str) or profile_id not in PROFILES:
                raise ValueError("Invalid saved profile")
            saved = record["session"]
            if not isinstance(saved, dict):
                raise ValueError("Invalid saved session")
            s = new_session()
            s.update({key: saved[key] for key in s if key in saved})
            UUID(s["id"])
            if s["screen"] not in {"studio", "atlas", "setup", "workbench", "review", "journal", "guide", "preferences"}:
                raise ValueError("Invalid saved screen")
            if s["selected_tooth"] is not None and (type(s["selected_tooth"]) is not int or s["selected_tooth"] != 16):
                raise ValueError("Invalid saved tooth")
            if any(type(s[key]) is not bool for key in ["isolated", "paused", "saved"]):
                raise ValueError("Invalid saved state flags")
            if s["isolated"] and s["selected_tooth"] != 16:
                raise ValueError("Invalid isolated specimen")
            s["rotation"] = {"yaw": number(s["rotation"]["yaw"], -180, 180), "pitch": number(s["rotation"]["pitch"], -80, 80)}
            s["zoom"] = number(s["zoom"], 0.6, 1.8)
            s["tool_position"] = {"x": number(s["tool_position"]["x"], -1, 1), "y": number(s["tool_position"]["y"], -1, 1)}
            if s["layer"] not in LAYERS or s["tool"] not in {"hand", "mirror", "explorer"} or s["mode"] not in {"manual", "gesture"}:
                raise ValueError("Invalid saved controls")
            if not isinstance(s["checkpoints"], list) or len(s["checkpoints"]) > 3 or any(p not in {"located", "inspected", "mirror_placed"} for p in s["checkpoints"]):
                raise ValueError("Invalid saved checkpoints")
            if not isinstance(s["note"], str) or len(s["note"]) > 4000 or type(s["gesture_epoch"]) is not int or s["gesture_epoch"] < 0:
                raise ValueError("Invalid saved reflection or epoch")
            if s["pause_reason"] not in {None, "manual", "tracking"}:
                raise ValueError("Invalid saved pause state")
            s["gesture_epoch"] += 1
            hand = record.get("hand")
            hand = hand if isinstance(hand, str) and hand in {"left", "right"} else "right"
            self.state["profile"] = copy.deepcopy(PROFILES[profile_id])
            self.state["identity_source"] = "restored_session"
            self.state["session"] = s
            self.state["vision"]["dominant_hand"] = hand
            if s["mode"] == "gesture":
                self._pause("tracking")
        except (KeyError, ValueError, TypeError, AttributeError):
            # A malformed checkpoint must not prevent opening the journal.
            return

    def snapshot(self) -> dict:
        return {**copy.deepcopy(self.state), "content": content_for(self.state), "journal": self.store.journal(self.state["profile"]["id"])}

    def worker_status(self, source: str, connected: bool):
        self.state["workers"][source] = connected
        service = self.state["services"][source]
        service["status"] = "running" if connected else "stopping" if service["managed"] and service["status"] == "stopping" else "starting" if service["managed"] else "stopped"
        if source == "vision" and not connected:
            if self.state["tracking"] != "camera_unavailable":
                self.state["tracking"] = "offline"
            self.state["vision"]["calibrated"] = False
            self.state["vision"]["capturing"] = False
            self.state["vision"]["pending_capture"] = False
            self.state["vision"]["calibration_status"] = "idle"
            self.state["vision"]["calibration_progress"] = 0.0
            self.state["vision"]["pose"] = None
            if self.state["session"]["mode"] == "gesture":
                self._pause("tracking")
        elif source == "bluetooth":
            self.state["bluetooth"]["status"] = "idle" if connected else "offline"

    def _pause(self, reason: str):
        if self.state["session"]["paused"] and self.state["session"]["pause_reason"] == reason:
            return
        self.state["session"].update(paused=True, pause_reason=reason)
        self.state["session"]["gesture_epoch"] += 1
        self.state["vision"]["capturing"] = False
        self.state["vision"]["pending_capture"] = False

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
        if message.source == "vision" and message.type == "POSE_FRAME":
            if message.session_id != self.state["session"]["id"]:
                raise ValueError("Pose frame belongs to another session")
            self.state["vision"]["pose"] = self._pose(message)
            return {"type": "ack", "event_id": message.event_id, "status": "preview"}
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
        if message.source == "ui" or message.type in {"USER_IDENTIFIED", "GESTURE_RECOGNIZED"}:
            self.checkpoint()
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
        elif action in {"edit_note", "save_session"}:
            note = payload.get("note", "")
            if not isinstance(note, str) or len(note) > 4000:
                raise ValueError("Reflection must be text of at most 4000 characters")
            s["note"] = note
            s["saved"] = action == "save_session"
            if action == "save_session":
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
        elif action in {"vision_start", "vision_stop", "ble_start", "ble_stop"}:
            source = "vision" if action.startswith("vision") else "bluetooth"
            service = self.state["services"][source]
            if action.endswith("start"):
                if self.state["workers"][source] or service["managed"] or service["status"] in {"starting", "running", "stopping"}:
                    raise ValueError("This service is already starting or running")
                if source == "vision":
                    camera = payload.get("camera", 0)
                    if type(camera) is not int or not 0 <= camera <= 4:
                        raise ValueError("Choose a camera index from 0 to 4")
                    self.state["vision"]["error"] = None
                service.update(status="starting", error=None)
            else:
                if service["status"] == "stopping":
                    raise ValueError("This service is already stopping")
                service.update(status="stopping", error=None)
                if source == "vision":
                    self.state["vision"].update(calibrated=False, capturing=False, pending_capture=False, pose=None, calibration_status="idle", calibration_progress=0.0)
                    s["gesture_epoch"] += 1
                    if s["mode"] == "gesture":
                        s["mode"] = "manual"
        elif action == "vision_hand":
            if payload.get("hand") not in {"left", "right"}:
                raise ValueError("Choose left or right hand")
            self.state["vision"].update(dominant_hand=payload["hand"], calibrated=False, calibration_progress=0.0, calibration_status="idle")
            s["gesture_epoch"] += 1
            if s["mode"] == "gesture":
                self._pause("tracking")
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
            if action == "vision_calibrate":
                self.state["vision"].update(calibrated=False, calibration_progress=0.0, calibration_status="collecting", capturing=False, pending_capture=False)
                s["gesture_epoch"] += 1
                if s["mode"] == "gesture":
                    self._pause("tracking")
            if action in {"capture_start", "template_record"}:
                if self.state["tracking"] != "ready" or not self.state["vision"]["calibrated"]:
                    raise ValueError("Calibrate visible shoulder and wrist before recording")
                if action == "capture_start" and (s["mode"] != "gesture" or s["paused"]):
                    raise ValueError("Enable gesture mode and resume before recording")
            if action == "template_record" and payload.get("name") not in {"V", "circle", "Z"}:
                raise ValueError("Choose V, circle or Z for the template")
            if action in {"capture_start", "template_record"}:
                if self.state["vision"]["capturing"] or self.state["vision"]["pending_capture"]:
                    raise ValueError("Finish or cancel the current recording first")
                self.state["vision"]["pending_capture"] = True
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
            self.state["vision"]["pending_capture"] = False
            self.state["vision"]["capture_name"] = p.get("capture_name") if p.get("capture_name") in {"V", "circle", "Z"} else None
            if "calibration_progress" in p:
                self.state["vision"]["calibration_progress"] = number(p["calibration_progress"], 0, 1)
            if p.get("calibration_status") in {"idle", "collecting", "ready", "needs_position"}:
                self.state["vision"]["calibration_status"] = p["calibration_status"]
            if "error" in p:
                self.state["vision"]["error"] = str(p.get("error") or "")[:300] or None
            if isinstance(p.get("template_counts"), dict):
                counts = p["template_counts"]
                if any(key not in {"V", "circle", "Z"} or type(value) is not int or not 0 <= value <= 300 for key, value in counts.items()):
                    raise ValueError("Invalid template counts")
                self.state["vision"]["template_counts"] = counts
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

    def _pose(self, message):
        p = message.payload
        points, trail = p.get("landmarks"), p.get("trail", [])
        if not isinstance(points, list) or len(points) not in {0, 33} or not isinstance(trail, list) or len(trail) > 200:
            raise ValueError("Invalid pose preview dimensions")
        landmarks = [{"x": number(point["x"], -2, 3), "y": number(point["y"], -2, 3), "visibility": number(point["visibility"], 0, 1)} for point in points]
        path = []
        for point in trail:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("Invalid preview trajectory")
            path.append([number(point[0], -2, 3), number(point[1], -2, 3)])
        count = p.get("capture_points", 0)
        if type(count) is not int or not 0 <= count <= 1000:
            raise ValueError("Invalid capture sample count")
        return {"landmarks": landmarks, "trail": path, "capture_points": count,
            "capture_elapsed": number(p.get("capture_elapsed", 0), 0, 9), "timestamp": message.timestamp,
            "image": validate_camera_image(p.get("image")), "hands": validate_hands(p.get("hands", [])),
            "hand_tracking": p.get("hand_tracking") is True}

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
