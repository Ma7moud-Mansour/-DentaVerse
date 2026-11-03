# Controlling the specimen with live hands

Open Anatomy atlas → Inspect specimen. Start the camera if needed and select **Enable hand controls**. Session setup also offers **Continue with hand controls**. Hand controls use the finger tracker directly and do not require shoulder calibration or stored DollarPy templates.

| Movement | Scene action |
|---|---|
| Show an open palm | Arm that hand without moving the scene |
| Close that hand and move sideways/up/down | Rotate/tilt the tooth from its existing angle |
| Turn the gripped palm | Add rotation to the tooth |
| Pinch with Hand selected | Grab and rotate the tooth |
| Select Mirror/Explorer, then pinch and move | Move the selected instrument relative to its current position |
| Pinch with both armed hands, then spread/close the gap | Zoom in/out from the current zoom |
| Open the controlling hand | Release immediately and retain the scene |

One open hand can arm independently while the other is closed. If both hands try to grab, the preferred hand is selected; the current grab retains ownership. Two pinches take priority for zoom. When zoom ends, release the held pinches and open your hands before another grab. The remaining pinch cannot turn into an accidental instrument drag.

In hand mode the camera and control feedback appear at the top of the inspector beside the specimen. Mouse dragging, wheel zoom, viewer keys and transform sliders are disabled in this mode. **Use mouse & keyboard** restores manual operation. Tool selection, layer selection and explicit reset remain available; they release the grab and require a new open-hand arm.

## Coordinator behavior

An open hand may have three or more visibly extended fingers and a released pinch; it does not need a perfectly straight five-finger classifier label. The controller reports missing, partial and stabilizing hands directly in the visible feedback beside the camera. Pointer transforms remain disabled while this hand mode is active.

`backend/hand_control.py` maintains ephemeral grab anchors. Each gesture uses the current scene transform and current hand center as its baseline, so acquiring a grab does not snap the tooth/tool to a hand coordinate. Motion is relative, with dead zones and bounded yaw/pitch, instrument position and zoom. Open-hand arming accepts natural finger bend; raw opening/pinch-release geometry can release before the stable pose label finishes its short debounce.

Validated vision POSE_FRAME messages carry `control_epoch`, echoed from coordinator context. Bindings require the active session/epoch, explicit hand mode, a fresh hand-capable camera frame, an isolated specimen on Workbench, no pause and no active gesture recording. UI navigation, reset, tool changes and input-mode transitions invalidate the anchors. Duplicate/older previews never replay movement. Pose shoulder visibility does not gate finger controls.

Losing the controlling hand releases the grab. A closed hand reappearing in view must open before acquiring a new grab. Worker loss or a frame stream older than 0.8 seconds pauses hand mode; a 0.2-second coordinator monitor also catches silent camera stalls. Recovery requires fresh frames, explicit Resume, and an open hand. Timing/dead-zone values are initial engineering settings, not measured usability results.

The coordinator updates the same rotate/zoom/move_tool actions used by manual controls. Hand previews deliver authoritative session transforms and hand_control feedback to the browser over WebSocket. Motion checkpoints are saved at most twice per second and on release/loss; the journal still requires an explicit save. Camera images, hand coordinates and grab anchors are not persisted. Restored hand-mode workspaces start paused with empty sensor state.

## Verification

Python checks cover arming without jumps, one-hand independence, naturally bent fingers, relative rotation/palm roll, instrument movement, zoom priority, release/loss, stale context, reset/pause/resume, old/duplicate frames, persistence and restart. Browser checks use synthetic hand signals through real TCP/WebSocket connections to rotate the rendered tooth, move the mirror, zoom, recover from a stalled stream, block mouse transforms in hand mode and retain the transforms after reload. Physical feedback is recorded separately in PROGRESS.md; synthetic checks do not establish recognition accuracy.
