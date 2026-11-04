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
      {active && state.session.tool !== "hand" && (
        <div className="hand-roles">
          <span>
            <b>Left · tooth</b>
            {state.hand_control?.roles?.left || "Open palm to rearm"}
          </span>
          <span>
            <b>Right · instrument</b>
            {state.hand_control?.roles?.right || "Open palm to rearm"}
          </span>
        </div>
      )}
      <details open={!active}>
        <summary>Hand gestures</summary>
        <ul>
          <li>
            <b>With an instrument:</b> your left hand rotates the tooth; move it
            closer to the camera to zoom in. Your right hand moves the
            instrument. Both hands work together, each with its own grip or
            pinch.
          </li>
          <li>
            <b>Instrument XYZ:</b> move right/left, up/down, or toward/away from
            the camera. Turn your right palm to tilt the mirror or explorer.
          </li>
          <li>
            <b>Hand tool:</b> either hand can grip to rotate. Two pinches and
            spreading your hands control zoom in this mode only.
          </li>
        </ul>
        <small>
          Open your hand to release. After tracking loss, open that hand before
          grabbing again. Camera depth is relative, not a physical measurement.
        </small>
      </details>
    </section>
  );
}
