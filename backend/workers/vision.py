"""Live Pose camera owner, coordinate preview, calibration and DollarPy captures."""
import argparse
import asyncio
import logging
import math
import time
from pathlib import Path

from backend.gestures import GestureLibrary
from backend.hands import HandTracker, CONNECTIONS as HAND_CONNECTIONS
from backend.pose import PoseTracker
from backend.preview import encode_camera_image
from backend.workers.client import WorkerClient
from backend.wave import RightWave

ROOT = Path(__file__).resolve().parents[2]
CONNECTIONS = [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28)]


class Capture:
    def __init__(self):
        self.points = []
        self.started = None
        self.template_name = None
        self.session_id = None
        self.epoch = None

    @property
    def active(self):
        return self.started is not None

    def begin(self, session_id, epoch, now, template_name=None):
        self.points = []
        self.started = now
        self.template_name = template_name
        self.session_id = session_id
        self.epoch = epoch

    def clear(self):
        self.__init__()


async def run(args):
    import cv2
    import mediapipe as mp

    if not Path(args.model).is_file():
        raise SystemExit("Pose model missing. Run: python tools/download_pose_model.py")
    if not Path(args.hand_model).is_file():
        raise SystemExit("Hand model missing. Run: python tools/download_hand_model.py")
    library = GestureLibrary(args.templates, args.threshold)
    tracker, capture = PoseTracker(), Capture()
    hand_tracker = HandTracker()
    wave = RightWave()
    transport = WorkerClient("vision", args.port)
    network = asyncio.create_task(transport.run())
    cam = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW) if __import__('sys').platform == 'win32' else cv2.VideoCapture(args.camera)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    previous_status, previous_session, generation = None, None, -1
    last_status = last_preview = last_tracking = last_finish = 0.0
    frame_count = 0

    async def publish_status(now, force=False):
        nonlocal last_status
        if not transport.connected.is_set() or not force and now - last_status < 0.3:
            return
        await transport.emit("VISION_STATUS", {"calibrated": tracker.calibrated, "dominant_hand": tracker.hand,
            "capturing": capture.active, "capture_name": capture.template_name, "template_counts": library.counts,
            "calibration_progress": tracker.progress, "calibration_status": "collecting" if tracker.started is not None else "ready" if tracker.calibrated else "needs_position" if tracker.error else "idle", "error": tracker.error})
        last_status = now

    try:
        if not cam.isOpened():
            await asyncio.wait_for(transport.connected.wait(), 10)
            await transport.emit("TRACKING_STATUS", {"status": "camera_unavailable", "error": "Camera could not be opened. Check permissions, camera index and other camera apps."}, wait_ack=True)
            return
        options = mp.tasks.vision.PoseLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(args.model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1,
            min_pose_detection_confidence=0.6, min_pose_presence_confidence=0.6, min_tracking_confidence=0.6)
        hand_options = mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(args.hand_model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=0.65, min_hand_presence_confidence=0.65, min_tracking_confidence=0.65)
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker, mp.tasks.vision.HandLandmarker.create_from_options(hand_options) as hand_landmarker:
            while True:
                ok, frame = await asyncio.to_thread(cam.read)
                if not ok:
                    await transport.emit("TRACKING_STATUS", {"status": "camera_unavailable", "error": "Camera stopped delivering frames. Stop and restart the camera service."})
                    break
                now = time.monotonic()
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                camera_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(camera_image, int(now * 1000))
                hand_result = hand_landmarker.detect_for_video(camera_image, int(now * 1000))
                detections = []
                for index, landmarks in enumerate(hand_result.hand_landmarks):
                    category = hand_result.handedness[index][0]
                    hand_points = []
                    for p in landmarks:
                        if not all(math.isfinite(v) for v in (p.x,p.y,p.z)):
                            break
                        hand_points.append({"x": round(max(-2,min(3,1-p.x)),6), "y": round(max(-2,min(3,p.y)),6), "z": round(max(-2,min(2,p.z)),6)})
                    if len(hand_points) != 21 or category.category_name.lower() not in {"left","right"}:
                        continue
                    world = [(p.x,p.y,p.z) for p in hand_result.hand_world_landmarks[index]]
                    if len(world) != 21 or not all(math.isfinite(v) for p in world for v in p):
                        world = None
                    detections.append({"handedness": category.category_name.lower(), "score": float(category.score), "landmarks": hand_points, "world": world})
                points = []
                if result.pose_landmarks:
                    for point in result.pose_landmarks[0]:
                        x, y, visibility = float(point.x), float(point.y), float(point.visibility or 0)
                        if not all(math.isfinite(v) for v in (x, y, visibility)):
                            x, y, visibility = 0.0, 0.0, 0.0
                        points.append({"x": round(max(-2, min(3, x)),6), "y": round(max(-2, min(3, y)),6), "visibility": round(max(0, min(1, visibility)),6)})
                if generation != transport.generation:
                    generation = transport.generation
                    tracker.set_hand(transport.hand)
                    hand_tracker.reset()
                    capture.clear()
                    previous_status = None
                if previous_session != transport.session_id:
                    previous_session = transport.session_id
                    capture.clear()
                    hand_tracker.reset()
                hands = hand_tracker.update(detections, now, frame.shape[1] / frame.shape[0])
                tracker.observe(points, now)
                if capture.active and (not tracker.ready or not tracker.calibrated or not transport.connected.is_set()
                        or capture.session_id != transport.session_id or capture.epoch != transport.epoch
                        or capture.template_name is None and not transport.gesture_active):
                    capture.clear()
                    await transport.emit("GESTURE_REJECTED", {"reason": "Recording cancelled because tracking or the active control state changed", "score": 0.0})
                status = "ready" if tracker.ready else "lost"
                if transport.connected.is_set() and (status != previous_status or now - last_tracking > 3):
                    await transport.emit("TRACKING_STATUS", {"status": status})
                    previous_status, last_tracking = status, now
                    await publish_status(now, True)

                while not transport.commands.empty():
                    command = transport.commands.get_nowait()
                    if command["command"] == "shutdown":
                        return
                    if command.get("session_id") != transport.session_id:
                        continue
                    kind = command["command"]
                    try:
                        if kind == "vision_hand":
                            capture.clear()
                            tracker.set_hand(command["payload"]["hand"])
                        elif kind == "vision_calibrate":
                            capture.clear()
                            tracker.set_hand(command["payload"].get("hand", tracker.hand))
                            tracker.begin_calibration(now)
                        elif kind in {"capture_start", "template_record"}:
                            if not tracker.ready or not tracker.calibrated:
                                raise ValueError("Complete stable calibration with your chosen wrist visible first")
                            if capture.active:
                                raise ValueError("Finish or cancel the current recording first")
                            if now - last_finish < 0.8:
                                raise ValueError("Release between gestures before recording another shape")
                            if kind == "capture_start" and not transport.gesture_active:
                                raise ValueError("Enable gesture mode and resume before recording")
                            capture.begin(command["session_id"], command["epoch"], now,
                                command["payload"].get("name") if kind == "template_record" else None)
                        elif kind == "capture_cancel":
                            capture.clear()
                        elif kind == "capture_stop":
                            if not capture.active:
                                raise ValueError("Start a recording before recognizing or saving")
                            path, name, captured_session, epoch = capture.points[:], capture.template_name, capture.session_id, capture.epoch
                            capture.clear()
                            last_finish = now
                            if name:
                                library.add(name, path)
                            else:
                                match = library.recognize(path)
                                await transport.emit("GESTURE_RECOGNIZED" if match["accepted"] else "GESTURE_REJECTED", {**match, "epoch": epoch}, captured_session)
                    except (ValueError, OSError) as exc:
                        capture.clear()
                        await transport.emit("GESTURE_REJECTED", {"reason": str(exc)[:200], "score": 0.0})
                    await publish_status(now, True)

                point = tracker.normalized_wrist()
                if capture.active and point and all(abs(v) <= 10 for v in point):
                    capture.points.append(point)
                    if now - capture.started > 8 or len(capture.points) >= 1000:
                        capture.clear()
                        await transport.emit("GESTURE_REJECTED", {"reason": "Recording timed out. Draw one shape within eight seconds, then finish.", "score": 0.0})
                wave_epoch, wave_session = transport.epoch, transport.session_id
                wave_match=wave.update(hands,now,(wave_session,wave_epoch),enabled=transport.auto_wave and not capture.active)
                if transport.connected.is_set() and now - last_preview >= 1 / 15:
                    preview = tracker.preview(capture.points, now - capture.started if capture.active else 0)
                    preview["wave"] = wave.feedback
                    preview["hands"] = hands
                    preview["hand_tracking"] = True
                    preview["control_epoch"] = transport.epoch
                    preview["image"] = encode_camera_image(frame, cv2)
                    await transport.emit("POSE_FRAME", preview)
                    last_preview = now
                if wave_match and transport.connected.is_set():
                    await transport.emit("GESTURE_RECOGNIZED",{**wave_match,"epoch":wave_epoch},wave_session)
                if tracker.started is not None or capture.active or now - last_status > 3:
                    await publish_status(now)

                if not args.no_preview:
                    display = cv2.flip(frame, 1)
                    h, w = display.shape[:2]
                    for a, b in CONNECTIONS:
                        if points and min(points[a]["visibility"], points[b]["visibility"]) >= 0.5:
                            pixel = lambda i: (int((1 - points[i]["x"]) * w), int(points[i]["y"] * h))
                            cv2.line(display, pixel(a), pixel(b), (171, 238, 219), 2)
                            cv2.circle(display, pixel(a), 4, (171, 238, 219), -1)
                    for hand in hands:
                        hand_pixel = lambda i: (int(hand["landmarks"][i]["x"] * w), int(hand["landmarks"][i]["y"] * h))
                        color = (220,210,80) if hand["id"] == "left" else (80,210,250)
                        for a,b in HAND_CONNECTIONS:
                            cv2.line(display, hand_pixel(a), hand_pixel(b), color, 2)
                        for i in range(21):
                            cv2.circle(display, hand_pixel(i), 3, color, -1)
                    cv2.putText(display, f"DentaVerse | {tracker.hand} wrist | {status} | {'calibrated' if tracker.calibrated else 'calibrate in browser'}", (15,25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (210,240,220), 1)
                    cv2.imshow("DentaVerse Pose - Q to close", display)
                    if cv2.waitKey(1) & 0xff == ord('q'):
                        break
                frame_count += 1
                if args.max_frames and frame_count >= args.max_frames:
                    break
                await asyncio.sleep(0.01)
    finally:
        if transport.connected.is_set():
            try:
                await transport.emit("TRACKING_STATUS", {"status": "offline"})
            except OSError:
                pass
        cam.release()
        if not args.no_preview:
            cv2.destroyAllWindows()
        network.cancel()
        await asyncio.gather(network, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--model", default=str(ROOT / "models" / "pose_landmarker_lite.task"))
    parser.add_argument("--hand-model", default=str(ROOT / "models" / "hand_landmarker.task"))
    parser.add_argument("--templates", default=str(ROOT / "data" / "templates" / "gestures.json"))
    parser.add_argument("--threshold", type=float, default=0.72, help="Initial hypothesis; evaluate using held-out captures")
    parser.add_argument("--no-preview", action="store_true", help="Send live video and coordinates to the browser without a native preview window")
    parser.add_argument("--max-frames", type=int, default=0, help="Optional bounded hardware diagnostic; zero runs until stopped")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass
    except ImportError as exc:
        raise SystemExit(f"Vision dependencies are incomplete: {exc}. Run powershell -File tools/setup.ps1 -WithVision and retry.") from exc


if __name__ == "__main__":
    main()
