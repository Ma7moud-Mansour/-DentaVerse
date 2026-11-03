import { useEffect, useState } from "react";
import { Hand, CameraOff } from "lucide-react";

const BONES = [
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28],
  [27, 29],
  [29, 31],
  [28, 30],
  [30, 32],
];
const HAND_BONES = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 4],
  [0, 5],
  [5, 6],
  [6, 7],
  [7, 8],
  [5, 9],
  [9, 10],
  [10, 11],
  [11, 12],
  [9, 13],
  [13, 14],
  [14, 15],
  [15, 16],
  [13, 17],
  [0, 17],
  [17, 18],
  [18, 19],
  [19, 20],
];
const GESTURES = {
  stabilizing: "Hold briefly…",
  open_palm: "Open palm",
  fist: "Closed fist",
  pinch: "Pinch",
  neutral: "Neutral",
  partial: "Show all fingertips",
};

export default function PosePreview({
  vision,
  tracking,
  online,
  small = false,
}) {
  const [now, setNow] = useState(Date.now());
  const [overlay, setOverlay] = useState("hands");
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);
  const pose = vision.pose;
  const fresh = online && pose && now - pose.timestamp * 1000 < 1800;
  const points = fresh ? pose.landmarks : [];
  const image = fresh ? pose.image : null;
  const handTracking = pose?.hand_tracking === true;
  const hands = fresh ? (pose.hands ?? []) : [];
  const showBody = !handTracking || overlay !== "hands";
  const showHands = overlay !== "body";
  const visible = (index) =>
    points[index]?.visibility >= 0.5 &&
    points[index].x >= 0 &&
    points[index].x <= 1 &&
    points[index].y >= 0 &&
    points[index].y <= 1;
  const count = points.filter((_, index) => visible(index)).length;
  const wrist = vision.dominant_hand === "left" ? 15 : 16;
  return (
    <div
      className={`pose-preview ${small ? "pose-small" : ""}`}
      data-live-joints={count}
      data-live-hands={hands.length}
    >
      {handTracking && (
        <div
          className="pose-overlay-controls"
          role="group"
          aria-label="Tracking overlay"
        >
          {["hands", "body", "both"].map((mode) => (
            <button
              key={mode}
              aria-pressed={overlay === mode}
              onClick={() => setOverlay(mode)}
            >
              {mode === "hands" ? "Hands" : mode === "body" ? "Body" : "Both"}
            </button>
          ))}
        </div>
      )}
      <div
        className="pose-picture"
        style={{
          aspectRatio: image ? `${image.width} / ${image.height}` : "4 / 3",
        }}
      >
        {image && (
          <img
            className="pose-video"
            src={`data:image/jpeg;base64,${image.data}`}
            alt="Live camera video"
            draggable={false}
          />
        )}
        <svg
          viewBox="0 0 640 480"
          preserveAspectRatio="none"
          role="img"
          aria-label={
            showHands && hands.length
              ? "Live hand skeletons"
              : showBody && count
                ? "Live body skeleton"
                : "Camera position guide"
          }
        >
          {showBody && (
            <rect
              x="125"
              y="45"
              width="390"
              height="385"
              rx="30"
              className="pose-guide"
            />
          )}
          {showBody &&
            BONES.map(([a, b]) =>
              visible(a) && visible(b) ? (
                <line
                  key={`${a}-${b}`}
                  x1={points[a].x * 640}
                  y1={points[a].y * 480}
                  x2={points[b].x * 640}
                  y2={points[b].y * 480}
                  className="pose-bone"
                />
              ) : null,
            )}
          {showBody &&
            points.map((point, index) =>
              visible(index) ? (
                <circle
                  key={index}
                  cx={point.x * 640}
                  cy={point.y * 480}
                  r={index === wrist ? 9 : 4}
                  className={index === wrist ? "pose-wrist" : "pose-joint"}
                />
              ) : null,
            )}
          {showHands &&
            hands.map((hand) => (
              <g
                key={hand.id}
                className={`hand-skeleton hand-${hand.id}`}
                data-testid={`skeleton-${hand.id}`}
              >
                {HAND_BONES.map(([a, b]) => (
                  <line
                    key={`${a}-${b}`}
                    x1={hand.landmarks[a].x * 640}
                    y1={hand.landmarks[a].y * 480}
                    x2={hand.landmarks[b].x * 640}
                    y2={hand.landmarks[b].y * 480}
                  />
                ))}
                {hand.landmarks.map((point, index) => (
                  <circle
                    key={index}
                    cx={point.x * 640}
                    cy={point.y * 480}
                    r={[4, 8, 12, 16, 20].includes(index) ? 5 : 3.5}
                  />
                ))}
                <text
                  x={Math.min(560, Math.max(10, hand.landmarks[0].x * 640))}
                  y={Math.min(
                    465,
                    Math.max(22, hand.landmarks[0].y * 480 + 22),
                  )}
                >
                  {hand.id === "left" ? "Left" : "Right"}
                </text>
              </g>
            ))}
          {fresh && showBody && pose.trail?.length > 1 && (
            <polyline
              className="pose-trail"
              points={pose.trail
                .map(([x, y]) => `${x * 640},${y * 480}`)
                .join(" ")}
            />
          )}
        </svg>
        {!count && !image && (
          <div className="pose-empty">
            {online ? (
              <Hand size={small ? 36 : 62} strokeWidth={1} />
            ) : (
              <CameraOff size={small ? 30 : 52} strokeWidth={1} />
            )}
            <p>
              {!online
                ? "Start your camera to see live video and hands."
                : tracking === "camera_unavailable"
                  ? "Camera unavailable. Check access and retry."
                  : "Keep both shoulders and your chosen wrist in view."}
            </p>
          </div>
        )}
        {image &&
          ((handTracking && showHands && !hands.length) ||
            (!handTracking && !count)) && (
            <div className="pose-position-hint">
              {handTracking
                ? "Show both palms and all fingertips inside the frame."
                : "Keep both shoulders and your chosen wrist in view."}
            </div>
          )}
      </div>
      <div className="pose-caption">
        <span className={`status-dot ${online && fresh ? "" : "offline"}`} />
        {handTracking && showHands
          ? `${hands.length}/2 hands · ${hands.length * 21} hand points`
          : count
            ? `${count} visible body points`
            : online
              ? "Waiting for visible body points"
              : "Camera off"}
        <span>{vision.dominant_hand} wrist</span>
      </div>
      {handTracking && (
        <div className="hand-readouts">
          {["left", "right"].map((side) => {
            const hand = hands.find((item) => item.id === side);
            return (
              <div
                key={side}
                className={`hand-readout hand-${side}`}
                data-testid={`hand-${side}`}
              >
                <strong>{side === "left" ? "Left hand" : "Right hand"}</strong>
                <span>{hand ? GESTURES[hand.gesture] : "Not visible"}</span>
                {hand && (
                  <>
                    <small>
                      {hand.extended_fingers}/5 fingers · Roll{" "}
                      {Math.round(hand.roll)}°
                    </small>
                    <div
                      className="finger-indicators"
                      aria-label={`${side} finger states`}
                    >
                      {Object.entries(hand.fingers).map(([name, extended]) => (
                        <span
                          key={name}
                          className={extended ? "extended" : ""}
                          title={`${name}: ${extended ? "extended" : "curled"}`}
                        >
                          {name.slice(0, 1).toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
      {vision.capturing && (
        <div className="capture-indicator" role="status">
          Recording {vision.capture_name || "gesture"} ·{" "}
          {pose?.capture_points ?? 0} samples · {pose?.capture_elapsed ?? 0}s
        </div>
      )}
    </div>
  );
}
