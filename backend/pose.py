"""Body-point processing and stable calibration, independent of camera drivers."""
import math
from collections import deque


class PoseTracker:
    def __init__(self, hand="right"):
        self.hand = hand
        self.landmarks = []
        self.wrist = None
        self.calibrated = False
        self.origin = None
        self.scale = None
        self.samples = deque(maxlen=20)
        self.started = None
        self.progress = 0.0
        self.error = None

    @property
    def wrist_index(self):
        return 15 if self.hand == "left" else 16

    @property
    def ready(self):
        return len(self.landmarks) == 33 and all(
            self.landmarks[i]["visibility"] >= 0.65 and 0 <= self.landmarks[i]["x"] <= 1 and 0 <= self.landmarks[i]["y"] <= 1
            for i in (11, 12, self.wrist_index)
        )

    def set_hand(self, hand):
        if hand not in {"left", "right"}:
            raise ValueError("Choose left or right hand")
        self.hand = hand
        self.invalidate()

    def invalidate(self):
        self.calibrated = False
        self.error = None
        self.origin = self.scale = self.wrist = self.started = None
        self.progress = 0.0
        self.samples.clear()

    def begin_calibration(self, now):
        self.invalidate()
        self.error = None
        if not self.ready:
            raise ValueError("Keep both shoulders and the chosen wrist inside the camera view")
        self.started = now

    def observe(self, landmarks, now):
        self.landmarks = landmarks
        if self.ready:
            point = (landmarks[self.wrist_index]["x"], landmarks[self.wrist_index]["y"])
            self.wrist = point if self.wrist is None else tuple(0.35 * a + 0.65 * b for a, b in zip(point, self.wrist))
        else:
            self.wrist = None
        if self.started is None:
            return
        if now - self.started > 8:
            self.started = None
            self.progress = 0.0
            self.error = "Calibration timed out. Keep both shoulders and your chosen wrist visible, then retry."
            return
        if not self.ready:
            self.samples.clear()
            self.progress = 0.0
            return
        if self.samples and now - self.samples[-1][0] < 0.04:
            return
        left, right = landmarks[11], landmarks[12]
        center = ((left["x"] + right["x"]) / 2, (left["y"] + right["y"]) / 2)
        width = math.dist((left["x"], left["y"]), (right["x"], right["y"]))
        if width < 0.08:
            self.samples.clear()
            self.progress = 0.0
            return
        self.samples.append((now, center[0], center[1], width))
        duration = now - self.samples[0][0]
        self.progress = min(0.95, len(self.samples) / 12, duration / 0.7)
        if len(self.samples) < 12 or duration < 0.7:
            return
        means = [sum(sample[i] for sample in self.samples) / len(self.samples) for i in (1, 2, 3)]
        stable_center = max(math.dist((sample[1], sample[2]), means[:2]) for sample in self.samples) < 0.025
        stable_width = max(abs(sample[3] - means[2]) for sample in self.samples) / means[2] < 0.15
        if stable_center and stable_width:
            self.origin = tuple(means[:2])
            self.scale = means[2]
            self.calibrated = True
            self.started = None
            self.progress = 1.0
            self.error = None

    def normalized_wrist(self):
        if not self.ready or not self.calibrated or self.wrist is None:
            return None
        return ((self.wrist[0] - self.origin[0]) / self.scale, (self.wrist[1] - self.origin[1]) / self.scale)

    def preview(self, path=(), elapsed=0):
        trail = []
        if self.origin and self.scale:
            trail = [[1 - (x * self.scale + self.origin[0]), y * self.scale + self.origin[1]] for x, y in path[-200:]]
        return {"landmarks": [{**point, "x": 1 - point["x"]} for point in self.landmarks], "trail": trail,
            "capture_points": len(path), "capture_elapsed": round(elapsed, 1)}
