# Right-hand wave: automatic DollarPy instrument switching

In **Live hand controls**, keep the right palm open and wave side to side quickly twice. One accepted wave cycles **No instrument → Mirror → Explorer → No instrument**. Pause the open hand briefly before the next wave. Click an active instrument shortcut again to remove it, or use **Next instrument** as a manual equivalent. The wave checkbox can disable automatic switching.

The wave is classified by the actual `dollarpy.Recognizer` ($P), not by a UI timer or a renamed finger pose. `backend/wave.py` segments the MediaPipe right-hand wrist trajectory, then passes its distinct points to DollarPy. It compares an **authored horizontal-wave reference** against authored vertical, circle and V references. These reference point clouds are constructed from geometry; they are not labelled as collected human samples and are never installed into `data/templates/gestures.json` or counted as live V/circle/Z captures.

## Accidental-command guards

- Only a fully visible, debounced open **right** palm with four or more extended fingers and a released pinch can contribute a path. The left palm, fist and pinch cannot trigger switching.
- A brief open-hand period precedes capture. Candidate movement needs horizontal speed, sufficient horizontal extent, two direction reversals, six or more frames and a bounded duration/vertical drift.
- $P ignores stroke order/direction, so temporal direction-reversal checks supplement shape matching. A single sweep or stationary hand cannot pass those guards.
- The accepted label must be `wave` with score at least 0.82. That score is a matcher similarity, not a calibrated probability or measured human accuracy.
- One accepted wave latches the recognizer. Further movement cannot cycle again until a quiet open-hand interval and a 1.8-second cooldown. Changing tool/context does not clear that latch prematurely.
- The worker receives `auto_wave` in coordinator context. It stops segmentation outside an isolated, unpaused Workbench in hand mode, or during manual recording. Context/session/epoch changes cancel an unfinished path.
- The server independently requires current session/epoch, a fresh hand preview, an open right palm, enabled wave controls, the DollarPy method/reference metadata, sufficient score and its own cooldown. Browser clients cannot impersonate sensor events.
- An accepted wave changes one tool, increments the epoch, releases old object grabs and checkpoints the workspace. Open palms before taking control of the newly selected tool.

Hand control remains separate from the manually recorded **Camera gestures** route. V/circle/Z still use actual saved wrist templates and shoulder calibration; the built-in wave does not require those captures. Body Pose and both full hands still share the live camera stream.

## Evidence

Synthetic trajectory tests invoke the real DollarPy library, including a low camera sampling rate. They exercise the incorrect hand, closed poses, single sweeps, vertical movement, latch/rearm, cooldown, stale contexts and server state guards. The browser test runs the real Python matcher on a declared synthetic trajectory, sends its result over the test worker TCP connection and checks the WebSocket-driven tool selection and remove/next buttons.

This proves implementation and transport behavior. It does not establish human recognition accuracy, false-positive rates or a held-out participant evaluation. Camera images and automatic wave trajectories are processed in memory, not saved or transmitted to an external service.
