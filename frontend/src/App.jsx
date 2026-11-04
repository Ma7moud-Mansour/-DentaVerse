import { useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowLeft,
  BookOpen,
  Camera,
  Check,
  ChevronRight,
  CircleHelp,
  Home,
  Layers,
  RotateCcw,
  Search,
  Settings2,
  Sparkles,
  Bluetooth,
  Hand,
  Pause,
  Play,
  X,
  Wifi,
  WifiOff,
  ScanLine,
  GraduationCap,
} from "lucide-react";
import { useWorkbench } from "./useWorkbench";
import Specimen from "./Specimen";
import CameraSetup from "./CameraSetup";
import PosePreview from "./PosePreview";
import HandControls from "./HandControls";

const TOOLS = [
  ["hand", "Hand control"],
  ["mirror", "Dental mirror"],
  ["explorer", "Explorer"],
];
const LAYERS = [
  ["surface", "Surface"],
  ["enamel", "Enamel"],
  ["dentin", "Dentin"],
  ["pulp", "Pulp"],
];
const PROFILES = [
  ["DV-STUDENT-01", "Beginning learner"],
  ["DV-STUDENT-02", "Experienced learner"],
  ["DV-TEACHER-01", "Teaching demonstrator"],
];
const TASKS = [
  ["located", "Locate tooth 16"],
  ["inspected", "Inspect the specimen"],
  ["mirror_placed", "Position the mirror"],
];

function Button({ children, secondary = false, className = "", ...props }) {
  return (
    <button
      className={`button ${secondary ? "secondary" : ""} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
function Eyebrow({ children }) {
  return <div className="eyebrow">{children}</div>;
}

export default function App() {
  const { state, connected, send, error, clearError } = useWorkbench();
  const [note, setNote] = useState(""),
    [reset, setReset] = useState(false),
    [query, setQuery] = useState("");
  const [savedNotice, setSavedNotice] = useState(false);
  const s = state?.session;
  useEffect(() => {
    setNote(s?.note ?? "");
    setSavedNotice(false);
  }, [s?.id]);
  useEffect(() => {
    setSavedNotice(Boolean(s?.saved));
  }, [s?.saved]);
  useEffect(() => {
    if (s?.mode === "hand" && s?.screen === "workbench") {
      document.querySelector(".inspector")?.scrollTo({ top: 0 });
    }
  }, [s?.mode, s?.screen]);
  useEffect(() => {
    if (reset || state?.pending_identity || s?.paused) {
      const el = document.querySelector('[role="dialog"] button');
      el?.focus();
    }
  }, [reset, state?.pending_identity, s?.paused]);

  if (!state)
    return (
      <main className="loading">
        <Logo />
        <h1>Opening your workbench</h1>
        <p>
          Connecting to the local coordinator. Start the server if this message
          remains.
        </p>
        <code>
          python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
        </code>
      </main>
    );
  const go = (screen) => send("navigate", { screen });
  const active = s.screen;
  const workbench = active === "workbench";
  const checkpoints = s.checkpoints.length;
  const sceneBlocked = !connected || s.paused;
  const nav = [
    ["studio", Home, "Studio"],
    ["atlas", Layers, "Anatomy atlas"],
    ["setup", Camera, "Session setup"],
    ["journal", BookOpen, "Session journal"],
  ];

  return (
    <div className={`app ${workbench ? "workbench-app" : ""}`}>
      {!workbench && (
        <aside className="sidebar">
          <Logo />
          <Eyebrow>Workspace</Eyebrow>
          <nav aria-label="Workspace navigation">
            {nav.map(([id, Icon, label]) => (
              <button
                key={id}
                className={`nav-item ${active === id ? "active" : ""}`}
                onClick={() => go(id)}
                disabled={!connected}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <button
              className={`nav-item ${active === "guide" ? "active" : ""}`}
              onClick={() => go("guide")}
              disabled={!connected}
            >
              <Hand size={18} />
              Gesture guide
            </button>
            <button
              className={`nav-item ${active === "preferences" ? "active" : ""}`}
              onClick={() => go("preferences")}
              disabled={!connected}
            >
              <Settings2 size={18} />
              Preferences
            </button>
            <div className="user">
              <span className="avatar">
                {state.profile.level === "demonstrator" ? "TD" : "DV"}
              </span>
              <div>
                <strong>{state.profile.name}</strong>
                <small>
                  {state.identity_source === "bluetooth"
                    ? "Identified over Bluetooth"
                    : state.identity_source === "manual_preview"
                      ? "Manual profile preview"
                      : state.identity_source === "restored_session"
                        ? "Restored local session"
                        : "Manual guest session"}
                </small>
              </div>
            </div>
          </div>
        </aside>
      )}
      <div className="main-shell">
        <header className="topbar">
          {workbench ? (
            <>
              <Logo />
              <button
                className="back-link"
                onClick={() => go("studio")}
                disabled={!connected}
              >
                <ArrowLeft size={15} /> Studio
              </button>
              <div className="header-title">
                <Eyebrow>Anatomy / permanent dentition</Eyebrow>
                <span>Explore the first molar</span>
              </div>
            </>
          ) : (
            <span className="topbar-copy">Dental learning, in your hands.</span>
          )}
          <div className="header-status">
            <span className={`status-dot ${connected ? "" : "offline"}`} />
            {connected
              ? workbench
                ? "Guided session"
                : "Local workspace"
              : "Reconnecting…"}
          </div>
          {workbench && (
            <>
              <Button
                secondary
                onClick={() => go("guide")}
                disabled={!connected}
              >
                <Hand size={14} />
                Gesture guide
              </Button>
              <Button
                secondary
                onClick={() => send("pause")}
                disabled={!connected || s.paused}
              >
                Pause session <Pause size={14} />
              </Button>
            </>
          )}
        </header>
        {!connected && (
          <div className="connection-banner" role="status">
            <WifiOff size={16} />
            Connection lost. Changes are disabled until the workspace
            reconnects.
          </div>
        )}
        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <button aria-label="Dismiss error" onClick={clearError}>
              <X size={16} />
            </button>
          </div>
        )}
        <fieldset
          disabled={!connected}
          className="workspace-fieldset"
          inert={reset || state.pending_identity || s.paused ? true : undefined}
        >
          {active === "studio" && (
            <main className="page studio">
              <Eyebrow>Your dental workbench</Eyebrow>
              <div className="hero">
                <div className="hero-copy">
                  <h1>
                    Knowledge,
                    <br />
                    within reach.
                  </h1>
                  <p>
                    Explore dental anatomy through movement.
                    <br />
                    Choose a specimen. Make it your own.
                  </p>
                  <div className="button-row">
                    <Button onClick={() => go("atlas")}>
                      Open anatomy atlas
                      <ArrowRight size={17} />
                    </Button>
                    <Button secondary onClick={() => go("setup")}>
                      Set up gestures
                    </Button>
                  </div>
                </div>
                <div className="hero-specimen">
                  <Eyebrow>The specimen series</Eyebrow>
                  <Specimen compact />
                  <div className="specimen-caption">
                    <div>
                      <strong>Upper right first molar</strong>
                      <small>Educational anatomy model</small>
                    </div>
                    <span>16</span>
                  </div>
                </div>
              </div>
              <section className="continue-section">
                <div className="section-heading">
                  <h2>Continue your practice</h2>
                  <Eyebrow>01 / Anatomy foundations</Eyebrow>
                </div>
                <div className="practice-row">
                  <article className="card practice-card">
                    <div className="tooth-symbol">♧</div>
                    <div>
                      <Eyebrow>Guided exercise 01</Eyebrow>
                      <h3>Explore the first molar</h3>
                      <p>3 checkpoints · One focused specimen</p>
                    </div>
                    <Button
                      secondary
                      onClick={() => go(s.isolated ? "workbench" : "atlas")}
                    >
                      View exercise <ArrowRight size={15} />
                    </Button>
                  </article>
                  <article className="gesture-promo">
                    <Hand size={23} />
                    <h3>New to gestures?</h3>
                    <p>A short guide to working in the air.</p>
                    <button onClick={() => go("guide")}>
                      Learn the gestures <ArrowRight size={15} />
                    </button>
                  </article>
                </div>
              </section>
              <div className="studio-footer">
                <span>Designed for focused, hands-on learning.</span>
                <span>DentaVerse / Personal studio</span>
              </div>
            </main>
          )}
          {active === "atlas" && (
            <main className="page">
              <Eyebrow>Anatomy atlas</Eyebrow>
              <h1>A closer look starts here.</h1>
              <p className="lede">
                Explore the dentition, then isolate a specimen for focused
                study.
              </p>
              <label className="search">
                <Search size={18} />
                <input
                  placeholder="Search by tooth name or FDI number"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <kbd>/</kbd>
              </label>
              <div className="chips">
                <span>Permanent dentition</span>
                <span>Upper arch</span>
                <span>First molar</span>
              </div>
              {!query || /16|molar|upper|right/i.test(query) ? (
                <div className="atlas-grid">
                  <article className="card tooth-map-card">
                    <Eyebrow>Permanent dentition / FDI map</Eyebrow>
                    <h2>Find your specimen.</h2>
                    <p>Choose the upper-right first molar to begin.</p>
                    <ToothMap
                      selected={s.selected_tooth}
                      select={() => send("select_tooth", { tooth: 16 })}
                    />
                    <div className="map-key">
                      <span className="status-dot" />
                      16 / Upper-right first molar
                    </div>
                    <small>This delivery contains the tooth 16 activity.</small>
                  </article>
                  <article className="card specimen-card">
                    <Specimen compact />
                    <div className="section-heading">
                      <div>
                        <h3>16 / First molar</h3>
                        <small>Upper right · Permanent</small>
                      </div>
                      <span className="tag">Study specimen</span>
                    </div>
                    <Button
                      onClick={() => {
                        if (s.selected_tooth !== 16)
                          send("select_tooth", { tooth: 16 });
                        send("isolate");
                      }}
                    >
                      Inspect specimen <ArrowRight size={17} />
                    </Button>
                  </article>
                </div>
              ) : (
                <div className="empty-state">
                  <Search size={30} />
                  <h2>No specimen matches that search.</h2>
                  <p>Try “16” or “first molar”.</p>
                  <Button secondary onClick={() => setQuery("")}>
                    Clear search
                  </Button>
                </div>
              )}
            </main>
          )}
          {active === "workbench" && (
            <main className="workbench">
              <div className="tool-rail" aria-label="Workbench actions">
                <button
                  title="Back to atlas"
                  aria-label="Back to atlas"
                  onClick={() => go("atlas")}
                >
                  <Layers size={21} />
                </button>
                <button
                  title="View tissue layers"
                  aria-label="View tissue layers"
                  onClick={() =>
                    send("layer", {
                      layer: s.layer === "surface" ? "enamel" : "surface",
                    })
                  }
                  disabled={sceneBlocked || !s.isolated}
                >
                  <ScanLine size={21} />
                </button>
                <button
                  title="Select mirror"
                  aria-label="Select mirror"
                  onClick={() => send("toggle_tool", { tool: "mirror" })}
                  disabled={sceneBlocked || !s.isolated}
                >
                  <Search size={21} />
                </button>
                <button
                  title="Reset view"
                  aria-label="Reset view"
                  onClick={() => setReset(true)}
                  disabled={sceneBlocked}
                >
                  <RotateCcw size={21} />
                </button>
              </div>
              <section className="specimen-stage">
                <div className="stage-heading">
                  <Eyebrow>Specimen / {s.selected_tooth ?? "—"}</Eyebrow>
                  <h2>
                    {s.isolated
                      ? "Upper right first molar"
                      : "Choose a tooth to begin"}
                  </h2>
                  <button
                    className="stage-reset"
                    onClick={() => setReset(true)}
                    disabled={sceneBlocked}
                  >
                    Reset view <RotateCcw size={13} />
                  </button>
                </div>
                <Specimen
                  session={s}
                  suspended={sceneBlocked || !s.isolated}
                  disabled={sceneBlocked || !s.isolated || s.mode === "hand"}
                  onAction={send}
                />
                <div className="stage-toolbar">
                  <span>
                    {s.tool === "hand" ? "Hand control" : `${s.tool} / active`}
                  </span>
                  <button onClick={() => go("atlas")}>
                    Return to dentition <ArrowRight size={15} />
                  </button>
                </div>
              </section>
              <aside className="inspector">
                {s.mode === "hand" && (
                  <section
                    className="live-hand-workbench"
                    aria-label="Live hand workspace"
                  >
                    <HandControls
                      state={state}
                      send={send}
                      blocked={sceneBlocked}
                    />
                    <PosePreview
                      vision={state.vision}
                      tracking={state.tracking}
                      online={state.workers.vision}
                      small
                    />
                  </section>
                )}
                <Eyebrow>Specimen</Eyebrow>
                <div className="specimen-identity">
                  <span>16</span>
                  <div>
                    Upper right
                    <br />
                    <strong>First molar</strong>
                  </div>
                </div>
                <p className="muted">Permanent · Maxillary</p>
                <div className="inspector-section">
                  <Eyebrow>Current task</Eyebrow>
                  <h3>{state.content.title}</h3>
                  <p>{state.content.task}</p>
                  <ol className="checkpoints">
                    {TASKS.map(([id, label], i) => (
                      <li key={id}>
                        <span
                          className={s.checkpoints.includes(id) ? "done" : ""}
                        >
                          {s.checkpoints.includes(id) ? (
                            <Check size={12} />
                          ) : (
                            i + 1
                          )}
                        </span>
                        {label}
                      </li>
                    ))}
                  </ol>
                </div>
                <div className="inspector-section">
                  <Eyebrow>Tissue explorer</Eyebrow>
                  <div className="segment">
                    {LAYERS.map(([id, label]) => (
                      <button
                        key={id}
                        aria-pressed={s.layer === id}
                        className={s.layer === id ? "selected" : ""}
                        disabled={sceneBlocked || !s.isolated}
                        onClick={() => send("layer", { layer: id })}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <p>
                    <strong>{state.content.layer_title}.</strong>{" "}
                    {state.content.layer_text}
                  </p>
                </div>
                <div className="inspector-section">
                  <Eyebrow>View controls</Eyebrow>
                  <Range
                    label="Turn specimen"
                    min={-180}
                    max={180}
                    value={s.rotation.yaw}
                    unit="°"
                    disabled={sceneBlocked || !s.isolated || s.mode === "hand"}
                    onChange={(yaw) =>
                      send("rotate", { yaw, pitch: s.rotation.pitch })
                    }
                  />
                  <Range
                    label="Tilt specimen"
                    min={-80}
                    max={80}
                    value={s.rotation.pitch}
                    unit="°"
                    disabled={sceneBlocked || !s.isolated || s.mode === "hand"}
                    onChange={(pitch) =>
                      send("rotate", { yaw: s.rotation.yaw, pitch })
                    }
                  />
                  <Range
                    label="Zoom"
                    min={0.6}
                    max={1.8}
                    step={0.1}
                    value={s.zoom}
                    unit="×"
                    disabled={sceneBlocked || !s.isolated || s.mode === "hand"}
                    onChange={(value) => send("zoom", { value })}
                  />
                  <Range
                    label="Roll specimen"
                    min={-180}
                    max={180}
                    value={s.rotation.roll ?? 0}
                    unit="°"
                    disabled={sceneBlocked || !s.isolated || s.mode === "hand"}
                    onChange={(roll) => send("rotate", { ...s.rotation, roll })}
                  />
                </div>
                <div className="inspector-section">
                  <Eyebrow>Instrument tray</Eyebrow>
                  <div
                    className="segment"
                    role="group"
                    aria-label="Instrument shortcuts"
                  >
                    {TOOLS.filter(([id]) => id !== "hand").map(
                      ([id, label]) => (
                        <button
                          key={id}
                          aria-label={`Toggle ${label}`}
                          aria-pressed={s.tool === id}
                          className={s.tool === id ? "selected" : ""}
                          disabled={sceneBlocked || !s.isolated}
                          onClick={() => send("toggle_tool", { tool: id })}
                        >
                          {label}
                          {s.tool === id ? " · remove" : ""}
                        </button>
                      ),
                    )}
                    <button
                      disabled={sceneBlocked || !s.isolated}
                      onClick={() => send("cycle_tool")}
                      aria-label="Next instrument"
                    >
                      Next instrument
                    </button>
                  </div>
                  <p className="muted">
                    Click the selected instrument again to remove it.
                  </p>
                  <label className="field-label">
                    Active tool
                    <select
                      aria-label="Active tool"
                      value={s.tool}
                      disabled={sceneBlocked || !s.isolated}
                      onChange={(e) => send("tool", { tool: e.target.value })}
                    >
                      {TOOLS.map(([id, label]) => (
                        <option key={id} value={id}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p>{state.content.tool_help}</p>
                  {s.tool !== "hand" && (
                    <>
                      <Range
                        label="Tool horizontal position"
                        min={-1}
                        max={1}
                        step={0.1}
                        value={s.tool_position.x}
                        disabled={sceneBlocked || s.mode === "hand"}
                        onChange={(x) =>
                          send("move_tool", { x, y: s.tool_position.y })
                        }
                      />
                      <Range
                        label="Tool vertical position"
                        min={-1}
                        max={1}
                        step={0.1}
                        value={s.tool_position.y}
                        disabled={sceneBlocked || s.mode === "hand"}
                        onChange={(y) =>
                          send("move_tool", { x: s.tool_position.x, y })
                        }
                      />
                      <Button
                        secondary
                        disabled={sceneBlocked || s.tool !== "mirror"}
                        onClick={() => send("place_tool")}
                      >
                        Confirm mirror placement <Check size={14} />
                      </Button>
                      <Range
                        label="Tool depth"
                        min={-1}
                        max={1}
                        step="any"
                        value={s.tool_position.z ?? 0}
                        disabled={sceneBlocked || s.mode === "hand"}
                        onChange={(z) => send("move_tool", { z })}
                      />
                      <Range
                        label="Tool tilt horizontal"
                        min={-80}
                        max={80}
                        value={s.tool_rotation?.yaw ?? 0}
                        unit="°"
                        disabled={sceneBlocked || s.mode === "hand"}
                        onChange={(yaw) => send("move_tool", { yaw })}
                      />
                      <Range
                        label="Tool tilt vertical"
                        min={-80}
                        max={80}
                        value={s.tool_rotation?.pitch ?? 0}
                        unit="°"
                        disabled={sceneBlocked || s.mode === "hand"}
                        onChange={(pitch) => send("move_tool", { pitch })}
                      />
                      <Range
                        label="Tool roll"
                        min={-180}
                        max={180}
                        value={s.tool_rotation?.roll ?? 0}
                        unit="°"
                        disabled={sceneBlocked || s.mode === "hand"}
                        onChange={(roll) => send("move_tool", { roll })}
                      />
                    </>
                  )}
                </div>
                <div className="inspector-section">
                  <Eyebrow>Gesture control</Eyebrow>
                  {s.mode !== "hand" && (
                    <>
                      <HandControls
                        state={state}
                        send={send}
                        blocked={sceneBlocked}
                      />
                      {state.workers.vision && (
                        <PosePreview
                          vision={state.vision}
                          tracking={state.tracking}
                          online={state.workers.vision}
                          small
                        />
                      )}
                    </>
                  )}
                  <button className="text-button" onClick={() => go("setup")}>
                    Camera setup
                  </button>
                  <details open={s.mode === "gesture"}>
                    <summary>Recorded gesture paths</summary>
                    <div className="button-row">
                      <Button
                        secondary
                        disabled={
                          sceneBlocked ||
                          s.mode !== "gesture" ||
                          state.vision.capturing ||
                          state.vision.pending_capture
                        }
                        onClick={() => send("capture_start")}
                      >
                        Record gesture
                      </Button>
                      <Button
                        secondary
                        disabled={!state.vision.capturing}
                        onClick={() => send("capture_stop")}
                      >
                        Recognize
                      </Button>
                    </div>
                  </details>
                  {state.last_gesture && (
                    <p role="status">
                      {state.last_gesture.name}
                      {state.last_gesture.reason
                        ? `: ${state.last_gesture.reason}`
                        : ` · match ${state.last_gesture.score.toFixed(2)}`}
                    </p>
                  )}
                </div>
                <Button onClick={() => go("review")}>
                  Finish & review <ArrowRight size={16} />
                </Button>
              </aside>
            </main>
          )}
          {active === "setup" && (
            <main className="page">
              <Eyebrow>Session setup / camera and identity</Eyebrow>
              <h1>Your hands are the interface.</h1>
              <p className="lede">
                Connect your identity, then prepare a comfortable space for
                movement.
              </p>
              <CameraSetup
                state={state}
                send={send}
                onContinue={() => go("atlas")}
              />
              <BluetoothPanel state={state} send={send} />
            </main>
          )}
          {active === "review" && (
            <main className="page">
              <Eyebrow>Session review</Eyebrow>
              <h1>One specimen. A clearer understanding.</h1>
              <p className="lede">
                Explore the first molar / Guided exercise 01
              </p>
              <div className="review-grid">
                <section className="review-score">
                  <Eyebrow>Interaction checkpoints</Eyebrow>
                  <div className="score">
                    {checkpoints}
                    <span>/3</span>
                  </div>
                  <p>checkpoints explored</p>
                  <div className="review-specimen">
                    <Specimen compact />
                  </div>
                  <strong>16 / Upper right first molar</strong>
                  <small>
                    Progress records interaction, not clinical proficiency.
                  </small>
                </section>
                <section className="card">
                  <Eyebrow>What you explored</Eyebrow>
                  <div className="review-tasks">
                    {TASKS.map(([id, label]) => (
                      <StatusLine
                        key={id}
                        checked={s.checkpoints.includes(id)}
                        title={label}
                        text={
                          id === "located"
                            ? "Selected and isolated tooth 16."
                            : id === "inspected"
                              ? "Changed the specimen viewing angle."
                              : "Confirmed the virtual mirror position."
                        }
                      />
                    ))}
                  </div>
                  <label className="field-label" htmlFor="reflection">
                    Reflect before you move on
                    <textarea
                      id="reflection"
                      value={note}
                      onChange={(e) => {
                        setNote(e.target.value);
                        setSavedNotice(false);
                        send("edit_note", { note: e.target.value });
                      }}
                      placeholder="What did you notice about the specimen?"
                      maxLength={4000}
                    />
                  </label>
                  <div className="button-row">
                    <Button onClick={() => send("save_session", { note })}>
                      Save reflection <Check size={16} />
                    </Button>
                    <Button secondary onClick={() => go("journal")}>
                      Open journal <ArrowRight size={16} />
                    </Button>
                  </div>
                  {savedNotice && (
                    <p className="saved-notice" role="status">
                      <Check size={15} />
                      Reflection saved to this user's journal.
                    </p>
                  )}
                </section>
              </div>
              <Button
                secondary
                onClick={() => go(s.isolated ? "workbench" : "atlas")}
              >
                Return to the specimen <ArrowLeft size={16} />
              </Button>
            </main>
          )}
          {active === "journal" && (
            <main className="page">
              <Eyebrow>Session journal</Eyebrow>
              <h1>Your learning, kept together.</h1>
              <p className="lede">
                A record of the specimens you explored and the questions worth
                revisiting.
              </p>
              {state.journal.length ? (
                <div className="journal-list">
                  {state.journal.map((entry) => (
                    <article className="card journal-entry" key={entry.id}>
                      <div className="section-heading">
                        <div>
                          <Eyebrow>FDI 16 / First molar</Eyebrow>
                          <h2>Explore the first molar</h2>
                        </div>
                        <span className="tag">
                          {entry.data.checkpoints.length}/3 checkpoints
                        </span>
                      </div>
                      <p className="journal-note">
                        {entry.note || "No reflection added."}
                      </p>
                      <small>
                        Saved {entry.saved_at} UTC · {state.profile.name}
                      </small>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <BookOpen size={42} strokeWidth={1} />
                  <h2>Nothing recorded yet.</h2>
                  <p>
                    Your completed explorations and reflections will appear
                    here.
                  </p>
                  <Button onClick={() => go("atlas")}>
                    Start your first exercise <ArrowRight size={16} />
                  </Button>
                </div>
              )}
            </main>
          )}
          {active === "guide" && (
            <main className="page">
              <Eyebrow>Interaction guide</Eyebrow>
              <h1>A few gestures. A familiar rhythm.</h1>
              <p className="lede">
                Record one deliberate path at a time, then ask the recognizer to
                match it.
              </p>
              <div className="gesture-grid">
                {[
                  [
                    "↔",
                    "Switch instruments with a wave",
                    "In Live hand controls, wave your open right palm quickly side to side twice. No instrument → Mirror → Explorer → No instrument. Hold still briefly before another wave.",
                  ],
                  [
                    "V",
                    "Confirm your selection",
                    "Select tooth 16, then draw a V to isolate it. With the mirror active, V confirms its placement.",
                  ],
                  [
                    "○",
                    "Explore the tissue layers",
                    "Draw a circle to open enamel exploration on an isolated specimen.",
                  ],
                  [
                    "Z",
                    "Pause the session",
                    "Draw a Z to stop interaction and retain the scene. Resume explicitly when ready.",
                  ],
                ].map(([shape, title, copy]) => (
                  <article className="card gesture-card" key={shape}>
                    <span className="gesture-shape">{shape}</span>
                    <h2>{title}</h2>
                    <p>{copy}</p>
                  </article>
                ))}
              </div>
              <div className="notice">
                <CircleHelp size={22} />
                <p>
                  DollarPy matches movement paths. The right-hand wave is ready
                  in Live hand controls. V, circle and Z use your recorded
                  templates: collect them in Preferences before using Camera
                  gestures. Direction alone does not distinguish a gesture.
                </p>
              </div>
              <Button onClick={() => go(s.isolated ? "workbench" : "setup")}>
                Try it in the workbench <ArrowRight size={16} />
              </Button>
            </main>
          )}
          {active === "preferences" && (
            <main className="page">
              <Eyebrow>Preferences / learning context</Eyebrow>
              <h1>Make room for your way of working.</h1>
              <p className="lede">
                Keep your input mode and learning guidance explicit.
              </p>
              <section className="card preferences-card">
                <div className="section-heading">
                  <div>
                    <h2>Input mode</h2>
                    <p>
                      Use the mouse and keyboard, or enable calibrated gesture
                      controls.
                    </p>
                  </div>
                  <select
                    aria-label="Input mode"
                    value={s.mode}
                    onChange={(e) => send("set_mode", { mode: e.target.value })}
                  >
                    <option value="manual">Mouse & keyboard</option>
                    <option
                      value="hand"
                      disabled={
                        !state.workers.vision ||
                        !state.vision.pose?.hand_tracking
                      }
                    >
                      Live hand controls
                    </option>
                    <option value="gesture">Camera gestures</option>
                  </select>
                </div>
                <div className="preference-row">
                  <div>
                    <h3>Manual profile preview</h3>
                    <p>
                      Inspect the different learning content without a Bluetooth
                      device. This does not count as sensor identification.
                    </p>
                  </div>
                  <select
                    aria-label="Manual profile preview"
                    value={state.profile.id === "guest" ? "" : state.profile.id}
                    onChange={(e) =>
                      send("preview_profile", { user_id: e.target.value })
                    }
                  >
                    <option value="" disabled>
                      Select a learning profile
                    </option>
                    {PROFILES.map(([id, label]) => (
                      <option key={id} value={id}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="notice">
                  <GraduationCap size={24} />
                  <div>
                    <strong>{state.content.title}</strong>
                    <p>{state.content.description}</p>
                    <ul>
                      {state.content.prompts.map((p) => (
                        <li key={p}>{p}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </section>
              <section className="card template-card">
                <Eyebrow>Gesture template collection</Eyebrow>
                <h2>Teach the recognizer your movements.</h2>
                <PosePreview
                  vision={state.vision}
                  tracking={state.tracking}
                  online={state.workers.vision}
                  small
                />
                <button className="text-button" onClick={() => go("setup")}>
                  Open camera setup
                </button>
                <p>
                  Calibrate first. Choose a shape, draw it in view, then save
                  the capture. Ask permission before collecting another person's
                  trajectories.
                </p>
                <div className="button-row">
                  {["V", "circle", "Z"].map((name) => (
                    <Button
                      key={name}
                      secondary
                      onClick={() => send("template_record", { name })}
                      disabled={
                        !state.vision.calibrated ||
                        state.tracking !== "ready" ||
                        state.vision.capturing ||
                        state.vision.pending_capture
                      }
                    >
                      Record {name} ({state.vision.template_counts[name] ?? 0})
                    </Button>
                  ))}
                  <Button
                    onClick={() => send("capture_stop")}
                    disabled={!state.vision.capturing}
                  >
                    Save capture <Check size={15} />
                  </Button>
                  <Button
                    secondary
                    onClick={() => send("capture_cancel")}
                    disabled={!state.vision.capturing}
                  >
                    Cancel
                  </Button>
                </div>
                <small>
                  Templates contain coordinate paths, not camera frames. Counts
                  remain zero until real captures are saved.
                </small>
                {state.last_gesture?.reason && (
                  <p role="status">{state.last_gesture.reason}</p>
                )}
              </section>
              <BluetoothPanel state={state} send={send} />
            </main>
          )}
        </fieldset>
        <footer className="statusbar">
          <div>
            <span
              className={`status-dot ${(s.mode === "hand" ? state.workers.vision && state.vision.pose?.hands?.length : state.tracking === "ready") ? "" : "offline"}`}
            />
            {s.mode === "manual"
              ? "Manual input"
              : s.mode === "hand"
                ? "Hand controls"
                : "Pose tracking"}
            <span className="status-divider" />
            {s.mode === "manual"
              ? "Mouse & keyboard"
              : s.mode === "hand"
                ? (state.hand_control?.phase ?? "waiting")
                : state.tracking.replace("_", " ")}
            <span className="status-divider" />
            <Bluetooth size={12} />
            {state.bluetooth.status}
          </div>
          <span>
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />} Local
            session ·{" "}
            {state.identity_source === "bluetooth"
              ? "Bluetooth identity"
              : state.identity_source === "restored_session"
                ? "Restored identity"
                : "Manual identity"}
          </span>
        </footer>
      </div>
      {(reset || state.pending_identity || s.paused) && (
        <div
          className="modal-backdrop"
          onKeyDown={(e) => {
            if (e.key === "Tab") {
              const buttons = [
                ...e.currentTarget.querySelectorAll("button:not(:disabled)"),
              ];
              const first = buttons[0],
                last = buttons.at(-1);
              if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last?.focus();
              } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first?.focus();
              }
            }
            if (e.key === "Escape" && reset) setReset(false);
          }}
        >
          <section
            className="modal card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
          >
            {reset ? (
              <>
                <RotateCcw size={30} />
                <h2 id="dialog-title">Reset this specimen?</h2>
                <p>
                  The view and instrument position return to their starting
                  points. Your saved notes remain in the journal.
                </p>
                <div className="button-row">
                  <Button secondary onClick={() => setReset(false)}>
                    Keep working
                  </Button>
                  <Button
                    onClick={() => {
                      send("reset", { confirm: true });
                      setReset(false);
                    }}
                    disabled={!connected}
                  >
                    Reset specimen
                  </Button>
                </div>
              </>
            ) : state.pending_identity ? (
              <>
                <Bluetooth size={30} />
                <h2 id="dialog-title">Switch learning profiles?</h2>
                <p>
                  Another identity is ready. Save your current session first, or
                  explicitly discard its unsaved progress.
                </p>
                <div className="button-row">
                  <Button
                    secondary
                    onClick={() => send("cancel_identity")}
                    disabled={!connected}
                  >
                    Keep current profile
                  </Button>
                  <Button
                    onClick={() => {
                      send("save_session", { note });
                      send("confirm_identity", { discard: true });
                    }}
                    disabled={!connected}
                  >
                    Save & switch
                  </Button>
                  <Button
                    secondary
                    onClick={() => send("confirm_identity", { discard: true })}
                    disabled={!connected}
                  >
                    Discard & switch
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Hand size={32} />
                <h2 id="dialog-title">
                  {s.pause_reason === "tracking"
                    ? "Let’s get your hand back."
                    : "Take a moment."}
                </h2>
                <p>{state.content.recovery}</p>
                <div className="button-row">
                  <Button
                    secondary
                    onClick={() => {
                      send("set_mode", { mode: "manual" });
                      send("resume");
                    }}
                    disabled={!connected}
                  >
                    Use manual controls
                  </Button>
                  <Button
                    onClick={() => send("resume")}
                    disabled={
                      !connected ||
                      (s.mode === "hand" &&
                        (!state.workers.vision ||
                          !state.vision.pose?.hand_tracking ||
                          Date.now() / 1000 - state.vision.pose.timestamp >
                            0.8)) ||
                      (s.mode === "gesture" && state.tracking !== "ready")
                    }
                  >
                    Resume session <Play size={14} />
                  </Button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function Logo() {
  return (
    <div className="logo">
      <span className="logo-mark">∪</span>DentaVerse
    </div>
  );
}
function Range({ label, value, unit = "", onChange, ...props }) {
  return (
    <label className="range-label">
      <span>
        {label}
        <output>
          {Number(value).toFixed(unit === "°" ? 0 : unit === "×" ? 1 : 2)}
          {unit}
        </output>
      </span>
      <input
        type="range"
        aria-label={label}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        {...props}
      />
    </label>
  );
}
function StatusLine({ checked, title, text }) {
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
function ToothMap({ selected, select }) {
  return (
    <div className="tooth-map" aria-label="FDI permanent tooth map">
      <div className="quadrant">
        Upper right<span>Upper left</span>
      </div>
      <div className="teeth-row">
        {[18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28].map(
          (n) => (
            <button
              key={n}
              aria-label={`Tooth ${n}`}
              aria-pressed={selected === n}
              disabled={n !== 16}
              className={selected === n ? "selected" : ""}
              onClick={select}
            >
              {n}
            </button>
          ),
        )}
      </div>
      <div className="teeth-row lower">
        {[48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38].map(
          (n) => (
            <button
              key={n}
              aria-label={`Tooth ${n}, unavailable in this activity`}
              disabled
            >
              {n}
            </button>
          ),
        )}
      </div>
      <div className="quadrant">
        Lower right<span>Lower left</span>
      </div>
    </div>
  );
}
function BluetoothPanel({ state, send }) {
  const service = state.services?.bluetooth ?? { status: "stopped" };
  const active =
    state.workers.bluetooth ||
    service.managed ||
    ["starting", "running", "stopping"].includes(service.status);
  return (
    <section className="card bluetooth-panel">
      <div className="section-heading">
        <div>
          <Eyebrow>Bluetooth identity</Eyebrow>
          <h2>Pick up where you belong.</h2>
          <p>
            Discover a DentaVerse peripheral and read its registered application
            ID.
          </p>
          <p>
            Turn Bluetooth on in Windows first. This service finds DentaVerse
            BLE peripherals; ordinary paired devices are not listed here.
          </p>
        </div>
        <Bluetooth size={28} />
      </div>
      <div className="button-row">
        <Button
          secondary
          disabled={!state.services || active}
          onClick={() => send("ble_start")}
        >
          {service.status === "starting"
            ? "Starting…"
            : "Start Bluetooth service"}
        </Button>
        <Button
          secondary
          disabled={!active || service.status === "stopping"}
          onClick={() => send("ble_stop")}
        >
          {service.status === "stopping"
            ? "Stopping…"
            : "Stop Bluetooth service"}
        </Button>
        <Button
          secondary
          onClick={() => send("ble_scan")}
          disabled={
            !state.workers.bluetooth || state.bluetooth.status === "scanning"
          }
        >
          {state.bluetooth.status === "scanning"
            ? "Scanning…"
            : "Discover devices"}
          <Search size={15} />
        </Button>
        <span className="tag">{state.bluetooth.status}</span>
      </div>
      {state.bluetooth.devices.map((device) => (
        <div className="device-row" key={device.id}>
          <strong>{device.name}</strong>
          <Button
            secondary
            onClick={() => send("ble_connect", { device_id: device.id })}
          >
            Connect & read ID <ArrowRight size={14} />
          </Button>
        </div>
      ))}
      {state.bluetooth.status === "connected" && (
        <Button secondary onClick={() => send("ble_disconnect")}>
          Disconnect peripheral
        </Button>
      )}
      {state.bluetooth.error && (
        <p className="inline-error" role="status">
          {state.bluetooth.error}
        </p>
      )}
      {service.error && (
        <p className="inline-error" role="status">
          {service.error}
        </p>
      )}
      {!state.services && (
        <p role="status">Restart the local server to enable service buttons.</p>
      )}
      <small>
        Device discovery runs only when you select Discover devices.
      </small>
    </section>
  );
}
