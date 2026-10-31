"""Bounded real-camera check on isolated TCP/storage; never saves camera frames."""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_app
from backend.protocol import Message


async def check(camera, frames):
    app = create_app(ROOT / ".review" / "runtime" / "camera-smoke.db", tcp_port=0)
    async with app.router.lifespan_context(app):
        hub = app.state.hub
        sid = hub.engine.state["session"]["id"]
        await hub.dispatch(Message(source="ui", type="vision_start", session_id=sid, payload={"camera": camera}))
        previews, last, largest, visible, statuses = 0, None, 0, 0, set()
        try:
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline and previews < frames:
                state = hub.engine.state
                statuses.add(state["tracking"])
                pose = state["vision"]["pose"]
                if pose and pose["timestamp"] != last:
                    last = pose["timestamp"]
                    previews += 1
                    largest = max(largest, len(pose["landmarks"]))
                    visible = max(visible, sum(p["visibility"] >= 0.5 and 0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in pose["landmarks"]))
                if state["services"]["vision"]["status"] == "error":
                    break
                await asyncio.sleep(0.08)
            print(json.dumps({"camera_index": camera, "preview_frames": previews,
                "largest_landmark_count": largest, "max_visible_points": visible,
                "tracking_states": sorted(statuses), "calibrated": state["vision"]["calibrated"],
                "templates": state["vision"]["template_counts"],
                "error": state["vision"]["error"] or state["services"]["vision"]["error"]}), flush=True)
        finally:
            await hub.dispatch(Message(source="ui", type="vision_stop", session_id=sid))
            for _ in range(100):
                if not hub.supervisor.owns("vision") and not hub.engine.state["workers"]["vision"] and hub.engine.state["services"]["vision"]["status"] == "stopped":
                    break
                await asyncio.sleep(0.1)
            stopped = not hub.supervisor.owns("vision") and not hub.engine.state["workers"]["vision"]
            print(json.dumps({"stopped": stopped, "service": hub.engine.state["services"]["vision"]["status"]}), flush=True)
        return previews >= frames and stopped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, choices=range(5), default=0)
    parser.add_argument("--frames", type=int, choices=range(1, 101), default=15)
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(check(args.camera, args.frames)) else 1)
