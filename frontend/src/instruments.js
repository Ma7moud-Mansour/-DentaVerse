import * as THREE from "three";
import { Reflector } from "three/addons/objects/Reflector.js";
import { MeshBVH, getTriangleHitPointInfo } from "three-mesh-bvh";

export const TOOL_SCALE = 1.8;
export const TOOL_DEPTH = 1.6;
export const TIP = new THREE.Vector3(-0.18, 0.25, 0);
const EXPLORER_CURVE = new THREE.CatmullRomCurve3([
  new THREE.Vector3(0, -0.1, 0),
  new THREE.Vector3(0, 0.27, 0),
  new THREE.Vector3(-0.13, 0.35, 0),
  TIP.clone(),
]);
const SHAFT = Array.from({ length: 9 }, (_, i) => ({
  point: new THREE.Vector3(0, -0.09 - i * 0.14, 0),
  radius: 0.085,
}));
const MIRROR_BOUNDS = [{ point: new THREE.Vector3(), radius: 0.4 }, ...SHAFT];
const EXPLORER_BOUNDS = [
  ...Array.from({ length: 25 }, (_, i) => ({
    point: EXPLORER_CURVE.getPoint(i / 24),
    radius: 0.025,
  })),
  ...SHAFT,
];

export function instrumentBounds(kind) {
  return kind === "mirror" ? MIRROR_BOUNDS : EXPLORER_BOUNDS;
}

export function nearestSurface(tooth, worldPoint) {
  let result = null;
  for (const mesh of visibleSurfaces(tooth)) {
    const geometry = mesh.geometry;
    geometry.boundsTree ??= new MeshBVH(geometry, { maxLeafSize: 10 });
    const local = mesh.worldToLocal(worldPoint.clone());
    const hit = geometry.boundsTree.closestPointToPoint(local);
    if (!hit) continue;
    const info = getTriangleHitPointInfo(hit.point, geometry, hit.faceIndex);
    const normal = info.face.normal
      .clone()
      .applyNormalMatrix(new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld));
    const point = mesh.localToWorld(hit.point.clone());
    const delta = worldPoint.clone().sub(point),
      distance = delta.length();
    const signed = delta.dot(normal) < 0 ? -distance : distance;
    const candidate = { point, normal, distance, signed };
    if (
      !result ||
      (signed < 0 && (result.signed >= 0 || signed < result.signed)) ||
      (signed >= 0 && result.signed >= 0 && distance < result.distance)
    )
      result = candidate;
  }
  return result;
}

export function constrainInstrument(tooth, tool, kind) {
  if (kind === "hand") return false;
  tooth.updateWorldMatrix(true, true);
  tool.updateWorldMatrix(true, true);
  const signature = () =>
    `${kind}:${visibleSurfaces(tooth)
      .map((m) => m.uuid)
      .join(
        ",",
      )}:${tooth.matrixWorld.elements.join(",")}:${tool.matrixWorld.elements.join(",")}`;
  if (tool.userData.boundaryPose === signature())
    return tool.userData.boundaryBlocked;
  let blocked = false;
  let solved = false;
  for (let iteration = 0; iteration < 48; iteration++) {
    tool.updateWorldMatrix(true, true);
    let deepest = 0,
      correction = null;
    for (const bound of instrumentBounds(kind)) {
      const center = tool.localToWorld(bound.point.clone());
      const hit = nearestSurface(tooth, center);
      if (!hit) continue;
      const overlap = bound.radius + 0.003 - hit.signed;
      if (overlap > deepest) {
        deepest = overlap;
        // Nearest-point projection keeps the entire conservative tool volume outside.
        correction =
          hit.signed > 1e-6 ? center.sub(hit.point).normalize() : hit.normal;
      }
    }
    if (deepest < 0.0001) {
      solved = true;
      break;
    }
    blocked = true;
    tool.position.addScaledVector(correction, Math.min(deepest, 0.45));
  }
  // A deterministic outward fallback handles conflicting contacts in tight concavities.
  if (!solved) {
    for (let escape = 0; escape < 50; escape++) {
      tool.position.z += 0.2;
      tool.updateWorldMatrix(true, true);
      if (instrumentClearance(tooth, tool, kind) >= 0) {
        solved = true;
        break;
      }
    }
  }
  tool.userData.clearance = instrumentClearance(tooth, tool, kind);
  tool.updateWorldMatrix(true, true);
  tool.userData.boundaryPose = signature();
  tool.userData.boundaryBlocked = blocked;
  return blocked;
}

export function instrumentClearance(tooth, tool, kind) {
  tool.updateWorldMatrix(true, true);
  return Math.min(
    ...instrumentBounds(kind).map((b) => {
      const hit = nearestSurface(tooth, tool.localToWorld(b.point.clone()));
      return hit ? hit.signed - b.radius : Infinity;
    }),
  );
}

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
    textureWidth: 512,
    textureHeight: 512,
    multisample: 0,
  });
  reflector.position.z = 0.002;
  mirror.add(reflector);
  tool.add(mirror);
  const explorer = new THREE.Mesh(
    new THREE.TubeGeometry(EXPLORER_CURVE, 32, 0.014, 8, false),
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
  const hit = nearestSurface(tooth, tip);
  if (!hit) return { kind: "away", tip };
  const gap = hit.signed;
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
