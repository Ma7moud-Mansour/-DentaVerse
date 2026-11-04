import { Camera, Hand, MousePointer2 } from "lucide-react";

const WAVE_MESSAGES = {
  disabled: "Enable live hand controls and resume to wave.",
  missing: "Show your right palm to the camera.",
  partial: "Keep your whole right palm and fingertips in view.",
  open: "Open your right palm and release the pinch.",
  ready: "Ready · wave your right palm side to side twice.",
  tracking: "Reading your wave",
  cooldown: "Hold your open palm still briefly before the next wave.",
  matched: "Wave matched · switching instrument.",
  retry: "Try two clear side-to-side sweeps with your palm open.",
};

export default function HandControls({ state, send, blocked }) {
  const active = state.session.mode === "hand";
  const camera = state.services?.vision;
  const starting =
    camera?.status === "starting" ||
    camera?.status === "stopping" ||
    camera?.managed;
  const ready = state.workers.vision && state.vision.pose?.hand_tracking;
  const wave = state.vision.pose?.wave;
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
          <small>
            Left fist: tooth · Right grip/pinch: instrument · Both pinches: zoom
          </small>
        </div>
      )}
      <details open={!active}>
        <summary>Hand gestures</summary>
        <ul>
          <li>
            <b>Left hand:</b> a fist rotates the tooth. Left-hand depth does not
            zoom.
          </li>
          <li>
            <b>Instrument XYZ:</b> move right/left, up/down, or toward/away from
            the camera. Turn your right palm to tilt the mirror or explorer.
          </li>
          <li>
            <b>Change instrument:</b> wave your open right palm quickly side to
            side, twice. One wave cycles No instrument → Mirror → Explorer → No
            instrument. Hold still briefly before another wave.
          </li>
          <li>
            <b>Zoom in any tool:</b> pinch with both hands, spread to zoom in,
            bring them together to zoom out. Tooth and instrument movement stop
            during zoom. Open both palms before grabbing again.
          </li>
        </ul>
        <small>
          Open your hand to release. After tracking loss, open that hand before
          grabbing again. Camera depth is relative, not a physical measurement.
        </small>
      </details>
      {active && (
        <label className="wave-toggle">
          <input
            type="checkbox"
            aria-label="Right-hand wave switches instruments"
            checked={state.session.wave_enabled ?? true}
            disabled={blocked}
            onChange={(e) =>
              send("wave_enabled", { enabled: e.target.checked })
            }
          />
          Right-hand wave switches instruments (DollarPy)
        </label>
      )}
      {active && state.session.wave_enabled && (
        <p
          className="hand-control-feedback"
          role="status"
          aria-label="Wave recognition feedback"
          data-wave-phase={
            state.session.paused ? "paused" : (wave?.phase ?? "missing")
          }
        >
          DollarPy ·{" "}
          {state.session.paused
            ? "Resume the session to wave."
            : (WAVE_MESSAGES[wave?.phase] ?? "Waiting for the camera update…")}
          {!state.session.paused &&
            wave?.phase === "tracking" &&
            ` · ${wave.turns}/2 direction changes`}
        </p>
      )}
      {active && (
        <label className="range-label">
          Movement sensitivity ·{" "}
          {Math.round((state.session.hand_response ?? 0.55) * 100)}%
          <input
            type="range"
            min="0.25"
            max="1.25"
            step="0.05"
            aria-label="Hand movement sensitivity"
            value={state.session.hand_response ?? 0.55}
            disabled={blocked}
            onChange={(e) =>
              send("hand_response", { value: Number(e.target.value) })
            }
          />
        </label>
      )}
    </section>
  );
}
