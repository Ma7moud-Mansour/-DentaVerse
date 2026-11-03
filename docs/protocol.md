# DentaVerse local protocol v1

## TCP transport

Every frame is a 4-byte unsigned big-endian UTF-8 body length followed by that many JSON bytes. Maximum body length is 65,536 bytes. `readexactly` assembles split headers and bodies; back-to-back frames remain separate. Empty, oversized and non-object bodies are rejected. TCP workers use `127.0.0.1` only.

The first frame is `{"type":"hello","version":1,"source":"vision"}` or source `bluetooth`. The coordinator permits one connection per source and replies with `welcome` and the active session ID. Heartbeats are separate transport messages; the worker sends one every five seconds.

## Event envelope

```json
{
  "version": 1,
  "event_id": "a-fresh-uuid",
  "source": "vision",
  "type": "GESTURE_RECOGNIZED",
  "session_id": "current-session-id",
  "timestamp": 1793450000.0,
  "payload": {"name": "circle", "score": 0.86, "epoch": 4}
}
```

The timestamp above is illustrative. Send the actual current Unix timestamp. Events older than 15 seconds or more than 5 seconds in the future are rejected. UI actions and classified gestures require the current session ID. Duplicate IDs in the bounded recent-event window are acknowledged without replay. Events that fail validation are not recorded as applied.

## Source responsibilities

| Source | Events |
|---|---|
| vision | TRACKING_STATUS, VISION_STATUS, POSE_FRAME, GESTURE_RECOGNIZED, GESTURE_REJECTED |
| bluetooth | BLE_STATUS, BLE_DEVICES, USER_IDENTIFIED |
| ui | navigate, select_tooth, isolate, rotate, zoom, layer, tool, move_tool, place_tool, reset, pause, resume, set_mode, edit_note, save_session, new_session, preview_profile, confirm_identity, cancel_identity |
| ui worker controls | ble_scan, ble_connect, ble_disconnect, vision_hand, vision_calibrate, capture_start, capture_stop, capture_cancel, template_record |
| ui service controls | vision_start (camera index 0–4), vision_stop, ble_start, ble_stop |

Worker controls are validated then forwarded as a `command` frame. Their ACK says `dispatched`, meaning delivery was requested; subsequent sensor status reports provide the operation outcome. Ordinary actions receive `applied`; duplicate events receive `duplicate`; invalid worker events receive `rejected` with an error. Browser validation errors use an `error` message and leave authoritative state unchanged.

## Coordinator messages

The preview now carries `hand_tracking: true` and `hands: [...]`. It permits at most two distinct left/right IDs, exactly 21 finite x/y/z landmarks per hand, and bounded finger/pose/motion features. Each hand includes a debounced gesture state, five finger booleans, extended-finger count, normalized pinch ratio, palm center, roll and per-frame motion deltas. `score` is the handedness probability for the emitted side, not a positional-accuracy score. Missing hands must be an empty array; no prior hand pose is replayed. Body points remain in the same packet, separately selectable in the UI. See [hand signals](hand-tracking.md).

- Browser: `{"type":"state","state":{...}}` full state, including active profile, session, context, worker status and this user's journal.
- Browser preview: `{"type":"pose","session_id":"...","pose":{"landmarks":[{"x":0.4,"y":0.3,"visibility":0.9}],"trail":[],"capture_points":0,"capture_elapsed":0,"timestamp":1793450000.0}}`. The shortened example shows one point; actual landmark arrays contain **zero or 33** points. Display coordinates are mirrored; anatomical left/right indices are unchanged. Paths contain at most 200 displayed points. Valid previews use a separate bounded stream, do not enter event history, and do not write SQLite. The browser hides stale points after 1.8 seconds.
- Worker: `{"type":"context","session_id":"...","gesture_active":true,"epoch":4,"hand":"right"}`. Workers cancel a capture on context/epoch invalidation.
- Worker control: `{"type":"command","command":"capture_start","session_id":"...","epoch":4,"payload":{}}`.

POSE_FRAME may now include `image: {data: "base64 JPEG bytes", width: 640, height: 480}` for the requested local live video. The JPEG is mirrored to match the landmark display and comes from the same source frame. Width/height preserve the frame aspect ratio within 640×480; base64 data is bounded to 42,000 characters and validated as JPEG. The complete message still fits the existing 64 KiB limit. Both video and points are ephemeral, excluded from journal/checkpoint/history persistence, and discarded on worker loss. Missing image remains valid for older coordinate-only workers.

Personal participant details do not belong in protocol payloads. The latest 20 applied event labels are included for debugging. They are not research results or a durable clinical audit log.

Service controls launch only fixed Python modules, without a shell, and use the coordinator's actual TCP port. Service status is starting/running/stopping/stopped/error; managed indicates a process owned by this coordinator. Stop sends `shutdown` and waits for exit. A stuck owned process is terminated with a bounded fallback; external workers must honor shutdown or be closed by their operator. Logs are local under ignored `.review/runtime`.
