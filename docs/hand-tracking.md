# Two-hand and finger tracking

The worker runs **MediaPipe Hand Landmarker with num_hands=2** alongside the required Pose model. Every hand has 21 x/y/z landmarks covering the wrist, thumb and four fingers. Pose still supplies the body skeleton and existing wrist-path calibration.

## Coordinates and identity

Both models process the same unmirrored RGB frame. Current Tasks documentation defines handedness relative to the subject. Each model's x coordinate is mirrored exactly once for the displayed selfie video; anatomical side labels are preserved. Preview landmarks come directly from the current frame, without delayed coordinate smoothing.

Assignment combines model handedness and temporal wrist proximity. It retains distinct left/right identities across result reordering and weak label fluctuations. Losing a hand removes its skeleton and history; reacquisition starts with zero motion and a stabilizing state. Left is blue; right is amber. Hands is the default overlay; Body and Both remain available. Finger tracking starts immediately and does not require shoulder calibration.

## Signals for programmable bindings

| POSE_FRAME.hands[] field | Meaning |
|---|---|
| id / handedness | Stable left/right side, not a personal identity |
| landmarks | Exactly 21 normalized x/y/z values in display coordinates |
| score | Model handedness score, not positional accuracy |
| fingers / extended_fingers | Per-finger booleans and count |
| gesture | stabilizing, open_palm, fist, pinch, neutral, partial |
| pinch_ratio | 3D thumb-tip/index-tip distance divided by palm width |
| center | Smoothed display palm center for future movement bindings |
| roll | Smoothed clockwise screen-plane palm angle in degrees |
| motion | Per-frame x/y/roll deltas for movement/rotation bindings |
| in_frame | Wrist, palm bases and fingertips inside the usable frame |

Finger extension combines 3D joint angles, chain straightness and fingertip distance from the wrist. World landmarks are used when available. Pinch uses separate enter/release thresholds. A new pose requires three observations spanning at least 0.12 seconds. Motion smoothing is time-based and roll differences wrap at ±180 degrees. Partial hands suppress stable gestures.

These are initial geometric heuristics requiring human validation across lighting, perspectives and occlusion. Explicit **Live hand controls** now binds these signals to specimen rotation, instrument movement and two-hand zoom, with open-hand arming, release and context guards. The existing recorded DollarPy paths retain their command route. See [hand controls](hand-controls.md).

## Model and verification

`tools/download_hand_model.py` and `tools/setup.ps1 -WithVision` download Google's version-1 bundle. Installed SHA256: `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.

Hand points, video and derived states share the bounded local preview packet, remain in memory, and never enter event history, workspace storage or templates. The 64 KiB limit is unchanged. JSON fixtures in tests are explicitly synthetic.

Tests cover two 21-point hands, reordering, ambiguous handedness, loss/reacquisition, fist/pinch/open-palm debounce, natural joint bend, 3D rotation invariance, roll motion, invalid packets, persistence exclusion and the video+hands+trail byte budget. Browser checks cover skeletons, readouts, overlay switching and disappearance while video remains visible.

The model initialized successfully on a blank image. It detected one complete 21-point hand and five extended fingers/open-palm state in the screenshot supplied by the user; that was an offline development check. In the updated live page, the user explicitly confirmed that 2/2 hands appeared and the points matched the fingers. A later runtime observation contained a 21-point hand with an in-frame pinch signal. This is functional feedback, not a labelled accuracy study. Systematic left/right/finger-count/fist/pinch/roll evaluation remains tracked separately.

Sources: [current Hand Landmarker Tasks overview](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/index), [Python video API](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python).
