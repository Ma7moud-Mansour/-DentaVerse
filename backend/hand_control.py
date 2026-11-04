"""Clutched hand-to-scene bindings. Landmarks stay in the vision preview."""
import math


def clamp(value, low, high):
    return round(max(low, min(high, value)), 5)


def deadzone(value, limit):
    return math.copysign(max(0, abs(value) - limit), value)


def palm_span(hand, aspect):
    # Apparent palm size supplies RELATIVE depth on a monocular camera, not cm.
    points = hand["landmarks"]
    def distance(a, b):
        return math.hypot((points[a]["x"]-points[b]["x"])*aspect, points[a]["y"]-points[b]["y"])
    return max(0.025, hand.get("palm_span", (distance(5, 17)+distance(0, 9))/2))


def palm_tilt(hand, aspect):
    p = hand["landmarks"]
    a = [(p[5][k]-p[0][k]) * (aspect if k != "y" else 1) for k in ("x", "y", "z")]
    b = [(p[17][k]-p[0][k]) * (aspect if k != "y" else 1) for k in ("x", "y", "z")]
    x,y,z = a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]
    if z < 0:
        x,y,z = -x,-y,-z
    return {"yaw": math.degrees(math.atan2(x, max(z, 1e-6))), "pitch": math.degrees(math.atan2(y, max(math.hypot(x,z), 1e-6)))}


class HandControl:
    def __init__(self):
        self.reset()

    def reset(self, require_all=False):
        self.context = None
        self.armed = set()
        self.anchor = None
        self.needs_release = True
        self.release_all = require_all
        self.dual_anchors = {}

    @staticmethod
    def feedback(phase, message, hands=()):
        return {"phase": phase, "message": message, "hands": list(hands)}

    def step(self, session, hands, preferred, context, aspect=4/3):
        if session["tool"] != "hand":
            return self._bimanual(session, hands, context, aspect)
        action, feedback = self._single_step(session, hands, preferred, context, aspect)
        return [action] if action else [], feedback

    def _bimanual(self, session, hands, context, aspect):
        if context != self.context:
            self.reset()
            self.context = context
        visible = {h["id"]: h for h in hands if h["in_frame"] and h["gesture"] not in {"partial", "stabilizing"}}
        self.armed.intersection_update(visible)
        actions, active, states = [], [], {}
        for side in ("left", "right"):
            h = visible.get(side)
            if h is None:
                self.dual_anchors.pop(side, None)
                states[side] = "Show the whole hand"
                continue
            opened = h["gesture"] in {"open_palm", "neutral"} and h["extended_fingers"] >= 3 and h["pinch_ratio"] > .6
            held = h["gesture"] == "fist" and h["extended_fingers"] <= 1 or h["gesture"] == "pinch" and h["pinch_ratio"] <= .42
            if opened:
                self.armed.add(side)
                self.dual_anchors.pop(side, None)
                states[side] = "Ready · grip or pinch"
                continue
            if not held or side not in self.armed:
                if self.dual_anchors.pop(side, None):
                    self.armed.discard(side)
                states[side] = "Open palm to rearm"
                continue
            active.append(side)
            states[side] = "Tooth · rotate / depth zoom" if side == "left" else "Instrument · move XYZ / tilt"
            anchor = self.dual_anchors.get(side)
            if anchor is None:
                self.dual_anchors[side] = {"center": dict(h["center"]), "span": palm_span(h,aspect),
                    "rotation": dict(session["rotation"]), "zoom": session["zoom"],
                    "position": dict(session["tool_position"]), "tool_rotation": dict(session["tool_rotation"]),
                    "tilt": palm_tilt(h,aspect), "last_roll": h["roll"], "roll": 0.0}
                continue
            dx = deadzone(h["center"]["x"]-anchor["center"]["x"], .003)
            dy = deadzone(h["center"]["y"]-anchor["center"]["y"], .003)
            depth = deadzone(math.log(palm_span(h,aspect)/anchor["span"]), .035)
            anchor["roll"] += (h["roll"]-anchor["last_roll"]+180)%360-180
            anchor["last_roll"] = h["roll"]
            if side == "left":
                r = anchor["rotation"]
                actions.append(("rotate", {"yaw": clamp(r["yaw"]+dx*420,-180,180), "pitch": clamp(r["pitch"]+dy*300,-80,80),
                    "roll": clamp(r["roll"]+deadzone(anchor["roll"],1)*.9,-180,180)}))
                actions.append(("zoom", {"value": clamp(anchor["zoom"]*math.exp(depth*1.15),.6,1.8)}))
            else:
                p, r, tilt = anchor["position"], anchor["tool_rotation"], palm_tilt(h,aspect)
                actions.append(("move_tool", {"x": clamp(p["x"]+dx*4.2,-1,1), "y": clamp(p["y"]-dy*4.2,-1,1), "z": clamp(p["z"]+depth*1.8,-1,1),
                    "yaw": clamp(r["yaw"]+deadzone(tilt["yaw"]-anchor["tilt"]["yaw"],2)*.65,-80,80),
                    "pitch": clamp(r["pitch"]+deadzone(tilt["pitch"]-anchor["tilt"]["pitch"],2)*.65,-80,80),
                    "roll": clamp(r["roll"]+deadzone(anchor["roll"],1),-180,180)}))
        phase = "bimanual" if len(active) == 2 else "rotating" if active == ["left"] else "moving_tool" if active else "ready" if self.armed else "release" if visible else "waiting"
        feedback = self.feedback(phase, "Left: tooth · Right: instrument · open to release" if active else "Open palms · left controls tooth, right controls instrument", active)
        feedback["roles"] = states
        return actions, feedback

    def _single_step(self, session, hands, preferred, context, aspect=4/3):
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
        dx = deadzone(hand["center"]["x"] - anchor["center"]["x"], 0.003)
        dy = deadzone(hand["center"]["y"] - anchor["center"]["y"], 0.003)
        if mode == "move_tool":
            payload = {"x": clamp(anchor["position"]["x"] + dx * 3, -1, 1), "y": clamp(anchor["position"]["y"] - dy * 3, -1, 1)}
            return ("move_tool", payload), self.feedback("moving_tool", "Moving instrument · release the pinch to stop", owners)
        anchor["roll"] += (hand["roll"] - anchor["last_roll"] + 180) % 360 - 180
        anchor["last_roll"] = hand["roll"]
        payload = {"yaw": clamp(anchor["rotation"]["yaw"] + dx * 420, -180, 180),
            "pitch": clamp(anchor["rotation"]["pitch"] + dy * 300, -80, 80),
            "roll": clamp(anchor["rotation"]["roll"] + deadzone(anchor["roll"], 1)*.9, -180, 180)}
        return ("rotate", payload), self.feedback("rotating", "Rotating tooth · open your hand to release", owners)
