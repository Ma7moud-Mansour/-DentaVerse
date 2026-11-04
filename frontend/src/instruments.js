import * as THREE from "three";
import { Reflector } from "three/addons/objects/Reflector.js";

export const TOOL_SCALE = 1.8;
export const TOOL_DEPTH = 1.6;
export const TIP = new THREE.Vector3(-0.18, 0.25, 0);

export function buildInstrument() {
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
  grip.position.y = -0.65;
  tool.add(grip);
  const mirror = new THREE.Group();
  const backing = new THREE.Mesh(
    new THREE.CylinderGeometry(0.38, 0.38, 0.035, 48),
    metal,
  );
  backing.rotation.x = Math.PI / 2;
  backing.position.z = -0.025;
  mirror.add(backing);
  mirror.add(
    new THREE.Mesh(new THREE.TorusGeometry(0.37, 0.022, 12, 64), metal),
  );
  const reflector = new Reflector(new THREE.CircleGeometry(0.35, 64), {
    color: 0xe5ece6,
    clipBias: 0.003,
    textureWidth: 768,
    textureHeight: 768,
    multisample: 0,
  });
  reflector.position.z = 0.002;
  mirror.add(reflector);
  tool.add(mirror);
  const explorer = new THREE.Mesh(
    new THREE.TubeGeometry(
      new THREE.CatmullRomCurve3([
        new THREE.Vector3(0, -0.1, 0),
        new THREE.Vector3(0, 0.27, 0),
        new THREE.Vector3(-0.13, 0.35, 0),
        TIP.clone(),
      ]),
      32,
      0.014,
      8,
      false,
    ),
    metal,
  );
  tool.add(explorer);
  tool.userData.reflector = reflector;
  return tool;
}

export function positionInstrument(tool, kind, position, rotation, camera) {
  tool.visible = kind !== "hand";
  tool.children[1].visible = kind === "mirror";
  tool.children[2].visible = kind === "explorer";
  tool.position.set(
    position.x * TOOL_SCALE,
    position.y * TOOL_SCALE,
    0.9 + (position.z || 0) * TOOL_DEPTH,
  );
  tool.rotation.set(0, 0, 0);
  if (kind === "mirror") {
    // Bisect rays to the tooth and viewer, so the actual reflected view starts useful.
    // Relative palm tilt then lets the learner change the mirror's angle.
    const towardTooth = new THREE.Vector3(0, 0.55, 0)
      .sub(tool.position)
      .normalize();
    const towardViewer = camera.position.clone().sub(tool.position).normalize();
    const normal = towardTooth.add(towardViewer);
    if (normal.lengthSq() < 0.001) normal.set(1, 0, 0.2);
    tool.lookAt(tool.position.clone().add(normal.normalize()));
  }
  tool.rotateY(THREE.MathUtils.degToRad(rotation.yaw || 0));
  tool.rotateX(THREE.MathUtils.degToRad(rotation.pitch || 0));
  tool.rotateZ(THREE.MathUtils.degToRad(rotation.roll || 0) - 0.35);
  tool.updateMatrixWorld(true);
}

export function visibleSurfaces(tooth) {
  const surfaces = [];
  tooth.traverseVisible((o) => {
    if (o.isMesh && !o.userData.surfaceMark) surfaces.push(o);
  });
  return surfaces;
}

export function probeSurface(tooth, tool) {
  const tip = tool.localToWorld(TIP.clone());
  const center = tooth.getWorldPosition(new THREE.Vector3());
  const outward = tip.clone().sub(center);
  const distance = outward.length();
  if (distance < 0.001) return { kind: "inside", tip };
  outward.normalize();
  // A radial approach test on the visible mesh. No clinical force/distance score.
  const ray = new THREE.Raycaster(
    center.clone().addScaledVector(outward, 5),
    outward.clone().negate(),
    0,
    10,
  );
  const hit = ray.intersectObjects(visibleSurfaces(tooth), false)[0];
  if (!hit) return { kind: "away", tip };
  const gap = distance - hit.point.distanceTo(center);
  return {
    kind: Math.abs(gap) < 0.065 ? "contact" : gap < 0 ? "inside" : "away",
    tip,
    point: hit.point,
    gap,
  };
}

export function visibleSurfacePlacement(tooth, tool, camera) {
  const tip = tool.localToWorld(TIP.clone());
  const screen = tip.clone().project(camera);
  const ray = new THREE.Raycaster();
  ray.setFromCamera(new THREE.Vector2(screen.x, screen.y), camera);
  return ray.intersectObjects(visibleSurfaces(tooth), false)[0]?.point ?? null;
}
