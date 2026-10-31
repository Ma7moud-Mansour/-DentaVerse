import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Verify the local application without waiting for an optional font network.
  await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) =>
    route.abort(),
  );
});

test("manual learning flow saves a reflection and switches context without sharing notes", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /Knowledge,/ })).toBeVisible();
  await expect(page.locator(".hero-specimen .specimen")).toHaveAttribute(
    "data-model-state",
    "ready",
    { timeout: 15000 },
  );
  await page.screenshot({ path: "../.review/ui/studio.png", fullPage: true });
  await page.getByRole("button", { name: "Preferences", exact: true }).click();
  await page.getByLabel("Manual profile preview").selectOption("DV-STUDENT-01");
  const dialog = page.getByRole("dialog");
  if (await dialog.isVisible())
    await page.getByRole("button", { name: "Discard & switch" }).click();
  await expect(
    page.getByText("Beginning learner", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Anatomy atlas", exact: true })
    .click();
  await page.screenshot({ path: "../.review/ui/atlas.png", fullPage: true });
  await page
    .getByPlaceholder("Search by tooth name or FDI number")
    .fill("unknown tooth");
  await expect(
    page.getByRole("heading", { name: "No specimen matches that search." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear search" }).click();
  await page.getByRole("button", { name: "Inspect specimen" }).click();
  await expect(
    page.getByRole("heading", { name: "Upper right first molar", exact: true }),
  ).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible();
  await expect(page.locator(".specimen-stage .specimen")).toHaveAttribute(
    "data-model-state",
    "ready",
    { timeout: 15000 },
  );
  await page.screenshot({
    path: "../.review/ui/workbench.png",
    fullPage: true,
  });
  const rotation = page.getByRole("slider", { name: "Turn specimen" });
  await rotation.focus();
  for (let i = 0; i < 10; i++) await rotation.press("ArrowRight");
  await page.getByRole("button", { name: "Dentin", exact: true }).click();
  await expect(
    page.getByText("Dentin lies beneath enamel", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Active tool").selectOption("mirror");
  await page.getByRole("slider", { name: "Tool horizontal position" }).focus();
  await page
    .getByRole("slider", { name: "Tool horizontal position" })
    .press("ArrowLeft");
  await page.getByRole("button", { name: "Confirm mirror placement" }).click();
  await page.getByRole("button", { name: "Pause session" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Resume session" }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await page
    .locator(".specimen-stage")
    .getByRole("button", { name: "Reset view", exact: true })
    .click();
  await page.getByRole("button", { name: "Keep working" }).click();
  await page.getByRole("button", { name: "Finish & review" }).click();
  const note = `Molar reflection ${Date.now()}`;
  await page.getByLabel("Reflect before you move on").fill(note);
  await page.getByRole("button", { name: "Save reflection" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Reflection saved" }),
  ).toBeVisible();
  await page.screenshot({ path: "../.review/ui/review.png", fullPage: true });
  await page.getByRole("button", { name: "Open journal" }).click();
  await expect(page.getByText(note, { exact: true })).toBeVisible();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByText(note, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Preferences", exact: true }).click();
  await page.getByLabel("Manual profile preview").selectOption("DV-STUDENT-02");
  await expect(page.getByRole("heading", { name: /Knowledge,/ })).toBeVisible();
  await page.getByRole("button", { name: "Preferences", exact: true }).click();
  await expect(
    page.getByText("Explore structure and relationships", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Session journal", exact: true })
    .click();
  await expect(page.getByText(note, { exact: true })).toBeHidden();
  await page.getByRole("button", { name: "Preferences", exact: true }).click();
  await page.getByLabel("Manual profile preview").selectOption("DV-STUDENT-01");
  await expect(page.getByRole("heading", { name: /Knowledge,/ })).toBeVisible();
  await page
    .getByRole("button", { name: "Session journal", exact: true })
    .click();
  await expect(page.getByText(note, { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("mouse drag rotates, wheel zooms, and the instrument can be dragged", async ({
  page,
  request,
}) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page
    .getByRole("button", { name: "Anatomy atlas", exact: true })
    .click();
  await page.getByRole("button", { name: "Inspect specimen" }).click();
  const viewer = page.locator(".specimen-stage .specimen");
  await expect(viewer).toHaveAttribute("data-model-state", "ready", {
    timeout: 15000,
  });
  const asset = await request.get("/models/maxillary-first-molar-left.glb");
  expect(asset.ok()).toBe(true);
  const body = await asset.body();
  expect(body.subarray(0, 4).toString()).toBe("glTF");
  expect(body.length).toBeGreaterThan(1000000);
  const session = async () =>
    (await (await request.get("/api/state")).json()).session;
  const before = await session();
  const box = await page
    .getByLabel("3D tooth viewer", { exact: true })
    .boundingBox();
  await page.mouse.move(box.x + box.width * 0.46, box.y + box.height * 0.44);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width * 0.46 + 95,
    box.y + box.height * 0.44 + 25,
    { steps: 10 },
  );
  await page.mouse.up();
  await expect
    .poll(async () =>
      Math.abs((await session()).rotation.yaw - before.rotation.yaw),
    )
    .toBeGreaterThan(20);
  const turned = await session();
  await page.mouse.wheel(0, -160);
  await expect
    .poll(async () => (await session()).zoom)
    .toBeGreaterThan(turned.zoom);
  await page.getByLabel("Active tool").selectOption("mirror");
  const handle = page.getByRole("button", { name: "Drag selected instrument" });
  await expect(handle).toBeVisible();
  const toolBefore = (await session()).tool_position;
  const grip = await handle.boundingBox();
  await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    grip.x + grip.width / 2 - 70,
    grip.y + grip.height / 2 - 40,
    { steps: 10 },
  );
  await page.mouse.up();
  await expect
    .poll(async () =>
      Math.abs((await session()).tool_position.x - toolBefore.x),
    )
    .toBeGreaterThan(0.1);
  await expect
    .poll(async () =>
      Math.abs((await session()).tool_position.y - toolBefore.y),
    )
    .toBeGreaterThan(0.1);
  await page.screenshot({
    path: "../.review/ui/mouse-controls.png",
    fullPage: true,
  });
  const final = await session();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(viewer).toHaveAttribute("data-model-state", "ready", {
    timeout: 15000,
  });
  const retained = await session();
  expect(retained.rotation).toEqual(final.rotation);
  expect(retained.tool_position).toEqual(final.tool_position);
  expect(retained.zoom).toEqual(final.zoom);
  await page.getByRole("button", { name: "Pause session" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  const frozen = await session();
  await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.3);
  await page.mouse.wheel(0, -200);
  expect((await session()).zoom).toEqual(frozen.zoom);
  await page.getByRole("button", { name: "Use manual controls" }).click();
  await page
    .locator(".specimen-stage")
    .getByRole("button", { name: "Reset view", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Reset specimen", exact: true })
    .click();
  await expect
    .poll(async () => (await session()).rotation)
    .toEqual({ yaw: 0, pitch: 0 });
  await expect.poll(async () => (await session()).zoom).toBe(1);
  await page.getByLabel("3D tooth viewer", { exact: true }).focus();
  await page.getByLabel("3D tooth viewer", { exact: true }).press("ArrowRight");
  await expect.poll(async () => (await session()).rotation.yaw).toBe(5);
  const keyPosition = (await session()).tool_position.x;
  await page.getByRole("button", { name: "Drag selected instrument" }).focus();
  await page
    .getByRole("button", { name: "Drag selected instrument" })
    .press("ArrowLeft");
  await expect
    .poll(async () => (await session()).tool_position.x)
    .toBeCloseTo(keyPosition - 0.1);
  await page.screenshot({
    path: "../.review/ui/molar-fixed.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Studio", exact: true }).click();
});

test("essential navigation fits a narrow screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("button", { name: "Studio", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Studio", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Knowledge,/ })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    path: "../.review/ui/mobile-studio.png",
    fullPage: true,
  });
});
