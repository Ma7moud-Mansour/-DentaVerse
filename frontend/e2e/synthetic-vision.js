// Explicit synthetic protocol source; no workstation camera is accessed.
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
const sent = new Map();
const write = (data) => {
  if (data.type === "POSE_FRAME") {
    sent.set(data.event_id, Date.now());
    if (sent.size > 128) sent.delete(sent.keys().next().value);
  }
  const body = Buffer.from(JSON.stringify(data)),
    header = Buffer.alloc(4);
  header.writeUInt32BE(body.length);
  socket.write(Buffer.concat([header, body]));
};
let lastTick = Date.now();
const tick = () => {
  const now = Date.now();
  if (now - lastTick > 650)
    process.stderr.write(`Synthetic source gap: ${now - lastTick}ms\n`);
  lastTick = now;
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
  lastTick = Date.now();
  tick();
  timer = setInterval(tick, 100);
};
socket.on("data", (data) => {
  buffer = Buffer.concat([buffer, data]);
  while (buffer.length >= 4 && buffer.length >= buffer.readUInt32BE(0) + 4) {
    const length = buffer.readUInt32BE(0),
      packet = JSON.parse(buffer.subarray(4, length + 4).toString());
    buffer = buffer.subarray(length + 4);
    if (sent.has(packet.event_id)) {
      const lag = Date.now() - sent.get(packet.event_id);
      sent.delete(packet.event_id);
      if (lag > 650)
        process.stderr.write(`Synthetic source ACK lag: ${lag}ms\n`);
    }
    if (packet.type === "welcome") {
      session = packet.session_id;
      process.send({ session });
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

process.on("message", ({ command, value }) => {
  if (command === "set") {
    hands = value;
    if (!timer) lastTick = Date.now();
    tick();
  }
  if (command === "pause") {
    clearInterval(timer);
    timer = null;
  }
  if (command === "start") start();
  if (command === "match")
    write({
      version: 1,
      source: "vision",
      type: "GESTURE_RECOGNIZED",
      event_id: randomUUID(),
      session_id: session,
      timestamp: Date.now() / 1000,
      payload: { ...value, epoch },
    });
});
