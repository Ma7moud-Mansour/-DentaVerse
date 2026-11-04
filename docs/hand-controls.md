# Controlling the specimen with live hands

Open Anatomy atlas → Inspect specimen. Start the camera if needed and select **Enable hand controls**. Session setup also offers **Continue with hand controls**. Hand controls use the finger tracker directly and do not require shoulder calibration or stored DollarPy templates.

## Mirror or Explorer selected: two independent hands

| Hand / movement | Action |
|---|---|
| Open either palm | Arm that hand independently, without moving either object |
| Left fist, then move X/Y | Rotate the tooth in yaw/pitch |
| Turn the held left palm | Roll the tooth around its Z axis |
| Pinch with both hands, then separate / bring together | Zoom in / out; both object grabs stop |
| Bring the left palm closer / farther | No zoom; left-hand depth is ignored |
| Right fist or pinch, then move X/Y | Move the selected instrument horizontally / vertically |
| Bring the held right palm closer / farther | Move the instrument in Z, independently of tooth zoom |
| Tilt or turn the held right palm | Change instrument yaw/pitch/roll |
| Open a controlling hand | Release only its object; the other hand can continue |

The left fist rotates. The right hand accepts a fist or pinch to move the instrument. A left pinch alone does not rotate or zoom. **Both pinches take priority for span-based zoom in every tool mode**, freezing tooth rotation and instrument movement. Open the palms after zoom before grabbing again. Left/right mean anatomical hands as labelled in the overlay; preferred-wrist settings do not swap the fixed instrument-mode roles.

## Hand tool selected

Either armed hand can grip/pinch to rotate the tooth. If both try to grab, the preferred hand is selected and the current grab retains ownership. Two pinches take priority for span-based zoom here as well. When that zoom ends, release the held pinches and open your hands before another grab.

In hand mode the camera and control feedback appear at the top of the inspector beside the specimen. Mouse dragging, wheel zoom, viewer keys and transform sliders are disabled in this mode. **Use mouse & keyboard** restores manual operation. Tool selection, layer selection and explicit reset remain available; they release the grab and require a new open-hand arm.

## Coordinator behavior

An open hand may have three or more visibly extended fingers and a released pinch; it does not need a perfectly straight five-finger classifier label. The controller reports missing, partial and stabilizing hands directly in the visible feedback beside the camera. Pointer transforms remain disabled while this hand mode is active.

`backend/hand_control.py` maintains ephemeral grab anchors. Each gesture uses the current scene transform and current hand center as its baseline, so acquiring a grab does not snap the tooth/tool to a hand coordinate. Motion is relative, with dead zones and bounded yaw/pitch/roll, instrument XYZ/orientation and zoom. Open-hand arming accepts natural finger bend; raw opening/pinch-release geometry can release before the stable pose label finishes its short debounce.

Validated vision POSE_FRAME messages carry `control_epoch`, echoed from coordinator context. Bindings require the active session/epoch, explicit hand mode, a fresh hand-capable camera frame, an isolated specimen on Workbench, no pause and no active gesture recording. UI navigation, reset, tool changes and input-mode transitions invalidate the anchors. Duplicate/older previews never replay movement. Pose shoulder visibility does not gate finger controls.

Losing a controlling hand releases its grab independently and clears its arming. The other instrument-mode hand can continue. A closed hand reappearing in view must open before acquiring a new grab. Worker loss or a frame stream older than 0.8 seconds pauses hand mode; a 0.2-second coordinator monitor also catches silent camera stalls. Recovery requires fresh frames, explicit Resume, and an open hand. Timing/dead-zone values are initial engineering settings, not measured usability results.

The coordinator updates the same rotate/zoom/move_tool actions used by manual controls. Hand previews deliver authoritative session transforms and hand_control feedback to the browser over WebSocket. Motion checkpoints are saved at most twice per second and on release/loss; the journal still requires an explicit save. Camera images, hand coordinates and grab anchors are not persisted. Restored hand-mode workspaces start paused with empty sensor state.

## Smoothing and depth

Camera palm X/Y and roll use time-based adaptive filtering: stronger at rest and faster during deliberate movement. Overlay landmarks remain matched to the current video rather than lagging behind it. Apparent palm span has its own 90 ms filter. A 0.003 normalized X/Y dead zone and 420°/300° base rotation gains are multiplied by persistent `hand_response`, default 0.55, adjustable from 0.25 to 1.25 beside the camera; small roll and relative-depth dead zones suppress jitter. These are engineering defaults requiring user evaluation, not measured optimum settings.

The browser interpolates authoritative transforms by elapsed time (35 ms time constant), using quaternion interpolation for the tooth. It stops drawing settled frames, and snaps to authoritative retained state on pause, reset or epoch changes. Mouse input remains immediate. The server remains authoritative; interpolation does not produce extra commands.

Monocular depth is inferred from **relative apparent palm size**, not metric camera Z. Turning a palm can also affect apparent size, so depth is approximate. Grab anchors reset at the current transform, size and orientation. Tool Z is bounded to [-1,1]; roll/yaw/pitch persist with workspace recovery, including migration from older 2D checkpoints.

## Functional instruments

The dental mirror uses Three.js Reflector with an offscreen scene render, not a metallic painted disc. Its starting angle bisects directions to the crown area and viewer; right-palm tilt or manual tilt sliders change the reflection. An empty reflection can mean the mirror is aimed away from the tooth. Reset restores a useful starting transform.

Explorer feedback uses the nearest point on the currently visible mesh through a cached BVH. It shows away, inside-model, or surface contact and highlights the intersection. This is a visual geometry exercise without physical force, millimetre measurements or clinical scoring. Manual mode includes **Touch visible surface** to place the tip at the camera-ray intersection when it is over the tooth. Up to eight blue contact marks follow the rotated model in the current open view; they are cleared on remount/session changes and are not saved journal annotations. Pause/disconnection disables marking. Internal tissues remain illustrative.

## Verification

Python checks cover arming without jumps, one-hand independence, naturally bent fingers, relative rotation/palm roll, simultaneous left/right movement and loss, two-pinch separation/approach zoom without rotation or depth zoom, independent right depth/orientation, legacy checkpoint migration, Hand-tool zoom priority, release/loss, stale context, reset/pause/resume, old/duplicate frames, persistence and restart. Browser checks use synthetic hand signals through real TCP/WebSocket connections to rotate the rendered tooth, move the mirror, zoom, recover from a stalled stream, block mouse transforms in hand mode and retain the transforms after reload. Physical feedback is recorded separately in PROGRESS.md; synthetic checks do not establish recognition accuracy.

Instrument browser checks also read actual reflection render-target pixels before/after removing a synthetic target, detect real sphere-surface contact/penetration, exercise the licensed model contact/mark controls and verify depth/orientation recovery. These are geometry/software checks, not human tracking or clinical validation.

## Surface boundaries and automatic tool switching

Mirror head/backing and shaft, and Explorer tip/curve/shaft use conservative bounding spheres against nearest triangle points and normals on the visible mesh. The renderer projects requested poses out of the surface and displays a boundary notice. It checks again when the tooth rotates or tissue changes, caches settled contacts and uses a bounded outward fallback for conflicting contacts. These are conservative geometry boundaries, not a calibrated physical or force simulation; a small visible stand-off can occur.

The coordinator persists requested transforms. Rendering applies the surface constraint to them on the current mesh, including after reload. Constrained rendering is local and does not send an extra sensor command or silently rewrite the user's journal. Blue surface marks attach to the model, not the requested tool pose.

The open right-hand wave cycles instruments using actual DollarPy path matching. It has independent arming, reversal/extent/speed checks, a quiet-hand latch, cooldown and server guards. [Wave controls and reference provenance](wave-control.md). The built-in authored wave reference does not populate the live V/circle/Z template library.
