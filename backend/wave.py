"""Right-palm wave segmentation and real DollarPy matching.

Authored reference shapes are engineering defaults, not human training captures.
"""
import math
from dollarpy import Point, Recognizer, Template

WAVE_PHASES = {"disabled", "missing", "partial", "open", "ready", "tracking", "cooldown", "matched", "retry"}


def open_wave_palm(hand):
    """Allow a naturally bent finger, while excluding grabs and pinches."""
    return bool(hand and hand["id"] == "right" and hand["in_frame"]
        and hand["gesture"] not in {"fist", "pinch", "partial"}
        and sum(hand["fingers"][name] for name in ("index", "middle", "ring", "pinky")) >= 3
        and hand["pinch_ratio"] > .5)


def reference(points, steps=12):
    result = []
    for a, b in zip(points, points[1:]):
        result.extend(Point(a[0]+(b[0]-a[0])*i/steps, a[1]+(b[1]-a[1])*i/steps, 1) for i in range(steps))
    result.append(Point(*points[-1], 1))
    return result


class RightWave:
    THRESHOLD = .65
    COOLDOWN = 1.8

    def __init__(self):
        base = reference([(.2, .5), (.8, .5), (.2, .5)])
        waves = [[Point(p.x, .5+s*(p.x-.5)+a*(1-((p.x-.5)/.3)**2), 1) for p in base]
                 for s, a in ((0, 0), (.3, 0), (-.3, 0), (0, .12), (0, -.12), (.2, .08), (-.2, -.08))]
        waves.append(reference([(.2, .5), (.8, .5), (.2, .5), (.8, .5)]))
        self.references = [("wave", points) for points in waves] + [
            ("vertical", reference([(.5, .2), (.5, .8), (.5, .2)])),
            ("circle", [Point(.5+.4*math.cos(i*math.tau/32), .5+.4*math.sin(i*math.tau/32), 1) for i in range(33)]),
            ("V", reference([(.2, .2), (.5, .8), (.8, .2)])),
        ]
        self.recognizer = Recognizer([])
        self.context = None
        self.last_fire = -math.inf
        self.latched = False
        self.quiet_since = None
        self.feedback = {"phase": "missing", "turns": 0}
        self.clear()

    def clear(self):
        self.samples = []
        self.previous = None
        self.open_since = None
        self.direction = 0
        self.turns = 0
        self.extreme = None

    def status(self, phase):
        self.feedback = {"phase": phase, "turns": min(2, self.turns)}

    def update(self, hands, now, context, enabled=True):
        if context != self.context:
            self.context = context
            self.clear()
        if not enabled:
            self.clear(); self.quiet_since = None; self.status("disabled")
            return None
        hand = next((h for h in hands if h["id"] == "right"), None)
        if hand is None:
            # One missed detection must not erase an otherwise coherent wave.
            if self.previous and now-self.previous[0] <= .3:
                self.status("missing")
                return None
            self.clear(); self.quiet_since = None; self.status("missing")
            return None
        if not open_wave_palm(hand):
            self.clear(); self.quiet_since = None
            self.status("partial" if not hand["in_frame"] else "open")
            return None
        # MCP palm motion captures a wrist-pivot bye-bye as well as translation.
        x, y = (sum(hand["landmarks"][i][axis] for i in (5, 9, 13, 17))/4 for axis in ("x", "y"))
        if not all(math.isfinite(v) for v in (x, y, now)):
            self.clear(); self.status("retry")
            return None
        if self.open_since is None:
            self.open_since = now
        previous = self.previous
        self.previous = (now, x, y)
        self.status("ready")
        if not previous:
            return None
        dt = now-previous[0]
        if dt <= 0 or dt > .45:
            self.clear(); self.status("retry")
            return None
        span = max(.06, min(.3, hand.get("palm_span", .12)))
        dx = x-previous[1]
        speed = math.dist((x, y), previous[1:])/dt
        if speed < max(.04, span*.6):
            if self.quiet_since is None:
                self.quiet_since = now
            if now-self.quiet_since >= .35 and now-self.last_fire >= self.COOLDOWN:
                self.latched = False
        else:
            self.quiet_since = None
        if self.latched or now-self.last_fire < self.COOLDOWN:
            self.status("cooldown")
            return None
        if now-self.open_since < .15:
            return None
        if not self.samples:
            if abs(dx)/dt < max(.12, span*1.1):
                return None
            self.samples = [previous]
            self.direction = 1 if dx > 0 else -1
            self.turns = 0
            self.extreme = previous[1]
        self.samples.append((now, x, y))
        reversal = max(.012, min(.03, span*.12))
        if self.direction > 0:
            self.extreme = max(self.extreme, x)
            if x < self.extreme-reversal:
                self.turns += 1; self.direction = -1; self.extreme = x
        else:
            self.extreme = min(self.extreme, x)
            if x > self.extreme+reversal:
                self.turns += 1; self.direction = 1; self.extreme = x
        self.status("tracking")
        elapsed = now-self.samples[0][0]
        if elapsed > 2.4:
            self.samples = []; self.status("retry")
            return None
        if len(self.samples) < 6 or self.turns < 2 or elapsed < .25:
            return None
        xs = [p[1] for p in self.samples]; ys = [p[2] for p in self.samples]
        width, height = max(xs)-min(xs), max(ys)-min(ys)
        if width < max(.05, min(.14, span*.55)) or height > max(.045, width*.65):
            return None
        clean = []
        for _, px, py in self.samples:
            if not clean or math.dist((px, py), clean[-1]) > 1e-6:
                clean.append((px, py))
        if len(clean) < 5:
            return None
        # DollarPy resamples templates in place; give each match fresh copies.
        self.recognizer.templates = [Template(name, [Point(p.x, p.y, 1) for p in points]) for name, points in self.references]
        name, score = self.recognizer.recognize([Point(px, py, 1) for px, py in clean])
        score = max(0, min(1, float(score)))
        if name != "wave" or score < self.THRESHOLD:
            self.status("retry")
            return None
        self.last_fire = now; self.latched = True; self.samples = []
        self.status("matched")
        return {"name": "wave", "score": score, "method": "DollarPy", "template_origin": "authored_reference"}
