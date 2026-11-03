import { Camera, Hand, MousePointer2 } from "lucide-react";

export default function HandControls({ state, send, blocked }) {
  const active = state.session.mode === "hand";
  const camera = state.services?.vision;
  const starting =
    camera?.status === "starting" ||
    camera?.status === "stopping" ||
    camera?.managed;
  const ready = state.workers.vision && state.vision.pose?.hand_tracking;
  return (
    <section
      className={`hand-controls ${active ? "hand-controls-active" : ""}`}
      aria-label="Hand controls"
    >
      <strong>Move it with your hands</strong>
      {!state.workers.vision && (
        <button
          className="button secondary"
          disabled={blocked || starting}
          onClick={() => send("vision_start", { camera: 0 })}
        >
          <Camera size={14} />
          {starting ? "Starting camera…" : "Start camera"}
        </button>
      )}
      <button
        className="button"
        disabled={blocked || !state.hand_control || (!active && !ready)}
        onClick={() => send("set_mode", { mode: active ? "manual" : "hand" })}
      >
        {active ? <MousePointer2 size={14} /> : <Hand size={14} />}{" "}
        {active ? "Use mouse & keyboard" : "Enable hand controls"}
      </button>
      <p
        className="hand-control-feedback"
        role="status"
        aria-label="Hand control feedback"
      >
        {active
          ? state.hand_control?.message
          : "Enable, then show an open palm to take control."}
      </p>
      <details open={!active}>
        <summary>Hand gestures</summary>
        <ul>
          <li>
            <b>Rotate:</b> close your hand and move or turn it. With Hand
            selected, a pinch also grabs the tooth.
          </li>
          <li>
            <b>Move an instrument:</b> select Mirror or Explorer, then pinch and
            move.
          </li>
          <li>
            <b>Zoom:</b> pinch with both hands and spread them apart or bring
            them together.
          </li>
        </ul>
        <small>
          Open your hand to release. After zooming or tracking loss, open your
          hands before grabbing again.
        </small>
      </details>
    </section>
  );
}
