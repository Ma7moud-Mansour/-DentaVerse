"""Two-hand identity, finger features and debounced signals; independent of CV."""
import math
from itertools import permutations

SIDES = ("left", "right")
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
GESTURES = {"stabilizing", "open_palm", "fist", "pinch", "neutral", "partial"}
CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),(13,17),(0,17),(17,18),(18,19),(19,20)]


def angle(a, b, c):
    u, v = [x-y for x,y in zip(a,b)], [x-y for x,y in zip(c,b)]
    norm = math.sqrt(sum(x*x for x in u) * sum(x*x for x in v))
    if norm < 1e-12:
        return 0.0
    return math.degrees(math.acos(max(-1, min(1, sum(x*y for x,y in zip(u,v)) / norm))))


def finger_features(points):
    states = {}
    states["thumb"] = angle(points[1],points[2],points[3]) > 145 and angle(points[2],points[3],points[4]) > 150 and math.dist(points[4],points[17]) > 1.1 * math.dist(points[3],points[17])
    for name, mcp in zip(FINGERS[1:], (5,9,13,17)):
        length = sum(math.dist(points[i], points[i+1]) for i in (mcp,mcp+1,mcp+2))
        straightness = math.dist(points[mcp], points[mcp+3]) / max(length, 1e-6)
        states[name] = angle(points[mcp],points[mcp+1],points[mcp+2]) > 140 and angle(points[mcp+1],points[mcp+2],points[mcp+3]) > 130 and straightness > 0.85 and math.dist(points[mcp+3],points[0]) > 1.04 * math.dist(points[mcp+1],points[0])
    width = max(math.dist(points[5], points[17]), 1e-6)
    return states, min(10.0, math.dist(points[4], points[8]) / width)


class HandTracker:
    def __init__(self):
        self.tracks = {}

    def reset(self):
        self.tracks.clear()

    def update(self, detections, now, aspect=4/3):
        """Detections use display coordinates; world points retain metric geometry."""
        detections = detections[:2]
        if not detections:
            self.reset()
            return []
        # Assign distinct identities, preserving continuity when model output order changes.
        def cost(order):
            total = 0.0
            for detection, side in zip(detections, order):
                total += (0 if detection["handedness"] == side else 0.45 * max(0, (detection["score"] - 0.5) * 2))
                previous = self.tracks.get(side)
                if previous and now - previous["time"] < 0.5:
                    wrist = detection["landmarks"][0]
                    total += 2 * min(0.4, math.dist((wrist["x"] * aspect, wrist["y"]), previous["wrist"]))
                elif self.tracks:
                    total += 0.7
            return total
        order = min(permutations(SIDES, len(detections)), key=cost)
        updated, results = {}, []
        for detection, side in zip(detections, order):
            points = detection["landmarks"]
            previous = self.tracks.get(side)
            wrist = (points[0]["x"] * aspect, points[0]["y"])
            if previous and (now - previous["time"] > 0.5 or math.dist(wrist, previous["wrist"]) > 0.4):
                previous = None
            geometry = detection.get("world") or [(p["x"] * aspect, p["y"], p["z"] * aspect) for p in points]
            fingers, pinch_ratio = finger_features(geometry)
            in_frame = all(0.01 < points[i]["x"] < 0.99 and 0.01 < points[i]["y"] < 0.99 for i in (0,4,5,8,9,12,13,16,17,20))
            pinch = in_frame and pinch_ratio < (0.42 if previous and previous["pinch"] and any(fingers[name] for name in FINGERS[1:]) else 0.28)
            raw = "partial" if not in_frame else "pinch" if pinch else "fist" if not any(fingers[name] for name in FINGERS[1:]) else "open_palm" if all(fingers[name] for name in FINGERS[1:]) else "neutral"
            candidate = raw
            since, samples = now, 1
            stable = "partial" if not in_frame else "stabilizing"
            if previous:
                stable = previous["stable"]
                if previous["candidate"] == raw:
                    since, samples = previous["since"], previous["samples"] + 1
                if raw == "partial" or samples >= 3 and now - since >= 0.12:
                    stable = raw
            center = {axis: sum(points[i][axis] for i in (0,5,9,13,17)) / 5 for axis in ("x", "y")}
            palm_span = sum(math.hypot((points[a]["x"]-points[b]["x"])*aspect, points[a]["y"]-points[b]["y"]) for a,b in ((5,17),(0,9)))/2
            roll = math.degrees(math.atan2((points[9]["x"] - points[0]["x"]) * aspect, points[0]["y"] - points[9]["y"]))
            motion = {"x": 0.0, "y": 0.0, "roll": 0.0}
            if previous and in_frame:
                dt = max(.001, now-previous["time"])
                speed = math.hypot((center["x"]-previous["center"]["x"])*aspect, center["y"]-previous["center"]["y"])/dt
                # Stronger jitter suppression while still; follow intentional motion quickly.
                weight = 1 - math.exp(-dt / (.085/(1+min(speed,4)*4)))
                depth_weight = 1-math.exp(-dt/.09)
                palm_span = previous["palm_span"]+depth_weight*(palm_span-previous["palm_span"])
                center = {axis: previous["center"][axis] + weight * (center[axis] - previous["center"][axis]) for axis in ("x", "y")}
                delta_roll = (roll - previous["roll"] + 180) % 360 - 180
                filtered_roll = previous["roll"] + weight * delta_roll
                motion = {"x": center["x"] - previous["center"]["x"], "y": center["y"] - previous["center"]["y"], "roll": weight * delta_roll}
                roll = (filtered_roll + 180) % 360 - 180
            updated[side] = dict(time=now, wrist=wrist, pinch=pinch, candidate=candidate, since=since, samples=samples,
                stable=stable, center=center, roll=roll, palm_span=palm_span)
            results.append({"id": side, "handedness": side, "score": round(detection["score"] if detection["handedness"] == side else 1 - detection["score"], 4),
                "landmarks": points, "gesture": stable, "fingers": fingers, "extended_fingers": sum(fingers.values()),
                "pinch_ratio": round(pinch_ratio, 4), "in_frame": in_frame, "center": {k: round(v,6) for k,v in center.items()},
                "roll": round(roll,3), "palm_span": round(palm_span,6), "motion": {k: round(v,6) for k,v in motion.items()}})
        self.tracks = updated
        return sorted(results, key=lambda hand: hand["id"])


def validate_hands(hands):
    if not isinstance(hands, list) or len(hands) > 2:
        raise ValueError("Expected at most two tracked hands")
    def number(value, lower, upper):
        if type(value) not in (int,float) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError("Invalid hand feature number")
        return value
    result, seen = [], set()
    for hand in hands:
        if not isinstance(hand, dict) or hand.get("id") not in SIDES or hand["id"] in seen:
            raise ValueError("Hand identities must be distinct left/right")
        seen.add(hand["id"])
        points, fingers = hand.get("landmarks"), hand.get("fingers")
        if not isinstance(points, list) or len(points) != 21:
            raise ValueError("Each hand needs 21 landmarks")
        landmarks = [{"x": number(p["x"],-2,3), "y": number(p["y"],-2,3), "z": number(p["z"],-2,2)} for p in points]
        if not isinstance(fingers, dict) or set(fingers) != set(FINGERS) or any(type(v) is not bool for v in fingers.values()):
            raise ValueError("Invalid finger state")
        if hand.get("gesture") not in GESTURES or type(hand.get("in_frame")) is not bool:
            raise ValueError("Invalid hand gesture")
        if type(hand.get("extended_fingers")) is not int or hand["extended_fingers"] != sum(fingers.values()):
            raise ValueError("Invalid finger count")
        center, motion = hand.get("center",{}), hand.get("motion",{})
        result.append({"id": hand["id"], "handedness": hand["id"], "score": number(hand.get("score"),0,1),
            "landmarks": landmarks, "gesture": hand["gesture"], "fingers": fingers, "extended_fingers": hand["extended_fingers"],
            "in_frame": hand["in_frame"], "pinch_ratio": number(hand.get("pinch_ratio"),0,10), "roll": number(hand.get("roll"),-180,180),
            "center": {k: number(center.get(k),-2,3) for k in ("x","y")},
            "motion": {k: number(motion.get(k),-180 if k == "roll" else -5,180 if k == "roll" else 5) for k in ("x","y","roll")}})
        if "palm_span" in hand:
            result[-1]["palm_span"] = number(hand["palm_span"],0,5)
    return result
