# Camera implementation and observed check

## Implementation

The vision worker owns one OpenCV camera and MediaPipe Pose Landmarker in VIDEO mode. Inference uses the unmirrored frame so anatomical wrist indices remain correct. At the user's request, live video now accompanies normalized coordinate/visibility values and a bounded wrist trail over loopback TCP/WebSocket. A mirrored JPEG and the points inferred from that same source frame share one POSE_FRAME message, avoiding separate camera owners and mismatched video/points. The browser overlays the SVG on the video with the actual image aspect ratio. No frames are recorded or written to SQLite.

Live JPEGs have a maximum 640×480 bounding box, preserve aspect ratio, and adapt quality/resolution to a 42,000-character base64 budget within the existing 64 KiB message limit. Preview transmission is capped at 15 updates per second; actual frame rate depends on camera/inference speed. Stale frames and points are hidden together. Coordinate-only workers remain supported. The original observations below predate video display and remain a historical record.

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

## Requested live video — 2026-10-31

The updated worker/browser path was exercised on the physical camera with video enabled. Eight distinct frame timestamps were observed during a bounded check, carrying 640×480 JPEGs and 33 landmarks. The largest observed base64 image was 41,800 characters. The browser decoded the real image and confirmed that its displayed rectangle and the SVG rectangle match. The scene/profile/note state survived the coordinator update. Camera and Bluetooth services were left running.

Local verification now passes 44 Python tests and the sensor browser test. The latter decodes an explicitly synthetic 320×180 JPEG to check widescreen aspect/overlay alignment. Encoder tests also check mirroring and the existing 64 KiB transport budget on high-detail noise. Video remains ephemeral; only a local ignored QA screenshot was saved, not a camera recording or a collected gesture template.
