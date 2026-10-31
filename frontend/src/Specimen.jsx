import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

// An original procedural teaching schematic, not a validated anatomical mesh.
function buildSpecimen() {
  const group = new THREE.Group();
  const materials = {
    enamel: new THREE.MeshStandardMaterial({ color: 0xf2e6c7, roughness: 0.28, metalness: 0.02 }),
    dentin: new THREE.MeshStandardMaterial({ color: 0xd4aa65, roughness: 0.45 }),
    pulp: new THREE.MeshStandardMaterial({ color: 0xb16e66, roughness: 0.55 }),
    root: new THREE.MeshStandardMaterial({ color: 0xd6c6a1, roughness: 0.55 }),
  };
  function sphere(parent, position, scale, material) {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 28), material);
    mesh.position.set(...position); mesh.scale.set(...scale); parent.add(mesh); return mesh;
  }
  for (const [name, size] of [['enamel', 1], ['dentin', 0.85], ['pulp', 0.46]]) {
    const layer = new THREE.Group(); layer.name = name;
    sphere(layer, [0, 0.68, 0], [0.78 * size, 0.66 * size, 0.66 * size], materials[name]);
    for (const [x, z] of [[-0.35, -0.28], [0.35, -0.28], [-0.35, 0.28], [0.35, 0.28]])
      sphere(layer, [x * size, 1.12 * size, z * size], [0.36 * size, 0.3 * size, 0.33 * size], materials[name]);
    group.add(layer);
  }
  const roots = new THREE.Group(); roots.name = 'roots';
  for (const [x, z, tilt] of [[-0.35, -0.18, -0.18], [0.32, -0.25, 0.15], [0.12, 0.36, 0.08]]) {
    const root = new THREE.Mesh(new THREE.ConeGeometry(0.25, 1.7, 32), materials.root);
    root.rotation.z = Math.PI + tilt; root.rotation.x = z * 0.35;
    root.position.set(x, -0.53, z); roots.add(root);
    sphere(roots, [x, 0.18, z], [0.27, 0.33, 0.27], materials.root);
  }
  group.add(roots);
  return group;
}

export default function Specimen({ session, compact = false }) {
  const mount = useRef(null), sceneRef = useRef(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const host = mount.current;
    let renderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
    catch { setFailed(true); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.8;
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    camera.position.set(0, 0.25, 7.8); camera.lookAt(0, 0.1, 0);
    scene.add(new THREE.HemisphereLight(0xfff9e7, 0x456259, 3.5));
    const key = new THREE.DirectionalLight(0xfff4d5, 5); key.position.set(-3, 5, 5); scene.add(key);
    const rim = new THREE.DirectionalLight(0xdceebb, 3); rim.position.set(4, 1, -2); scene.add(rim);
    const tooth = buildSpecimen(); scene.add(tooth);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(1.7, 0.008, 8, 96), new THREE.MeshBasicMaterial({ color: 0x4b6356 }));
    ring.rotation.x = -Math.PI / 2; ring.position.y = -1.65; scene.add(ring);
    const tool = new THREE.Group();
    const metal = new THREE.MeshStandardMaterial({ color: 0xc8dad4, metalness: 0.75, roughness: 0.2 });
    const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.045, 1.1, 20), metal);
    handle.position.y = -0.45; tool.add(handle);
    const mirror = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.05, 40), metal);
    mirror.rotation.x = Math.PI / 2; mirror.position.y = 0.2; tool.add(mirror);
    tool.rotation.z = 0.35; scene.add(tool);
    sceneRef.current = { tooth, tool, camera, scene, renderer };
    function resize() {
      if (!host.clientWidth || !host.clientHeight) return;
      renderer.setSize(host.clientWidth, host.clientHeight);
      camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    }
    const observer = new ResizeObserver(resize); observer.observe(host); resize();
    return () => {
      observer.disconnect();
      scene.traverse(obj => { obj.geometry?.dispose(); if (obj.material) obj.material.dispose(); });
      renderer.dispose(); renderer.domElement.remove(); sceneRef.current = null;
    };
  }, []);
  useEffect(() => {
    const view = sceneRef.current; if (!view) return;
    const { tooth, tool, camera, scene, renderer } = view;
    tooth.rotation.set(THREE.MathUtils.degToRad(session?.rotation?.pitch ?? 0), THREE.MathUtils.degToRad(session?.rotation?.yaw ?? -20), 0);
    const layer = session?.layer ?? 'surface';
    tooth.getObjectByName('enamel').visible = layer === 'surface' || layer === 'enamel';
    tooth.getObjectByName('dentin').visible = layer === 'dentin';
    tooth.getObjectByName('pulp').visible = layer === 'pulp';
    tooth.getObjectByName('roots').visible = layer !== 'pulp';
    tool.visible = session?.tool !== undefined && session.tool !== 'hand';
    mirrorShape(tool, session?.tool);
    tool.position.set((session?.tool_position?.x ?? 0.7) * 1.8, (session?.tool_position?.y ?? 0) * 1.8, 0.9);
    camera.position.z = 7.8 / (session?.zoom ?? 1);
    renderer.render(scene, camera);
  }, [session, failed]);
  return <div className={`specimen ${compact ? 'compact' : ''}`} role="img" aria-label="Interactive schematic of tooth 16; not a validated anatomy model">
    <div ref={mount} className="three-mount" />
    {failed && <div className="canvas-fallback">3D preview unavailable. Enable WebGL in your browser; the learning controls remain available.</div>}
    {!compact && <><span className="specimen-label">FDI 16 / UPPER RIGHT</span><span className="schematic-label">SCHEMATIC MODEL · ANATOMY REVIEW PENDING</span><span className="anatomy-label crown-label">Crown</span><span className="anatomy-label root-label">Roots</span></>}
  </div>;
}

function mirrorShape(tool, name) {
  tool.children[1].scale.setScalar(name === 'explorer' ? 0.3 : 1);
}
