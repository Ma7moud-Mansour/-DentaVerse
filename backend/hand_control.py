"""Clutched hand-to-scene bindings. Landmarks stay in the vision preview."""
import math


def clamp(value, low, high):
    return round(max(low, min(high, value)), 5)


def deadzone(value, limit):
    return math.copysign(max(0, abs(value) - limit), value)


class HandControl:
    def __init__(self):
        self.reset()

    def reset(self, require_all=False):
        self.context = None
        self.armed = set()
        self.anchor = None
        self.needs_release = True
        self.release_all = require_all

    @staticmethod
    def feedback(phase, message, hands=()):
        return {"phase": phase, "message": message, "hands": list(hands)}

    def step(self, session, hands, preferred, context, aspect=4/3):
        if context != self.context:
            self.reset()
            self.context = context
        visible = {h["id"]: h for h in hands if h["in_frame"] and h["gesture"] not in {"partial", "stabilizing"}}
        if not visible:
            self.reset()
            self.context = context
            message = "No hands detected · show an open palm in the video" if not hands else "Keep the whole hand and fingertips inside the video" if any(not h["in_frame"] for h in hands) else "Hold an open hand briefly to take control"
            return None, self.feedback("waiting", message)
        self.armed.intersection_update(visible)
        def pinching(h):
            return h["gesture"] == "pinch" and h["pinch_ratio"] <= 0.42
        def gripping(h):
            return h["gesture"] == "fist" and h["extended_fingers"] <= 1
        def opened(h):
            return h["gesture"] in {"open_palm", "neutral"} and h["extended_fingers"] >= 3 and h["pinch_ratio"] > 0.6
        if self.needs_release:
            if self.release_all and any(gripping(h) or pinching(h) for h in visible.values()):
                return None, self.feedback("release", "Open your hands before taking control")
            self.armed = {side for side,h in visible.items() if opened(h)}
            self.needs_release = not bool(self.armed)
            if self.armed:
                self.release_all = False
            phase = "ready" if self.armed else "release" if any(gripping(h) or pinching(h) for h in visible.values()) else "waiting"
            return None, self.feedback(phase, "Ready · grip or pinch to grab" if self.armed else "Open a hand before taking control")
        self.armed.update(side for side,h in visible.items() if opened(h))
        pinches = [side for side in ("left", "right") if side in self.armed and side in visible and pinching(visible[side])]

        def operation(hand):
            if gripping(hand) or pinching(hand) and session["tool"] == "hand":
                return "rotate"
            if pinching(hand):
                return "move_tool"
            return None

        mode, owners = None, ()
        if len(pinches) == 2:
            mode, owners = "zoom", tuple(pinches)
        elif self.anchor:
            old = self.anchor
            side = old["owners"][0]
            if old["mode"] != "zoom" and side in visible and operation(visible[side]) == old["mode"]:
                mode, owners = old["mode"], old["owners"]
        else:
            for side in (preferred, "left" if preferred == "right" else "right"):
                if side in self.armed and side in visible and operation(visible[side]):
                    mode, owners = operation(visible[side]), (side,)
                    break
        if self.anchor and (mode, owners) != (self.anchor["mode"], self.anchor["owners"]):
            # Two pinches may take over a one-hand grab without moving the scene.
            if mode != "zoom":
                self.reset(require_all=self.anchor["mode"] == "zoom")
                self.context = context
                return None, self.feedback("release", "Release the grab, then open your hands")
            self.anchor = None
        if mode is None:
            return None, self.feedback("ready", "Ready · grip or pinch to grab")
        if mode == "zoom":
            a,b = (visible[side]["center"] for side in owners)
            span = math.hypot((a["x"]-b["x"]) * aspect, a["y"]-b["y"])
            if span < 0.10:
                self.reset(require_all=True)
                self.context = context
                return None, self.feedback("release", "Separate your hands, then open them to rearm")
        hand = visible[owners[0]]
        if self.anchor is None:
            self.anchor = {"mode": mode, "owners": owners, "center": dict(hand["center"]),
                "rotation": dict(session["rotation"]), "position": dict(session["tool_position"]),
                "zoom": session["zoom"], "span": span if mode == "zoom" else None,
                "last_roll": hand["roll"], "roll": 0.0}
            return None, self.feedback({"rotate":"rotating","move_tool":"moving_tool","zoom":"zooming"}[mode], "Grabbed · move your hands; release to stop", owners)
        anchor = self.anchor
        if mode == "zoom":
            value = clamp(anchor["zoom"] * (1 + deadzone(span / anchor["span"] - 1, 0.015)), 0.6, 1.8)
            return ("zoom", {"value": value}), self.feedback("zooming", "Pinch both hands · spread to zoom in", owners)
        dx = deadzone(hand["center"]["x"] - anchor["center"]["x"], 0.008)
        dy = deadzone(hand["center"]["y"] - anchor["center"]["y"], 0.008)
        if mode == "move_tool":
            payload = {"x": clamp(anchor["position"]["x"] + dx * 3, -1, 1), "y": clamp(anchor["position"]["y"] - dy * 3, -1, 1)}
            return ("move_tool", payload), self.feedback("moving_tool", "Moving instrument · release the pinch to stop", owners)
        anchor["roll"] += (hand["roll"] - anchor["last_roll"] + 180) % 360 - 180
        anchor["last_roll"] = hand["roll"]
        payload = {"yaw": clamp(anchor["rotation"]["yaw"] + dx * 240 + deadzone(anchor["roll"], 2) * 0.6, -180, 180),
            "pitch": clamp(anchor["rotation"]["pitch"] + dy * 160, -80, 80)}
        return ("rotate", payload), self.feedback("rotating", "Rotating tooth · open your hand to release", owners)
