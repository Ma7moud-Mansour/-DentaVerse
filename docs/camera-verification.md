# Camera implementation and observed check

## Implementation

The vision worker owns one OpenCV camera and MediaPipe Pose Landmarker in VIDEO mode. Inference uses the unmirrored frame so anatomical wrist indices remain correct. Only normalized coordinate/visibility values and a bounded wrist trail travel over TCP/WebSocket. The browser mirrors these points into its SVG preview. It receives no RGB images.

Calibration requires both shoulders and the preferred wrist with visibility at least 0.65 and inside the frame. It samples at most 25 times per second, requires at least 12 samples over 0.7 seconds, and accepts only a stable shoulder center/width. It times out after eight seconds. Wrist positions use exponential smoothing (0.35 new / 0.65 previous), reset when tracking is lost, then normalize to the calibrated shoulder center and width. These are initial engineering thresholds, not measured study results.

The browser supports camera start/stop/index selection, preferred hand, calibration progress, actual landmark preview, capture sample/time feedback and template counts. Stale preview points disappear. Tracking loss in gesture mode pauses the workspace; regaining tracking never resumes it automatically. A recording is cancelled on loss, mode/epoch/session change or reconnect. Stop camera invalidates calibration and returns to manual input.

## Actual local hardware observation — 2026-10-31

Windows reported an **Integrated Webcam**. A real OpenCV probe opened camera index 0 and received a 640×480 frame, without saving it.

A separate coordinator with isolated SQLite storage and an ephemeral TCP port launched the actual vision worker:

- 15 coordinate previews received from the physical camera.
- Largest landmark array: 33; maximum visible/in-frame landmarks: 23.
- Observed tracking statuses: offline during startup, lost, and ready.
- No camera/worker error reported.
- Calibration remained false; V, circle and Z template counts remained zero.
- Explicit stop completed: the owned worker exited, its TCP connection closed, and service status became stopped.

The repeatable diagnostic is `tools/check_camera_runtime.py`. No raw image, trajectory or participant identity was committed. This confirms the camera/model/transport/lifecycle path. It does **not** establish successful human calibration, recognition accuracy, usability, or an end-to-end physical BLE/gesture journey. Those checks remain open.

A subsequent five-preview run of the new diagnostic received frames with no detected body (zero landmarks, offline/lost statuses), then stopped successfully. Detection depends on the person being in view; this was not an accuracy study.

## Automated evidence

42 Python tests passed, including stable/moving calibration, preferred wrist, mirroring, ephemeral preview validation, stale gesture rejection, duplicate recording prevention and real Bluetooth worker process start/stop without scanning. Four browser tests passed; the new sensor test uses explicitly synthetic coordinates to verify SVG preview, hand preference, progress, capture feedback, cancellation and explicit recovery.

The synthetic UI screenshot is stored locally under `.review/ui/synthetic-skeleton-capture.png`; it is not live camera evidence.
