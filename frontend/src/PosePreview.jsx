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

export default function PosePreview({
  vision,
  tracking,
  online,
  small = false,
}) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);
  const pose = vision.pose;
  const fresh = online && pose && now - pose.timestamp * 1000 < 1800;
  const points = fresh ? pose.landmarks : [];
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
    >
      <svg
        viewBox="0 0 640 480"
        role="img"
        aria-label={count ? "Live body skeleton" : "Camera position guide"}
      >
        <rect
          x="125"
          y="45"
          width="390"
          height="385"
          rx="30"
          className="pose-guide"
        />
        {BONES.map(([a, b]) =>
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
        {points.map((point, index) =>
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
        {fresh && pose.trail?.length > 1 && (
          <polyline
            className="pose-trail"
            points={pose.trail
              .map(([x, y]) => `${x * 640},${y * 480}`)
              .join(" ")}
          />
        )}
      </svg>
      {!count && (
        <div className="pose-empty">
          {online ? (
            <Hand size={small ? 36 : 62} strokeWidth={1} />
          ) : (
            <CameraOff size={small ? 30 : 52} strokeWidth={1} />
          )}
          <p>
            {!online
              ? "Start your camera to see live body points."
              : tracking === "camera_unavailable"
                ? "Camera unavailable. Check access and retry."
                : "Keep both shoulders and your chosen wrist in view."}
          </p>
        </div>
      )}
      <div className="pose-caption">
        <span className={`status-dot ${online && fresh ? "" : "offline"}`} />
        {count
          ? `${count} visible body points`
          : online
            ? "Waiting for visible body points"
            : "Camera off"}
        <span>{vision.dominant_hand} wrist</span>
      </div>
      {vision.capturing && (
        <div className="capture-indicator" role="status">
          Recording {vision.capture_name || "gesture"} ·{" "}
          {pose?.capture_points ?? 0} samples · {pose?.capture_elapsed ?? 0}s
        </div>
      )}
    </div>
  );
}
