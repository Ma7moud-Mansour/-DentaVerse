"""Live MediaPipe Pose worker. Launch explicitly to open a local camera preview."""
import argparse
import asyncio
import logging
import math
import time
from pathlib import Path

from backend.gestures import GestureLibrary
from backend.workers.client import WorkerClient

ROOT = Path(__file__).resolve().parents[2]


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

    def begin(self, session_id, epoch, template_name=None):
        self.points = []
        self.started = time.monotonic()
        self.template_name = template_name
        self.session_id = session_id
        self.epoch = epoch

    def clear(self):
        self.__init__()


async def run(args):
    # Lazy imports keep protocol/classifier tests independent of camera dependencies.
    import cv2
    import mediapipe as mp

    model = Path(args.model)
    if not model.is_file():
        raise SystemExit("Pose model missing. Run: python tools/download_pose_model.py")
    library = GestureLibrary(args.templates, args.threshold)
    transport = WorkerClient("vision", args.port)
    network = asyncio.create_task(transport.run())
    capture = Capture()
    cam = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW) if __import__('sys').platform == 'win32' else cv2.VideoCapture(args.camera)
    hand = "right"
    calibrated = False
    origin = None
    scale = None
    smooth = None
    previous_status = None
    previous_session = None
    last_status = 0.0
    last_finish = 0.0
    if not cam.isOpened():
        await transport.connected.wait()
        await transport.emit("TRACKING_STATUS", {"status": "camera_unavailable", "error": "Camera could not be opened. Check camera index, Windows permissions and other apps."})
        network.cancel()
        await asyncio.gather(network, return_exceptions=True)
        cam.release()
        return

    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    # Required body connections; no reliance on the removed legacy mp.solutions API.
    connections = [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28)]
    try:
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                ok, frame = await asyncio.to_thread(cam.read)
                if not ok:
                    if transport.connected.is_set():
                        await transport.emit("TRACKING_STATUS", {"status": "camera_unavailable", "error": "Camera stopped delivering frames. Restart the vision worker."})
                    break
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(time.monotonic() * 1000))
                h, w = frame.shape[:2]
                landmarks = result.pose_landmarks[0] if result.pose_landmarks else None
                wrist_index = 15 if hand == "left" else 16
                valid = bool(landmarks and all(landmarks[i].visibility >= 0.65 for i in [11,12,wrist_index]))
                if landmarks:
                    for a,b in connections:
                        if landmarks[a].visibility >= 0.5 and landmarks[b].visibility >= 0.5:
                            p1 = (int(landmarks[a].x*w), int(landmarks[a].y*h))
                            p2 = (int(landmarks[b].x*w), int(landmarks[b].y*h))
                            cv2.line(frame, p1, p2, (171,238,219), 2)
                            cv2.circle(frame, p1, 4, (171,238,219), -1)
                    if valid:
                        p = landmarks[wrist_index]
                        current = (p.x, p.y)
                        smooth = current if smooth is None else tuple(0.35*a+0.65*b for a,b in zip(current,smooth))
                        cv2.circle(frame, (int(p.x*w),int(p.y*h)), 9, (100,210,160), 2)
                else:
                    smooth = None

                status = "ready" if valid else "lost"
                if capture.active and (not valid or not transport.connected.is_set() or capture.session_id != transport.session_id or capture.epoch != transport.epoch or (capture.template_name is None and not transport.gesture_active)):
                    capture.clear()
                if previous_session != transport.session_id:
                    previous_session = transport.session_id
                    previous_status = None
                    capture.clear()
                    if not transport.connected.is_set():
                        calibrated = False
                now = time.monotonic()
                if transport.connected.is_set() and (status != previous_status or now-last_status > 3):
                    await transport.emit("TRACKING_STATUS", {"status": status})
                    await transport.emit("VISION_STATUS", {"calibrated": calibrated, "dominant_hand": hand, "capturing": capture.active, "template_counts": library.counts})
                    previous_status, last_status = status, now

                while not transport.commands.empty():
                    command = transport.commands.get_nowait()
                    if command.get("session_id") != transport.session_id:
                        continue
                    kind = command["command"]
                    try:
                        if kind == "vision_calibrate":
                            capture.clear()
                            calibrated = False
                            hand = command["payload"].get("hand", "right")
                            idx = 15 if hand == "left" else 16
                            if not landmarks or any(landmarks[i].visibility < 0.65 for i in [11,12,idx]):
                                raise ValueError("Keep both shoulders and the chosen wrist visible for calibration")
                            center = ((landmarks[11].x+landmarks[12].x)/2, (landmarks[11].y+landmarks[12].y)/2)
                            width = math.dist((landmarks[11].x,landmarks[11].y),(landmarks[12].x,landmarks[12].y))
                            if width < 0.08:
                                raise ValueError("Move closer until the shoulders are clearly separated")
                            origin, scale, calibrated = center, width, True
                            smooth = None
                        elif kind in {"capture_start", "template_record"}:
                            if not valid or not calibrated:
                                raise ValueError("Visible wrist and calibration are required")
                            if now-last_finish < 0.8:
                                raise ValueError("Release between gestures before starting another capture")
                            if kind == "capture_start" and not transport.gesture_active:
                                raise ValueError("Enable active gesture control first")
                            capture.begin(command["session_id"], command["epoch"], command["payload"].get("name") if kind == "template_record" else None)
                        elif kind == "capture_cancel":
                            capture.clear()
                        elif kind == "capture_stop":
                            if not capture.active:
                                raise ValueError("Start a capture before recognizing or saving")
                            points, name, captured_session, epoch = capture.points[:], capture.template_name, capture.session_id, capture.epoch
                            capture.clear(); last_finish = now
                            if name:
                                library.add(name, points)
                            else:
                                match = library.recognize(points)
                                await transport.emit("GESTURE_RECOGNIZED" if match["accepted"] else "GESTURE_REJECTED", {**match, "epoch": epoch}, captured_session)
                    except ValueError as exc:
                        capture.clear()
                        await transport.emit("GESTURE_REJECTED", {"reason": str(exc), "score": 0.0})
                    await transport.emit("VISION_STATUS", {"calibrated": calibrated, "dominant_hand": hand, "capturing": capture.active, "template_counts": library.counts})
                if capture.active and valid and smooth is not None and origin and scale:
                    point = ((smooth[0]-origin[0])/scale, (smooth[1]-origin[1])/scale)
                    if all(abs(v) <= 10 for v in point):
                        capture.points.append(point)
                    if now-capture.started > 8 or len(capture.points) >= 1000:
                        capture.clear()
                        await transport.emit("GESTURE_REJECTED", {"reason": "Capture timed out; record one deliberate shape within eight seconds", "score": 0.0})
                    if len(capture.points) >= 2:
                        for a,b in zip(capture.points,capture.points[1:]):
                            pa = (int((a[0]*scale+origin[0])*w),int((a[1]*scale+origin[1])*h))
                            pb = (int((b[0]*scale+origin[0])*w),int((b[1]*scale+origin[1])*h))
                            cv2.line(frame,pa,pb,(70,180,240),2)
                label = f"DentaVerse | {hand} wrist | {status} | {'calibrated' if calibrated else 'calibrate in browser'}"
                cv2.putText(frame,label,(15,25),cv2.FONT_HERSHEY_SIMPLEX,0.5,(210,240,220),1)
                if capture.active:
                    cv2.putText(frame,f"Recording {capture.template_name or 'gesture'} ({len(capture.points)} points)",(15,48),cv2.FONT_HERSHEY_SIMPLEX,0.5,(70,180,240),1)
                if not args.no_preview:
                    cv2.imshow("DentaVerse Pose — press Q to close", frame)
                    if cv2.waitKey(1) & 0xff == ord('q'):
                        break
                await asyncio.sleep(0.01)
    finally:
        if transport.connected.is_set():
            try:
                await transport.emit("TRACKING_STATUS", {"status": "offline"})
            except OSError:
                pass
        cam.release()
        cv2.destroyAllWindows()
        network.cancel()
        await asyncio.gather(network, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--model", default=str(ROOT/"models"/"pose_landmarker_lite.task"))
    parser.add_argument("--templates", default=str(ROOT/"data"/"templates"/"gestures.json"))
    parser.add_argument("--threshold", type=float, default=0.72, help="Initial hypothesis; calibrate with held-out user captures")
    parser.add_argument("--no-preview", action="store_true", help="Use live camera without a local preview window")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
