import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import {
  buildInstrument,
  positionInstrument,
  probeSurface,
  visibleSurfacePlacement,
  TOOL_SCALE,
  TOOL_DEPTH,
  constrainInstrument,
} from "./instruments";

const MODEL_URL = "/models/maxillary-first-molar-left.glb";
const clamp = THREE.MathUtils.clamp;
const degrees = THREE.MathUtils.degToRad;
const wrap = (angle) => ((((angle + 180) % 360) + 360) % 360) - 180;

function disposeObject(root) {
  const geometries = new Set(),
    materials = new Set(),
    textures = new Set();
  root.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    for (const material of object.material ? [object.material].flat() : []) {
      materials.add(material);
      for (const value of Object.values(material))
        if (value?.isTexture) textures.add(value);
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  textures.forEach((texture) => texture.dispose());
  materials.forEach((material) => material.dispose());
}

function prepareModel(source) {
  source.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(source);
  const center = bounds.getCenter(new THREE.Vector3());
  const scale = 3 / bounds.getSize(new THREE.Vector3()).y;
  const surface = new THREE.Group();
  surface.name = "surface";
  source.traverse((object) => {
    if (!object.isMesh) return;
    const geometry = object.geometry.clone();
    geometry.applyMatrix4(object.matrixWorld);
    geometry.translate(-center.x, -center.y, -center.z);
    geometry.scale(scale, scale, scale);
    const material = object.material.clone();
    material.roughness = 0.46;
    material.metalness = 0;
    const mesh = new THREE.Mesh(geometry, material);
    // Orient crown upwards, then mirror the documented left molar to the right.
    // Object-level reflection preserves correct face culling and normal maps.
    mesh.rotation.x = Math.PI;
    mesh.scale.x = -1;
    surface.add(mesh);
  });
  const specimen = new THREE.Group();
  specimen.add(surface);
  // The licensed file contains the external surface, not segmented tissues.
  // Internal views remain explicitly labelled illustrations pending review.
  const dentin = surface.clone();
  dentin.name = "dentin";
  dentin.visible = false;
  dentin.scale.setScalar(0.87);
  dentin.traverse((mesh) => {
    if (mesh.isMesh)
      mesh.material = new THREE.MeshStandardMaterial({
        color: 0xd7b273,
        roughness: 0.57,
      });
  });
  specimen.add(dentin);
  const pulp = new THREE.Group();
  pulp.name = "pulp";
  pulp.visible = false;
  const pulpMaterial = new THREE.MeshStandardMaterial({
    color: 0xc37a70,
    roughness: 0.55,
  });
  const chamber = new THREE.Mesh(
    new THREE.SphereGeometry(1, 32, 20),
    pulpMaterial,
  );
  chamber.scale.set(0.35, 0.28, 0.29);
  chamber.position.y = 0.55;
  pulp.add(chamber);
  for (const [x, z] of [
    [-0.43, -0.28],
    [0.47, -0.24],
    [0.08, 0.42],
  ]) {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(x * 0.4, 0.48, z * 0.4),
      new THREE.Vector3(x * 0.6, 0.05, z * 0.6),
      new THREE.Vector3(x * 0.9, -0.6, z * 0.9),
      new THREE.Vector3(x, -1.23, z),
    ]);
    pulp.add(
      new THREE.Mesh(
        new THREE.TubeGeometry(curve, 36, 0.045, 10, false),
        pulpMaterial,
      ),
    );
  }
  specimen.add(pulp);
  return specimen;
}

export default function Specimen({
  session,
  compact = false,
  disabled = false,
  suspended = false,
  onAction,
}) {
  const instrumentHandle = useRef(null);
  const [probe, setProbe] = useState("away");
  const [marked, setMarked] = useState(0);
  const [boundary, setBoundary] = useState(false);
  const mount = useRef(null),
    sceneRef = useRef(null);
  const latest = useRef({ session, disabled, suspended, onAction });
  latest.current = { session, disabled, suspended, onAction };
  const [loadState, setLoadState] = useState("loading");

  useEffect(() => {
    const host = mount.current;
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setLoadState("failed");
      return;
    }
    let disposed = false;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    host.appendChild(renderer.domElement);
    const canvas = renderer.domElement;
    canvas.setAttribute(
      "aria-label",
      compact ? "Molar preview" : "3D tooth viewer",
    );
    canvas.tabIndex = compact ? -1 : 0;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    camera.position.set(0, 0.1, 7.6);
    camera.lookAt(0, 0.1, 0);
    scene.add(new THREE.HemisphereLight(0xfffcf0, 0x4c665a, 2.6));
    const key = new THREE.DirectionalLight(0xfff4df, 3.2);
    key.position.set(-3, 5, 5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xe0efcf, 2);
    rim.position.set(4, 1, -2);
    scene.add(rim);
    const tooth = new THREE.Group();
    scene.add(tooth);
    const tool = buildInstrument();
    scene.add(tool);
    const contact = new THREE.Mesh(
      new THREE.SphereGeometry(0.055, 16, 12),
      new THREE.MeshBasicMaterial({ color: 0xd9f399, depthTest: false }),
    );
    contact.visible = false;
    contact.renderOrder = 10;
    scene.add(contact);
    const marks = new THREE.Group();
    tooth.add(marks);
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(1.4, 0.005, 8, 96),
      new THREE.MeshBasicMaterial({ color: 0x405d4c }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = -1.67;
    scene.add(ring);
    const view = {
      tooth,
      tool,
      camera,
      scene,
      renderer,
      drag: null,
      pending: {},
      values: {},
      lastSent: 0,
      displayedTool: null,
      lastProbe: 0,
      markers: marks,
    };
    sceneRef.current = view;
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), -0.9);
    const enabled = () =>
      !compact &&
      !latest.current.disabled &&
      latest.current.session?.isolated &&
      view.ready &&
      Boolean(latest.current.onAction);
    const draw = () => {
      if (view.ready) {
        const blocked = constrainInstrument(
          tooth,
          tool,
          latest.current.session?.tool ?? "hand",
        );
        setBoundary((old) => (old === blocked ? old : blocked));
        host.parentElement.dataset.instrumentBoundary = String(blocked);
        host.parentElement.dataset.instrumentClearance = String(
          tool.userData.clearance ?? 0,
        );
      }
      scene.updateMatrixWorld(true);
      if (
        view.ready &&
        latest.current.session?.tool === "explorer" &&
        performance.now() - view.lastProbe > 90
      ) {
        view.lastProbe = performance.now();
        const result = probeSurface(tooth, tool);
        view.probe = result;
        contact.visible = result.kind === "contact";
        if (contact.visible) contact.position.copy(result.point);
        setProbe((old) => (old === result.kind ? old : result.kind));
      } else if (latest.current.session?.tool !== "explorer")
        contact.visible = false;
      renderer.render(scene, camera);
      const handle = instrumentHandle.current;
      if (handle) {
        const point = tool
          .localToWorld(new THREE.Vector3(0, 0, 0))
          .project(camera);
        handle.style.left = `${(point.x * 0.5 + 0.5) * host.clientWidth}px`;
        handle.style.top = `${(-point.y * 0.5 + 0.5) * host.clientHeight}px`;
      }
    };
    view.draw = draw;
    const goalRotation = new THREE.Quaternion();
    view.updateTransforms = (alpha = 1) => {
      if (!view.values.rotation) return;
      const { yaw, pitch, roll = 0 } = view.values.rotation;
      goalRotation.setFromEuler(
        new THREE.Euler(
          degrees(pitch) + 0.15,
          degrees(yaw) - 0.4,
          degrees(roll),
        ),
      );
      let moving =
        tooth.quaternion.angleTo(goalRotation) > 0.0001 ||
        Math.abs(7.6 / view.values.zoom - camera.position.z) > 0.0001;
      tooth.quaternion.slerp(goalRotation, alpha);
      camera.position.z += (7.6 / view.values.zoom - camera.position.z) * alpha;
      const target = {
        ...view.values.tool_position,
        ...view.values.tool_rotation,
      };
      view.displayedTool ??= { ...target };
      for (const key of Object.keys(target)) {
        moving ||=
          Math.abs((target[key] || 0) - (view.displayedTool[key] || 0)) >
          0.0001;
        view.displayedTool[key] +=
          ((target[key] || 0) - (view.displayedTool[key] || 0)) * alpha;
      }
      const t = view.displayedTool;
      if (!moving && alpha !== 1) return false;
      positionInstrument(
        tool,
        latest.current.session?.tool ?? "hand",
        t,
        t,
        camera,
      );
      return moving;
    };
    let animation,
      previousTime = performance.now();
    const animate = (now) => {
      if (disposed) return;
      const session = latest.current.session;
      if (session?.mode === "hand" && !session.paused && view.values.rotation) {
        const dt = Math.min(0.05, (now - previousTime) / 1000);
        // Render between ~15 Hz sensor frames; no extra fixed-frame input delay.
        if (view.updateTransforms(1 - Math.exp(-dt / 0.035))) draw();
      }
      previousTime = now;
      animation = requestAnimationFrame(animate);
    };
    animation = requestAnimationFrame(animate);
    view.touchSurface = () => {
      if (!enabled() || latest.current.session.tool !== "explorer") return;
      scene.updateMatrixWorld(true);
      const point = visibleSurfacePlacement(tooth, tool, camera);
      if (!point) {
        setProbe("miss");
        return;
      }
      const tip = tool.localToWorld(new THREE.Vector3(-0.18, 0.25, 0));
      const delta = point.sub(tip);
      const p = view.values.tool_position;
      send(
        "move_tool",
        {
          x: clamp(p.x + delta.x / TOOL_SCALE, -1, 1),
          y: clamp(p.y + delta.y / TOOL_SCALE, -1, 1),
          z: clamp((p.z || 0) + delta.z / TOOL_DEPTH, -1, 1),
        },
        true,
      );
    };
    view.markContact = () => {
      if (
        latest.current.suspended ||
        latest.current.session?.paused ||
        !view.probe ||
        view.probe.kind !== "contact" ||
        view.markers.children.length >= 8
      )
        return;
      const marker = new THREE.Mesh(
        new THREE.SphereGeometry(0.045, 12, 8),
        new THREE.MeshBasicMaterial({ color: 0x88cfff, depthTest: false }),
      );
      marker.position.copy(tooth.worldToLocal(view.probe.point.clone()));
      marker.renderOrder = 9;
      marker.userData.surfaceMark = true;
      view.markers.add(marker);
      setMarked(view.markers.children.length);
      draw();
    };
    const send = (kind, payload, final = false) => {
      view.pending[kind] = { payload, at: performance.now() };
      if (final || performance.now() - view.lastSent > 45) {
        latest.current.onAction?.(kind, payload);
        view.lastSent = performance.now();
      }
    };
    function coordinates(event) {
      const rect = canvas.getBoundingClientRect();
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
    }
    function planePoint(event) {
      coordinates(event);
      return raycaster.ray.intersectPlane(plane, new THREE.Vector3());
    }
    function onDown(event, forceTool = false) {
      if (!enabled() || event.button !== 0 || view.drag) return;
      event.preventDefault();
      canvas.focus();
      coordinates(event);
      scene.updateMatrixWorld(true);
      const hits = raycaster.intersectObjects(
        tool.visible ? [tooth, tool] : [tooth],
        true,
      );
      let object = hits[0]?.object,
        isTool = forceTool;
      while (object) {
        if (object === tool) isTool = true;
        object = object.parent;
      }
      const startPoint = isTool ? planePoint(event) : null;
      view.drag = {
        id: event.pointerId,
        kind: isTool ? "move_tool" : "rotate",
        x: event.clientX,
        y: event.clientY,
        startRotation: { ...view.values.rotation },
        startPosition: { ...view.values.tool_position },
        startPoint,
        session: latest.current.session.id,
      };
      canvas.setPointerCapture(event.pointerId);
      canvas.style.cursor = "grabbing";
    }
    view.startDrag = onDown;
    function onMove(event) {
      const drag = view.drag;
      if (
        !drag ||
        event.pointerId !== drag.id ||
        !enabled() ||
        latest.current.session.id !== drag.session
      )
        return;
      if (drag.kind === "rotate") {
        const yaw = wrap(
          drag.startRotation.yaw + (event.clientX - drag.x) * 0.42,
        );
        const pitch = clamp(
          drag.startRotation.pitch + (event.clientY - drag.y) * 0.35,
          -80,
          80,
        );
        view.values.rotation = { ...view.values.rotation, yaw, pitch };
        tooth.rotation.set(
          degrees(pitch) + 0.15,
          degrees(yaw) - 0.4,
          degrees(view.values.rotation.roll || 0),
        );
        send("rotate", { yaw, pitch });
      } else {
        const point = planePoint(event);
        if (!point || !drag.startPoint) return;
        const x = clamp(
          drag.startPosition.x + (point.x - drag.startPoint.x) / 1.8,
          -1,
          1,
        );
        const y = clamp(
          drag.startPosition.y + (point.y - drag.startPoint.y) / 1.8,
          -1,
          1,
        );
        view.values.tool_position = { ...view.values.tool_position, x, y };
        view.displayedTool = null;
        view.updateTransforms();
        send("move_tool", { x, y });
      }
      draw();
    }
    function finish(event) {
      const drag = view.drag;
      if (!drag || event.pointerId !== drag.id) return;
      view.drag = null;
      if (enabled() && latest.current.session.id === drag.session)
        send(
          drag.kind,
          drag.kind === "rotate"
            ? view.values.rotation
            : view.values.tool_position,
          true,
        );
      if (canvas.hasPointerCapture(drag.id))
        canvas.releasePointerCapture(drag.id);
      canvas.style.cursor = enabled() ? "grab" : "default";
    }
    function onWheel(event) {
      if (!enabled()) return;
      event.preventDefault();
      const unit =
        event.deltaMode === 1
          ? 16
          : event.deltaMode === 2
            ? canvas.clientHeight
            : 1;
      const value =
        Math.round(
          clamp(
            view.values.zoom * Math.exp(-event.deltaY * unit * 0.0014),
            0.6,
            1.8,
          ) * 100,
        ) / 100;
      view.values.zoom = value;
      camera.position.z = 7.6 / value;
      send("zoom", { value }, true);
      draw();
    }
    function onKey(event) {
      if (!enabled()) return;
      const rotation = { ...view.values.rotation };
      if (event.key === "ArrowLeft") rotation.yaw = wrap(rotation.yaw - 5);
      else if (event.key === "ArrowRight")
        rotation.yaw = wrap(rotation.yaw + 5);
      else if (event.key === "ArrowUp")
        rotation.pitch = clamp(rotation.pitch - 5, -80, 80);
      else if (event.key === "ArrowDown")
        rotation.pitch = clamp(rotation.pitch + 5, -80, 80);
      else if (["+", "=", "-"].includes(event.key)) {
        event.preventDefault();
        const value = clamp(
          view.values.zoom + (event.key === "-" ? -0.1 : 0.1),
          0.6,
          1.8,
        );
        view.values.zoom = value;
        camera.position.z = 7.6 / value;
        send("zoom", { value }, true);
        draw();
        return;
      } else return;
      event.preventDefault();
      view.values.rotation = rotation;
      tooth.rotation.set(
        degrees(rotation.pitch) + 0.15,
        degrees(rotation.yaw) - 0.4,
        0,
      );
      send("rotate", rotation, true);
      draw();
    }
    const onUp = (event) => finish(event),
      onCancel = (event) => finish(event);
    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("pointercancel", onCancel);
    canvas.addEventListener("lostpointercapture", onCancel);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("keydown", onKey);
    function resize() {
      if (!host.clientWidth || !host.clientHeight) return;
      renderer.setSize(host.clientWidth, host.clientHeight);
      camera.aspect = host.clientWidth / host.clientHeight;
      camera.updateProjectionMatrix();
      draw();
    }
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();
    new GLTFLoader().load(
      MODEL_URL,
      (gltf) => {
        if (disposed) {
          disposeObject(gltf.scene);
          return;
        }
        tooth.add(prepareModel(gltf.scene));
        view.ready = true;
        gltf.scene.traverse((object) => {
          object.geometry?.dispose();
          object.material?.dispose();
        });
        setLoadState("ready");
        draw();
      },
      undefined,
      () => {
        if (!disposed) setLoadState("failed");
      },
    );
    return () => {
      disposed = true;
      cancelAnimationFrame(animation);
      tool.userData.reflector.dispose();
      observer.disconnect();
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("pointercancel", onCancel);
      canvas.removeEventListener("lostpointercapture", onCancel);
      canvas.removeEventListener("wheel", onWheel);
      canvas.removeEventListener("keydown", onKey);
      disposeObject(scene);
      renderer.dispose();
      canvas.remove();
      sceneRef.current = null;
    };
  }, [compact]);

  useEffect(() => {
    const view = sceneRef.current;
    if (!view) return;
    const { tooth, tool, camera, scene, renderer } = view;
    const actual = {
      rotation: session?.rotation ?? { yaw: 0, pitch: 0 },
      tool_position: session?.tool_position ?? { x: 0.7, y: 0, z: 0 },
      tool_rotation: session?.tool_rotation ?? { yaw: 0, pitch: 0, roll: 0 },
      zoom: session?.zoom ?? 1,
    };
    const snap =
      view.session !== session?.id ||
      view.epoch !== session?.gesture_epoch ||
      session?.paused;
    if (disabled || view.session !== session?.id) {
      view.drag = null;
      view.pending = {};
    }
    if (view.session !== session?.id) {
      view.markers.children.forEach((m) => {
        m.geometry.dispose();
        m.material.dispose();
      });
      view.markers.clear();
      setMarked(0);
    }
    view.session = session?.id;
    view.epoch = session?.gesture_epoch;
    view.values.tool_rotation = actual.tool_rotation;
    for (const [kind, key] of [
      ["rotate", "rotation"],
      ["move_tool", "tool_position"],
      ["zoom", "zoom"],
    ]) {
      const pending = view.pending[kind],
        payload = kind === "zoom" ? { value: actual.zoom } : actual[key];
      const acknowledged =
        pending &&
        Object.keys(pending.payload).every(
          (name) => Math.abs(pending.payload[name] - payload[name]) < 0.0001,
        );
      if (!pending || acknowledged || performance.now() - pending.at > 1500) {
        view.values[key] = actual[key];
        delete view.pending[kind];
      }
    }

    const layer = session?.layer ?? "surface";
    tooth.traverse((object) => {
      if (["surface", "dentin", "pulp"].includes(object.name))
        object.visible =
          object.name === (layer === "enamel" ? "surface" : layer);
    });
    if (session?.mode !== "hand" || snap) {
      view.displayedTool = null;
      view.updateTransforms();
      view.lastProbe = 0;
    }
    renderer.domElement.style.cursor =
      compact || disabled ? "default" : view.drag ? "grabbing" : "grab";
    const signature = JSON.stringify({
      ...actual,
      layer,
      tool: session?.tool,
      paused: session?.paused,
      epoch: session?.gesture_epoch,
      loadState,
    });
    if (view.drawSignature !== signature) {
      view.drawSignature = signature;
      view.draw();
    }
  }, [session, disabled, compact, loadState]);

  const internal = session?.layer === "dentin" || session?.layer === "pulp";
  return (
    <div
      className={`specimen ${compact ? "compact" : ""}`}
      data-model-state={loadState}
    >
      <div ref={mount} className="three-mount" />
      {!compact && session?.tool !== "hand" && !disabled && (
        <button
          className="instrument-grab"
          ref={instrumentHandle}
          aria-label="Drag selected instrument"
          title="Drag to move instrument; arrow keys also move it"
          onPointerDown={(event) => sceneRef.current?.startDrag(event, true)}
          onKeyDown={(event) => {
            if (!event.key.startsWith("Arrow")) return;
            event.preventDefault();
            const position = { ...session.tool_position };
            if (event.key === "ArrowLeft")
              position.x = clamp(position.x - 0.1, -1, 1);
            if (event.key === "ArrowRight")
              position.x = clamp(position.x + 0.1, -1, 1);
            if (event.key === "ArrowUp")
              position.y = clamp(position.y + 0.1, -1, 1);
            if (event.key === "ArrowDown")
              position.y = clamp(position.y - 0.1, -1, 1);
            onAction?.("move_tool", position);
          }}
        >
          <span aria-hidden="true">✥</span>
        </button>
      )}
      {!compact && session?.tool !== "hand" && (
        <div
          className="instrument-readout"
          aria-label="Instrument feedback"
          data-probe={session?.tool === "explorer" ? probe : "reflection"}
        >
          <strong>
            {session?.tool === "mirror"
              ? "Live mirror reflection"
              : probe === "contact"
                ? "Tip touching the surface"
                : probe === "inside"
                  ? "Tip inside model · move outward"
                  : probe === "miss"
                    ? "Move the tip over the tooth first"
                    : "Bring the explorer tip to the surface"}
          </strong>
          <span>
            {session?.tool === "mirror"
              ? "Move XYZ and tilt your right palm to change the reflected view."
              : "The contact marker follows the visible mesh. No force or clinical score is measured."}
          </span>
          {boundary && (
            <small className="instrument-boundary" role="status">
              Surface boundary reached · move around the tooth
            </small>
          )}
          {session?.tool === "explorer" && (
            <div className="instrument-actions">
              {session.mode !== "hand" && (
                <button
                  disabled={disabled}
                  onClick={() => sceneRef.current?.touchSurface()}
                >
                  Touch visible surface
                </button>
              )}
              <button
                disabled={
                  suspended ||
                  session.paused ||
                  probe !== "contact" ||
                  marked >= 8
                }
                onClick={() => sceneRef.current?.markContact()}
              >
                Mark contact ({marked}/8)
              </button>
              {marked > 0 && (
                <button
                  onClick={() => {
                    const v = sceneRef.current;
                    v.markers.children.forEach((m) => {
                      m.geometry.dispose();
                      m.material.dispose();
                    });
                    v.markers.clear();
                    setMarked(0);
                    v.draw();
                  }}
                >
                  Clear marks
                </button>
              )}
            </div>
          )}
          {marked > 0 && <small>Marks belong to this open view.</small>}
        </div>
      )}
      {loadState === "loading" && (
        <div className="canvas-fallback" role="status">
          Loading the molar…
        </div>
      )}
      {loadState === "failed" && (
        <div className="canvas-fallback" role="status">
          The 3D model could not load. Refresh the workspace to try again.
        </div>
      )}
      {!compact && (
        <>
          <span className="specimen-label">FDI 16 / UPPER RIGHT</span>
          <div className="viewer-instructions">
            {session?.mode === "hand" ? (
              <>
                {session.tool === "hand"
                  ? "Grip to rotate · Two pinches to zoom"
                  : "Left hand: tooth · Right hand: instrument XYZ"}
              </>
            ) : (
              <>
                Drag tooth to rotate <span>·</span> Drag instrument to move{" "}
                <span>·</span> Scroll to zoom
              </>
            )}
          </div>
          <div className="model-credit">
            <a
              href="https://sketchfab.com/3d-models/maxillary-first-molar-e719a474ef7e4bd7abec508f85f1e984"
              target="_blank"
              rel="noreferrer"
            >
              University of Dundee
            </a>{" "}
            ·{" "}
            <a
              href="https://creativecommons.org/licenses/by/4.0/"
              target="_blank"
              rel="noreferrer"
            >
              CC BY 4.0
            </a>
            <span>
              {internal
                ? "Illustrative internal layer · review pending"
                : "Mirrored educational model · anatomy review pending"}
            </span>
          </div>
          {!internal && (
            <>
              <span className="anatomy-label crown-label">Crown</span>
              <span className="anatomy-label root-label">Roots</span>
            </>
          )}
        </>
      )}
    </div>
  );
}
