import { test, expect } from "@playwright/test";
import net from "node:net";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";

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
  const socket = net.createConnection({ host: "127.0.0.1", port: 8767 });
  let buffer = Buffer.alloc(0),
    session,
    epoch = 0,
    timer;
  let hands = [hand()];
  const image = {
    data: readFileSync(
      new URL("../../tests/fixtures/preview-synthetic.jpg", import.meta.url),
    ).toString("base64"),
    width: 320,
    height: 180,
  };
  const write = (data) => {
    const body = Buffer.from(JSON.stringify(data)),
      header = Buffer.alloc(4);
    header.writeUInt32BE(body.length);
    socket.write(Buffer.concat([header, body]));
  };
  const tick = () => {
    if (session && !socket.destroyed)
      write({
        version: 1,
        source: "vision",
        type: "POSE_FRAME",
        event_id: randomUUID(),
        session_id: session,
        timestamp: Date.now() / 1000,
        payload: {
          landmarks: [],
          image,
          hands,
          hand_tracking: true,
          control_epoch: epoch,
        },
      });
  };
  const start = () => {
    clearInterval(timer);
    tick();
    timer = setInterval(tick, 100);
  };
  socket.on("data", (data) => {
    buffer = Buffer.concat([buffer, data]);
    while (buffer.length >= 4 && buffer.length >= buffer.readUInt32BE(0) + 4) {
      const length = buffer.readUInt32BE(0),
        packet = JSON.parse(buffer.subarray(4, length + 4).toString());
      buffer = buffer.subarray(length + 4);
      if (packet.type === "welcome") {
        session = packet.session_id;
        start();
      }
      if (packet.type === "context") {
        session = packet.session_id;
        epoch = packet.epoch;
      }
      if (packet.type === "command" && packet.command === "shutdown") {
        clearInterval(timer);
        socket.end();
      }
    }
  });
  write({ type: "hello", version: 1, source: "vision" });
  return {
    get session() {
      return session;
    },
    set(h) {
      hands = h;
      tick();
    },
    pause() {
      clearInterval(timer);
    },
    start,
    close() {
      clearInterval(timer);
      socket.destroy();
    },
  };
}

test("synthetic hands rotate the tooth, move the mirror and zoom through real sockets", async ({
  page,
  request,
}) => {
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
      .toBeGreaterThan(beforeDual.rotation.yaw + 30);
    await expect
      .poll(async () => (await state()).session.tool_rotation.roll)
      .toBeLessThan(-10);
    await expect
      .poll(async () => (await state()).session.tool_position.x)
      .toBeLessThan(beforeDual.tool_position.x - 0.3);
    const zoomed = (await state()).session;
    // Losing the instrument hand freezes only that target; left-hand motion continues.
    sensor.set([hand("left", "fist", 0.45, 0.57, 25)]);
    await expect.poll(phase).toBe("rotating");
    expect((await state()).session.tool_position).toEqual(zoomed.tool_position);
    const retainedRotation = (await state()).session.rotation;
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
    sensor.close();
  }
});
