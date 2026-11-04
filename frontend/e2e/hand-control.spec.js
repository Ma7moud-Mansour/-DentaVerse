import { test, expect } from "./fixtures.js";
import { Worker } from "node:worker_threads";
import { readFileSync } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const signals = JSON.parse(
  readFileSync(
    new URL(
      "../../tests/fixtures/hand-signals-synthetic.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
function hand(side = "right", pose = "open", x = 0.7, y = 0.5, roll = 0) {
  const value = structuredClone(signals[pose].find((h) => h.id === side));
  const dx = x - value.center.x,
    dy = y - value.center.y;
  value.landmarks.forEach((p) => {
    p.x += dx;
    p.y += dy;
  });
  value.center = { x, y };
  value.roll = roll;
  return value;
}

function syntheticVision() {
  const worker = new Worker(new URL("./synthetic-vision.js", import.meta.url));
  let session;
  worker.on("message", (value) => {
    session = value.session;
  });
  const send = (command, value) => worker.postMessage({ command, value });
  return {
    get session() {
      return session;
    },
    set(value) {
      send("set", value);
    },
    pause() {
      send("pause");
    },
    start() {
      send("start");
    },
    match(value) {
      send("match", value);
    },
    close() {
      return worker.terminate();
    },
  };
}

test("synthetic hands rotate the tooth, move the mirror and zoom through real sockets", async ({
  page,
  request,
}) => {
  // Full multi-step transport/recovery journey with a software-rendered GLB and mirror.
  test.setTimeout(120000);
  // Protocol fixtures only; the workstation camera and database are never used.
  await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) =>
    route.abort(),
  );
  const sensor = syntheticVision();
  const state = async () =>
    (await request.get("http://127.0.0.1:8001/api/state")).json();
  const phase = () => state().then((s) => s.hand_control.phase);
  try {
    await expect.poll(() => sensor.session).toBeTruthy();
    await page.goto("/", { waitUntil: "domcontentloaded" });
    if (
      (await state()).session.paused ||
      (await page
        .getByRole("button", { name: "Use manual controls", exact: true })
        .isVisible())
    )
      await page
        .getByRole("button", { name: "Use manual controls", exact: true })
        .click();
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
    await page.getByLabel("Active tool").selectOption("hand");
    await page
      .locator(".specimen-stage")
      .getByRole("button", { name: "Reset view", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Reset specimen", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Enable hand controls", exact: true })
      .click();
    await expect.poll(phase).toBe("ready");
    await expect(
      page.getByRole("slider", { name: "Turn specimen" }),
    ).toBeDisabled();
    const mouseBefore = await state();
    const box = await page.locator(".specimen-stage canvas").boundingBox();
    await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.45);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.6, {
      steps: 4,
    });
    await page.mouse.up();
    await page.mouse.wheel(0, -200);
    await expect
      .poll(async () => (await state()).vision.pose.timestamp)
      .toBeGreaterThan(mouseBefore.vision.pose.timestamp);
    expect((await state()).session.rotation).toEqual(
      mouseBefore.session.rotation,
    );
    expect((await state()).session.zoom).toEqual(mouseBefore.session.zoom);
    sensor.set([hand("right", "fist")]);
    await expect.poll(phase).toBe("rotating");
    sensor.set([hand("right", "fist", 0.82, 0.56, 25)]);
    await expect
      .poll(async () => (await state()).session.rotation.yaw)
      .toBeGreaterThan(25);
    await expect
      .poll(() =>
        page
          .getByRole("slider", { name: "Turn specimen" })
          .evaluate((el) => Number(el.value)),
      )
      .toBeGreaterThan(25);
    sensor.set([hand()]);
    await expect.poll(phase).toBe("ready");
    await page.getByLabel("Active tool").selectOption("mirror");
    await expect.poll(phase).toBe("ready");
    sensor.set([hand("right", "pinch")]);
    await expect.poll(phase).toBe("moving_tool");
    sensor.set([hand("right", "pinch", 0.8, 0.6)]);
    await expect
      .poll(async () => (await state()).session.tool_position.x)
      .toBeGreaterThan(0.9);
    await expect
      .poll(async () => (await state()).session.tool_position.y)
      .toBeLessThan(-0.2);
    sensor.set([hand("left", "open", 0.3), hand()]);
    await expect.poll(phase).toBe("ready");
    const beforeDual = (await state()).session;
    sensor.set([hand("left", "fist", 0.3), hand("right", "pinch")]);
    await expect.poll(phase).toBe("bimanual");
    const left = hand("left", "fist", 0.4, 0.57, 25),
      right = hand("right", "pinch", 0.6, 0.6, -20);
    left.palm_span = 0.14;
    right.palm_span = 0.1;
    // Establish relative depth at the held pose, then move each hand independently.
    sensor.set([left, right]);
    await expect
      .poll(async () => (await state()).session.rotation.yaw)
      .toBeGreaterThan(beforeDual.rotation.yaw + 15);
    await expect
      .poll(async () => (await state()).session.tool_rotation.roll)
      .toBeLessThan(-10);
    await expect
      .poll(async () => (await state()).session.tool_position.x)
      .toBeLessThan(beforeDual.tool_position.x - 0.15);
    const zoomed = (await state()).session;
    // Losing the instrument hand freezes only that target; left-hand motion continues.
    sensor.set([hand("left", "fist", 0.45, 0.57, 25)]);
    await expect.poll(phase).toBe("rotating");
    expect((await state()).session.tool_position).toEqual(zoomed.tool_position);
    sensor.set([hand("left", "open", 0.3), hand("right")]);
    await expect.poll(phase).toBe("ready");
    const pinchBefore = (await state()).session;
    sensor.set([hand("left", "pinch", 0.3), hand("right", "pinch")]);
    await expect.poll(phase).toBe("zooming");
    sensor.set([hand("left", "pinch", 0.2), hand("right", "pinch", 0.8)]);
    await expect
      .poll(async () => (await state()).session.zoom)
      .toBeGreaterThan(pinchBefore.zoom + 0.4);
    expect((await state()).session.rotation).toEqual(pinchBefore.rotation);
    expect((await state()).session.tool_position).toEqual(
      pinchBefore.tool_position,
    );
    sensor.set([hand("left", "pinch", 0.4), hand("right", "pinch", 0.6)]);
    await expect
      .poll(async () => (await state()).session.zoom)
      .toBeLessThan(0.7);
    const retainedRotation = (await state()).session.rotation;
    sensor.set([hand()]);
    await expect.poll(phase).toBe("ready");
    sensor.set([hand("left", "open", 0.3), hand()]);
    await expect.poll(phase).toBe("ready");
    // Run the actual Python DollarPy recognizer on an explicitly synthetic wave,
    // then carry its result over the same real TCP/WebSocket path as the worker.
    const script = `import json,copy
from pathlib import Path
from backend.wave import RightWave
h=next(h for h in json.loads(Path('tests/fixtures/hand-signals-synthetic.json').read_text())['open'] if h['id']=='right')
w=RightWave()
for i in range(5):w.update([h],i*.1,('synthetic',1))
for i,x in enumerate([.5,.4,.3,.4,.5,.6,.7,.6,.5,.4,.3,.4,.5]):
 h['landmarks'][0]['x']=x
 result=w.update([h],(i+5)*.1,('synthetic',1))
 if result:
  print(json.dumps(result));break
`;
    const { stdout } = await promisify(execFile)(
      ".venv/Scripts/python.exe",
      ["-c", script],
      { cwd: "..", windowsHide: true },
    );
    const wave = JSON.parse(stdout.trim());
    expect(wave.method).toBe("DollarPy");
    sensor.match(wave);
    await expect(page.getByLabel("Active tool")).toHaveValue("explorer");
    await page
      .getByRole("button", { name: "Toggle Explorer", exact: true })
      .click();
    await expect(page.getByLabel("Active tool")).toHaveValue("hand");
    await page
      .getByRole("button", { name: "Next instrument", exact: true })
      .click();
    await expect(page.getByLabel("Active tool")).toHaveValue("mirror");
    sensor.pause();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Resume session", exact: true }),
    ).toBeDisabled();
    sensor.set([hand("right", "fist", 0.3)]);
    sensor.start();
    await expect(
      page.getByRole("button", { name: "Resume session", exact: true }),
    ).toBeEnabled();
    await page
      .getByRole("button", { name: "Resume session", exact: true })
      .click();
    await expect.poll(phase).toBe("release");
    expect((await state()).session.rotation).toEqual(retainedRotation);
    await page
      .getByRole("button", { name: "Use mouse & keyboard", exact: true })
      .click();
    const retained = (await state()).session;
    sensor.set([hand("right", "fist", 0.8)]);
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.locator(".specimen-stage .specimen")).toHaveAttribute(
      "data-model-state",
      "ready",
      { timeout: 15000 },
    );
    expect((await state()).session.rotation).toEqual(retained.rotation);
    expect((await state()).session.zoom).toEqual(retained.zoom);
    expect((await state()).session.tool_position).toEqual(
      retained.tool_position,
    );
    await page.screenshot({
      path: "../.review/ui/synthetic-hand-controls.png",
      fullPage: true,
    });
    await page.getByRole("button", { name: "Studio", exact: true }).click();
  } finally {
    try {
      if (
        await page
          .getByRole("button", { name: "Use manual controls", exact: true })
          .isVisible()
      )
        await page
          .getByRole("button", { name: "Use manual controls", exact: true })
          .click();
      if (
        await page
          .getByRole("button", { name: "Use mouse & keyboard", exact: true })
          .isVisible()
      )
        await page
          .getByRole("button", { name: "Use mouse & keyboard", exact: true })
          .click();
      await page
        .getByRole("button", { name: "Studio", exact: true })
        .click({ timeout: 2000 });
    } catch {
      /* Retain the original failure trace. */
    }
    await sensor.close();
  }
});
