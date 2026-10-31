import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

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

function buildInstrument() {
  const tool = new THREE.Group();
  const metal = new THREE.MeshStandardMaterial({
    color: 0xc5d3cb,
    metalness: 0.75,
    roughness: 0.25,
  });
  const grip = new THREE.Mesh(
    new THREE.CylinderGeometry(0.038, 0.045, 1.12, 20),
    metal,
  );
  grip.position.y = -0.5;
  tool.add(grip);
  const mirror = new THREE.Group();
  mirror.add(
    new THREE.Mesh(new THREE.TorusGeometry(0.205, 0.025, 12, 40), metal),
  );
  mirror.add(
    new THREE.Mesh(
      new THREE.CircleGeometry(0.19, 40),
      new THREE.MeshStandardMaterial({
        color: 0xb7d1cd,
        metalness: 0.8,
        roughness: 0.14,
        side: THREE.DoubleSide,
      }),
    ),
  );
  mirror.position.y = 0.18;
  tool.add(mirror);
  tool.add(
    new THREE.Mesh(
      new THREE.TubeGeometry(
        new THREE.CatmullRomCurve3([
          new THREE.Vector3(0, 0.06, 0),
          new THREE.Vector3(0, 0.27, 0),
          new THREE.Vector3(-0.13, 0.35, 0),
          new THREE.Vector3(-0.18, 0.25, 0),
        ]),
        24,
        0.015,
        8,
        false,
      ),
      metal,
    ),
  );
  tool.rotation.z = -0.35;
  return tool;
}

export default function Specimen({
  session,
  compact = false,
  disabled = false,
  onAction,
}) {
  const instrumentHandle = useRef(null);
  const mount = useRef(null),
    sceneRef = useRef(null);
  const latest = useRef({ session, disabled, onAction });
  latest.current = { session, disabled, onAction };
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
      renderer.render(scene, camera);
      const handle = instrumentHandle.current;
      if (handle) {
        const point = tool
          .localToWorld(new THREE.Vector3(0, 0.18, 0))
          .project(camera);
        handle.style.left = `${(point.x * 0.5 + 0.5) * host.clientWidth}px`;
        handle.style.top = `${(-point.y * 0.5 + 0.5) * host.clientHeight}px`;
      }
    };
    view.draw = draw;
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
        view.values.rotation = { yaw, pitch };
        tooth.rotation.set(degrees(pitch) + 0.15, degrees(yaw) - 0.4, 0);
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
        view.values.tool_position = { x, y };
        tool.position.set(x * 1.8, y * 1.8, 0.9);
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
      tool_position: session?.tool_position ?? { x: 0.7, y: 0 },
      zoom: session?.zoom ?? 1,
    };
    if (disabled || view.session !== session?.id) {
      view.drag = null;
      view.pending = {};
    }
    view.session = session?.id;
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
    const { yaw, pitch } = view.values.rotation;
    tooth.rotation.set(degrees(pitch) + 0.15, degrees(yaw) - 0.4, 0);
    const layer = session?.layer ?? "surface";
    tooth.traverse((object) => {
      if (["surface", "dentin", "pulp"].includes(object.name))
        object.visible =
          object.name === (layer === "enamel" ? "surface" : layer);
    });
    tool.visible = Boolean(session?.tool && session.tool !== "hand");
    tool.children[1].visible = session?.tool === "mirror";
    tool.children[2].visible = session?.tool === "explorer";
    tool.position.set(
      view.values.tool_position.x * 1.8,
      view.values.tool_position.y * 1.8,
      0.9,
    );
    camera.position.z = 7.6 / view.values.zoom;
    renderer.domElement.style.cursor =
      compact || disabled ? "default" : view.drag ? "grabbing" : "grab";
    view.draw();
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
            Drag tooth to rotate <span>·</span> Drag instrument to move{" "}
            <span>·</span> Scroll to zoom
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
