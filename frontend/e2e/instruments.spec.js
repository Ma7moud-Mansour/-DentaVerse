import { test, expect } from "./fixtures.js";

test.afterEach(async ({ page }) => {
  const manual = page.getByRole("button", {
    name: "Use manual controls",
    exact: true,
  });
  if (await manual.isVisible()) await manual.click();
  await page.getByRole("button", { name: "Studio", exact: true }).click();
});

test("the mirror renders scene pixels and the explorer detects actual mesh contact", async ({
  page,
}) => {
  await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) =>
    route.abort(),
  );
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const result = await page.evaluate(async () => {
    const THREE = await import("/node_modules/three/build/three.module.js");
    const {
      buildInstrument,
      positionInstrument,
      probeSurface,
      visibleSurfacePlacement,
      TIP,
      constrainInstrument,
      instrumentClearance,
    } = await import("/src/instruments.js");
    const renderer = new THREE.WebGLRenderer();
    renderer.setSize(160, 160);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    camera.position.set(0, 0, 7.6);
    camera.lookAt(0, 0, 0);
    const tooth = new THREE.Group();
    scene.add(tooth);
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.8, 32, 24),
      new THREE.MeshBasicMaterial({ color: 0xff0000 }),
    );
    tooth.add(sphere);
    const tool = buildInstrument();
    scene.add(tool);
    positionInstrument(tool, "mirror", { x: 0.7, y: 0, z: 0 }, {}, camera);
    renderer.render(scene, camera);
    const reflector = tool.userData.reflector,
      target = reflector.getRenderTarget();
    const pixels = new Uint16Array(target.width * target.height * 4);
    function redPixels() {
      renderer.readRenderTargetPixels(
        target,
        0,
        0,
        target.width,
        target.height,
        pixels,
      );
      let count = 0;
      for (let i = 0; i < pixels.length; i += 4)
        if (pixels[i] > pixels[i + 1] + 100 && pixels[i] > pixels[i + 2] + 100)
          count++;
      return count;
    }
    const reflected = redPixels();
    sphere.visible = false;
    renderer.render(scene, camera);
    const empty = redPixels();
    sphere.visible = true;
    positionInstrument(tool, "explorer", { x: 0, y: 0, z: 0 }, {}, camera);
    scene.updateMatrixWorld(true);
    const before = probeSurface(tooth, tool).kind;
    const placement = visibleSurfacePlacement(tooth, tool, camera);
    const tip = tool.localToWorld(TIP.clone());
    tool.position.add(placement.clone().sub(tip));
    scene.updateMatrixWorld(true);
    const touched = probeSurface(tooth, tool);
    tool.position.multiplyScalar(0.1);
    scene.updateMatrixWorld(true);
    const inside = probeSurface(tooth, tool).kind;
    const clearances = [];
    for (const kind of ["mirror", "explorer"]) {
      for (const z of [-0.6, 0, 0.6]) {
        for (const x of [-0.3, 0, 0.3]) {
          positionInstrument(
            tool,
            kind,
            { x, y: 0.2, z },
            { yaw: 25, pitch: -15, roll: 30 },
            camera,
          );
          tooth.rotation.set(0.2, 0.5, 0.3);
          scene.updateMatrixWorld(true);
          constrainInstrument(tooth, tool, kind);
          clearances.push(instrumentClearance(tooth, tool, kind));
        }
      }
    }
    reflector.dispose();
    scene.traverse((o) => {
      o.geometry?.dispose();
      o.material?.dispose();
    });
    renderer.dispose();
    return {
      reflected,
      empty,
      before,
      contact: touched.kind,
      point: touched.point.toArray(),
      inside,
      clearances,
    };
  });
  expect(result.reflected).toBeGreaterThan(100);
  expect(result.empty).toBe(0);
  expect(result.before).toBe("away");
  expect(result.contact).toBe("contact");
  expect(result.inside).toBe("inside");
  expect(Math.min(...result.clearances)).toBeGreaterThanOrEqual(-0.0001);
});

test("instrument depth, orientation and surface marks work in the student workspace", async ({
  page,
  request,
}) => {
  await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) =>
    route.abort(),
  );
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Studio", exact: true }).click();
  await page
    .getByRole("button", { name: "Anatomy atlas", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Inspect specimen", exact: true })
    .click();
  await expect(page.locator(".specimen-stage .specimen")).toHaveAttribute(
    "data-model-state",
    "ready",
    { timeout: 15000 },
  );
  await page
    .locator(".specimen-stage")
    .getByRole("button", { name: "Reset view", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Reset specimen", exact: true })
    .click();
  await page.getByLabel("Active tool").selectOption("mirror");
  await expect(
    page.getByText("Live mirror reflection", { exact: true }),
  ).toBeVisible();
  const setRange = async (name, value) => {
    const range = page.getByRole("slider", { name, exact: true });
    await range.fill(String(value));
    await range.dispatchEvent("input");
    await range.dispatchEvent("change");
  };
  await setRange("Tool depth", 0.2);
  await setRange("Tool tilt horizontal", 20);
  const state = async () =>
    (await request.get("http://127.0.0.1:8001/api/state")).json();
  await expect
    .poll(async () => (await state()).session.tool_position.z)
    .toBe(0.2);
  await expect
    .poll(async () => (await state()).session.tool_rotation.yaw)
    .toBe(20);
  await setRange("Tool tilt horizontal", 0);
  await page.screenshot({
    path: "../.review/ui/live-mirror.png",
    fullPage: true,
  });
  await setRange("Tool horizontal position", 0);
  await setRange("Tool depth", -0.4);
  const rendered = page.locator(".specimen-stage .specimen");
  await expect(rendered).toHaveAttribute("data-instrument-boundary", "true");
  await expect
    .poll(async () =>
      Number(await rendered.getAttribute("data-instrument-clearance")),
    )
    .toBeGreaterThanOrEqual(-0.0001);
  await setRange("Turn specimen", 60);
  await setRange("Tilt specimen", 25);
  await expect
    .poll(async () =>
      Number(await rendered.getAttribute("data-instrument-clearance")),
    )
    .toBeGreaterThanOrEqual(-0.0001);
  await page.screenshot({
    path: "../.review/ui/mirror-boundary.png",
    fullPage: true,
  });
  await setRange("Turn specimen", 0);
  await setRange("Tilt specimen", 0);
  await page.getByLabel("Active tool").selectOption("explorer");
  await setRange("Tool depth", 0.2);
  await setRange("Tool horizontal position", 0.1);
  await setRange("Tool vertical position", 0);
  await setRange("Tool tilt horizontal", 0);
  await page
    .getByRole("button", { name: "Touch visible surface", exact: true })
    .click();
  await expect(page.getByLabel("Instrument feedback")).toHaveAttribute(
    "data-probe",
    "contact",
  );
  await page
    .getByRole("button", { name: "Mark contact (0/8)", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Mark contact (1/8)", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "../.review/ui/explorer-contact.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Clear marks", exact: true }).click();
  await page
    .getByRole("button", { name: "Pause session", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Mark contact (0/8)", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Use manual controls", exact: true })
    .click();
  const retained = (await state()).session;
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect
    .poll(async () =>
      Number(
        await page
          .getByRole("slider", { name: "Tool depth", exact: true })
          .inputValue(),
      ),
    )
    .toBeCloseTo(retained.tool_position.z, 8);
  await page.getByRole("button", { name: "Studio", exact: true }).click();
});
