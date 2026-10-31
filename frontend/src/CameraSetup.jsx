import { useState } from "react";
import { ArrowRight, Camera, Check, ScanLine, Square } from "lucide-react";
import PosePreview from "./PosePreview";

export default function CameraSetup({ state, send, onContinue }) {
  const [camera, setCamera] = useState(0);
  const { vision } = state;
  const supported = Boolean(state.services);
  const service = state.services?.vision ?? { status: "stopped" };
  const active =
    state.workers.vision ||
    ["starting", "running", "stopping"].includes(service.status);
  const collecting = vision.calibration_status === "collecting";
  const ready = state.tracking === "ready" && vision.calibrated;
  return (
    <div className="setup-grid">
      <section className="camera-card">
        <div className="section-heading">
          <div className="eyebrow">Live body tracking</div>
          <span className="tag dark">
            {service.status === "starting"
              ? "Starting camera…"
              : state.workers.vision && state.tracking === "lost"
                ? "Camera on · position your shoulders and wrist"
                : state.tracking.replaceAll("_", " ")}
          </span>
        </div>
        <PosePreview
          vision={vision}
          tracking={state.tracking}
          online={state.workers.vision}
        />
        <p className="camera-caption">
          Live camera video with body points, shown only in this local
          workspace.
          <br />
          Video is not recorded. Saving a gesture stores its coordinate path
          only.
        </p>
      </section>
      <section className="card setup-checks">
        <div className="eyebrow">Ready when you are</div>
        <h2>A good start</h2>
        <div className="camera-buttons">
          <button
            className="button"
            disabled={!supported || active}
            onClick={() => send("vision_start", { camera })}
          >
            <Camera size={15} />
            {service.status === "starting" ? "Starting…" : "Start camera"}
          </button>
          <button
            className="button secondary"
            disabled={!active || service.status === "stopping"}
            onClick={() => send("vision_stop")}
          >
            <Square size={13} />
            {service.status === "stopping" ? "Stopping…" : "Stop camera"}
          </button>
        </div>
        <label className="field-label">
          Camera
          <select
            aria-label="Camera device"
            value={camera}
            disabled={!supported || active}
            onChange={(event) => setCamera(Number(event.target.value))}
          >
            <option value={0}>Default camera</option>
            {[1, 2, 3, 4].map((value) => (
              <option key={value} value={value}>
                Other camera {value}
              </option>
            ))}
          </select>
        </label>
        <ReadyLine
          checked={state.workers.vision}
          title="Camera connected"
          text="Ready to receive body points"
        />
        <ReadyLine
          checked={state.tracking === "ready"}
          title="Shoulders and wrist visible"
          text="Keep your chosen wrist inside the frame"
        />
        <ReadyLine
          checked={vision.calibrated}
          title="Stable position calibrated"
          text="Hold your upper body still during calibration"
        />
        <label className="field-label">
          Preferred hand
          <select
            aria-label="Preferred hand"
            value={vision.dominant_hand}
            disabled={!supported || vision.capturing || collecting}
            onChange={(event) =>
              send("vision_hand", { hand: event.target.value })
            }
          >
            <option value="right">Right hand</option>
            <option value="left">Left hand</option>
          </select>
        </label>
        <button
          className="button secondary"
          onClick={() =>
            send("vision_calibrate", { hand: vision.dominant_hand })
          }
          disabled={
            !supported ||
            !state.workers.vision ||
            state.tracking !== "ready" ||
            collecting ||
            vision.capturing
          }
        >
          {collecting ? "Hold your position…" : "Calibrate position"}
          <ScanLine size={16} />
        </button>
        {collecting && (
          <div className="calibration-progress">
            <progress
              aria-label="Calibration progress"
              max="1"
              value={vision.calibration_progress || 0}
            />
            <small>
              Keep both shoulders and your {vision.dominant_hand} wrist visible.
              Wait for stable calibration.
            </small>
          </div>
        )}
        <button
          className="button"
          disabled={!supported || !ready || collecting}
          onClick={() => {
            send("set_mode", { mode: "gesture" });
            onContinue();
          }}
        >
          Enter with gestures
          <ArrowRight size={16} />
        </button>
        <button
          className="text-button"
          onClick={() => {
            send("set_mode", { mode: "manual" });
            onContinue();
          }}
        >
          Continue with mouse & keyboard
        </button>
        {(vision.error || service.error) && (
          <p className="inline-error" role="status">
            {vision.error || service.error}
          </p>
        )}
        {!supported && (
          <p role="status">
            Restart the local server to enable the updated camera controls.
          </p>
        )}
      </section>
    </div>
  );
}

function ReadyLine({ checked, title, text }) {
  return (
    <div className="status-line">
      <span className={`check-icon ${checked ? "checked" : ""}`}>
        {checked ? <Check size={13} /> : "○"}
      </span>
      <div>
        <strong>{title}</strong>
        <small>{text}</small>
      </div>
    </div>
  );
}
