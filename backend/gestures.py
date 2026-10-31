"""DollarPy wrapper. No bundled synthetic templates are passed off as captures."""
import json
import math
from pathlib import Path

from dollarpy import Point, Recognizer, Template

NAMES = {"V", "circle", "Z"}


def validate_path(points: list) -> list[tuple[float, float]]:
    if not isinstance(points, list) or not 12 <= len(points) <= 2000:
        raise ValueError("Record a complete path with 12–2000 points")
    result = []
    for pair in points:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("Each path point must contain x and y")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 10 for v in pair):
            raise ValueError("Invalid path coordinate")
        result.append((float(pair[0]), float(pair[1])))
    length = sum(math.dist(a, b) for a, b in zip(result, result[1:]))
    xs, ys = zip(*result)
    if length < 0.15 or max(max(xs) - min(xs), max(ys) - min(ys)) < 0.08:
        raise ValueError("Movement is too small to classify reliably")
    # $P has a divide-by-zero edge case for duplicate samples; remove stationary points.
    clean = [result[0]]
    for point in result[1:]:
        if math.dist(point, clean[-1]) > 1e-6:
            clean.append(point)
    if len(clean) < 3:
        raise ValueError("Not enough distinct motion samples")
    return clean


class GestureLibrary:
    def __init__(self, path: str | Path, threshold: float = 0.72):
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        self.path = Path(path)
        self.threshold = threshold
        self.records = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or len(data) > 300:
                raise ValueError("Invalid gesture template library")
            for item in data:
                if item.get("name") not in NAMES or item.get("origin") != "live_pose":
                    raise ValueError("Templates must be named live Pose captures")
                validate_path(item.get("points"))
            self.records = data

    @property
    def counts(self):
        return {name: sum(r["name"] == name for r in self.records) for name in sorted(NAMES)}

    def add(self, name: str, points: list):
        if name not in NAMES:
            raise ValueError("Unsupported template name")
        if len(self.records) >= 300:
            raise ValueError("Template library is full")
        clean = validate_path(points)
        record = {"name": name, "origin": "live_pose", "points": clean}
        records = self.records + [record]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, allow_nan=False), encoding="utf-8")
        temporary.replace(self.path)
        self.records = records

    def recognize(self, points: list) -> dict:
        clean = validate_path(points)
        if not self.records:
            return {"accepted": False, "name": None, "score": 0.0, "reason": "No real templates saved. Collect V, circle and Z first."}
        templates = [Template(r["name"], [Point(x, y, 1) for x, y in validate_path(r["points"])]) for r in self.records]
        result = Recognizer(templates).recognize([Point(x, y, 1) for x, y in clean])
        if result is None:
            return {"accepted": False, "name": None, "score": 0.0, "reason": "No match"}
        name, score = result
        score = max(0.0, min(1.0, float(score)))
        return {"accepted": score >= self.threshold, "name": name, "score": score,
            "reason": None if score >= self.threshold else "Match below the configured threshold"}
