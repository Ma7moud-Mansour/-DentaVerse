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
| vision | TRACKING_STATUS, VISION_STATUS, GESTURE_RECOGNIZED, GESTURE_REJECTED |
| bluetooth | BLE_STATUS, BLE_DEVICES, USER_IDENTIFIED |
| ui | navigate, select_tooth, isolate, rotate, zoom, layer, tool, move_tool, place_tool, reset, pause, resume, set_mode, save_session, new_session, preview_profile, confirm_identity, cancel_identity |
| ui worker controls | ble_scan, ble_connect, ble_disconnect, vision_calibrate, capture_start, capture_stop, capture_cancel, template_record |

Worker controls are validated then forwarded as a `command` frame. Their ACK says `dispatched`, meaning delivery was requested; subsequent sensor status reports provide the operation outcome. Ordinary actions receive `applied`; duplicate events receive `duplicate`; invalid worker events receive `rejected` with an error. Browser validation errors use an `error` message and leave authoritative state unchanged.

## Coordinator messages

- Browser: `{"type":"state","state":{...}}` full state, including active profile, session, context, worker status and this user's journal.
- Worker: `{"type":"context","session_id":"...","gesture_active":true,"epoch":4}`. Workers cancel a capture on context/epoch invalidation.
- Worker control: `{"type":"command","command":"capture_start","session_id":"...","epoch":4,"payload":{}}`.

No camera frames or personal participant details belong in these messages. The latest 20 applied event labels are included for debugging. They are not research results or a durable clinical audit log.
