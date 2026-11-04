"""Local-only FastAPI coordinator, browser WebSocket and framed worker TCP."""
import asyncio
import copy
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from backend.engine import Engine
from backend.protocol import MAX_FRAME, Message, read_frame, write_frame
from backend.storage import Store
from backend.supervisor import WorkerSupervisor

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("dentaverse")
CONTROLS = {"ble_scan": "bluetooth", "ble_connect": "bluetooth", "ble_disconnect": "bluetooth",
    "vision_calibrate": "vision", "vision_hand": "vision", "capture_start": "vision", "capture_stop": "vision", "capture_cancel": "vision", "template_record": "vision"}
SERVICE_ACTIONS = {"vision_start": ("vision", True), "vision_stop": ("vision", False), "ble_start": ("bluetooth", True), "ble_stop": ("bluetooth", False)}


class Hub:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.browsers: set[WebSocket] = set()
        self.workers: dict[str, asyncio.StreamWriter] = {}
        self.broadcast_lock = asyncio.Lock()
        self.closing = False
        self.jobs = set()
        self.worker_tasks = set()
        self.pending_pose = None
        self.pose_task = None
        self.service_locks = {source: asyncio.Lock() for source in ("vision", "bluetooth")}
        self.supervisor = WorkerSupervisor(ROOT, 8766, self.service_exit)

    async def service_exit(self, source, code, expected):
        service = self.engine.state["services"][source]
        service["managed"] = False
        if not self.engine.state["workers"][source]:
            service["status"] = "stopped" if expected or code == 0 else "error"
        if code != 0 and not expected:
            service["error"] = "Camera service could not start. Check camera access and setup, then retry." if source == "vision" else "Bluetooth service could not start. Check Bluetooth setup, then retry."
        await self.broadcast()

    async def service_action(self, source, start, payload):
        async with self.service_locks[source]:
            await self._service_action(source, start, payload)

    async def _service_action(self, source, start, payload):
        try:
            if start:
                await self.supervisor.start(source, payload.get("camera", 0))
                self.engine.state["services"][source]["managed"] = True
            else:
                writer = self.workers.get(source)
                if writer:
                    s = self.engine.state["session"]
                    await write_frame(writer, {"type": "command", "command": "shutdown", "payload": {}, "session_id": s["id"], "epoch": s["gesture_epoch"]})
                if self.supervisor.owns(source):
                    await self.supervisor.stop(source)
                elif writer:
                    for _ in range(60):
                        if source not in self.workers:
                            break
                        await asyncio.sleep(0.1)
                    else:
                        raise ValueError("The external service did not stop. Close its preview or terminal, then retry.")
                self.engine.state["services"][source].update(status="stopped", managed=False)
        except (OSError, ValueError, asyncio.TimeoutError) as exc:
            self.engine.state["services"][source].update(status="error", error=str(exc)[:300])
        await self.broadcast()

    async def broadcast(self):
        if self.closing:
            return
        async with self.broadcast_lock:
            if self.closing:
                return
            state = self.engine.snapshot()
            for ws in list(self.browsers):
                try:
                    await asyncio.wait_for(ws.send_json({"type": "state", "state": state}), 2)
                except Exception:
                    self.browsers.discard(ws)
                    try:
                        await ws.close()
                    except Exception:
                        pass
            s = state["session"]
            context = {"type": "context", "session_id": s["id"], "gesture_active": s["mode"] == "gesture" and not s["paused"], "epoch": s["gesture_epoch"], "hand": state["vision"]["dominant_hand"], "auto_wave": s["mode"] == "hand" and s["wave_enabled"] and not s["paused"] and s["screen"] == "workbench" and s["isolated"]}
            for source, writer in list(self.workers.items()):
                try:
                    await write_frame(writer, context)
                except (OSError, asyncio.TimeoutError):
                    writer.close()

    async def dispatch(self, message: Message) -> dict:
        ack = self.engine.apply(message)
        if message.source == "vision" and message.type == "POSE_FRAME":
            session = self.engine.state["session"]
            if session["id"] != message.session_id or self.closing:
                return ack
            data = {"type": "pose", "session_id": session["id"], "pose": self.engine.state["vision"]["pose"], "hand_control": self.engine.state["hand_control"]}
            if session["mode"] == "hand":
                data["session"] = copy.deepcopy(session)
            # Camera ingestion/ACK must never wait for a slow browser. Keep one
            # latest preview, not a queue of stale RGB frames and transformations.
            self.pending_pose = (session["gesture_epoch"], data)
            if self.pose_task is None or self.pose_task.done():
                self.pose_task = asyncio.create_task(self.flush_poses())
                self.jobs.add(self.pose_task)
                self.pose_task.add_done_callback(self.jobs.discard)
            return ack
        if message.type in SERVICE_ACTIONS and ack["status"] == "applied":
            source, start = SERVICE_ACTIONS[message.type]
            task = asyncio.create_task(self.service_action(source, start, message.payload))
            self.jobs.add(task)
            task.add_done_callback(self.jobs.discard)
            ack["status"] = "dispatched"
        target = CONTROLS.get(message.type)
        if target and ack["status"] == "applied":
            writer = self.workers.get(target)
            if writer is None and message.type != "vision_hand":
                raise ValueError(f"{target} worker is disconnected")
            if writer:
                await write_frame(writer, {"type": "command", "command": message.type, "payload": message.payload, "session_id": message.session_id, "epoch": self.engine.state["session"]["gesture_epoch"]})
                ack["status"] = "dispatched"
        await self.broadcast()
        return ack

    async def flush_poses(self):
        try:
            while self.pending_pose is not None and not self.closing:
                async with self.broadcast_lock:
                    epoch, data = self.pending_pose
                    self.pending_pose = None
                    session = self.engine.state["session"]
                    if data["session_id"] != session["id"] or epoch != session["gesture_epoch"]:
                        continue
                    for ws in list(self.browsers):
                        try:
                            await asyncio.wait_for(ws.send_json(data), 2)
                        except Exception:
                            self.browsers.discard(ws)
        finally:
            self.pending_pose = None

    async def monitor_hand_control(self):
        while not self.closing:
            await asyncio.sleep(0.2)
            if self.engine.expire_hand_tracking():
                await self.broadcast()

    async def handle_worker(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        source = None
        task = asyncio.current_task()
        self.worker_tasks.add(task)
        try:
            hello = await read_frame(reader, timeout=5)
            if hello.get("type") != "hello" or hello.get("source") not in {"vision", "bluetooth"} or hello.get("version") != 1:
                raise ValueError("Expected a version 1 worker hello")
            source = hello["source"]
            if source in self.workers:
                raise ValueError("This worker is already connected")
            self.workers[source] = writer
            self.engine.worker_status(source, True)
            self.engine.state["services"][source]["managed"] = self.supervisor.owns(source)
            await write_frame(writer, {"type": "welcome", "session_id": self.engine.state["session"]["id"], "hand": self.engine.state["vision"]["dominant_hand"]})
            await self.broadcast()
            while True:
                raw = await read_frame(reader)
                if raw.get("type") == "heartbeat":
                    await write_frame(writer, {"type": "heartbeat_ack"})
                    continue
                try:
                    message = Message.model_validate(raw)
                    if message.source != source:
                        raise ValueError("Worker cannot send another source's events")
                    ack = await self.dispatch(message)
                except (ValueError, TypeError, KeyError, ValidationError) as exc:
                    ack = {"type": "ack", "event_id": str(raw.get("event_id", ""))[:100], "status": "rejected", "error": str(exc)[:400]}
                    if source == "bluetooth" and raw.get("type") == "USER_IDENTIFIED":
                        self.engine.state["bluetooth"].update(status="error", error=str(exc)[:300])
                        await self.broadcast()
                    elif source == "vision" and raw.get("type") == "GESTURE_RECOGNIZED":
                        self.engine.state["last_gesture"] = {"name": "Rejected", "score": 0.0, "reason": str(exc)[:200]}
                        await self.broadcast()
                await write_frame(writer, ack)
        except (ValueError, OSError, asyncio.IncompleteReadError, asyncio.TimeoutError) as exc:
            log.info("Worker closed: %s", type(exc).__name__)
        finally:
            self.worker_tasks.discard(task)
            if source and self.workers.get(source) is writer:
                self.workers.pop(source, None)
                self.engine.worker_status(source, False)
                await self.broadcast()
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


def create_app(db_path: str | Path | None = None, tcp_port: int | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = Store(db_path or os.environ.get("DENTAVERSE_DB", ROOT / "data" / "dentaverse.db"))
        app.state.hub = Hub(Engine(store))
        server = await asyncio.start_server(app.state.hub.handle_worker, "127.0.0.1", tcp_port if tcp_port is not None else int(os.environ.get("DENTAVERSE_TCP_PORT", "8766")))
        app.state.tcp_port = server.sockets[0].getsockname()[1]
        app.state.hub.supervisor.port = app.state.tcp_port
        monitor = asyncio.create_task(app.state.hub.monitor_hand_control())
        app.state.hub.jobs.add(monitor)
        monitor.add_done_callback(app.state.hub.jobs.discard)
        try:
            yield
        finally:
            app.state.hub.closing = True
            for task in list(app.state.hub.jobs):
                task.cancel()
            await asyncio.gather(*list(app.state.hub.jobs), return_exceptions=True)
            await app.state.hub.supervisor.close()
            for writer in list(app.state.hub.workers.values()):
                writer.close()
            server.close()
            await server.wait_closed()
            tasks = list(app.state.hub.worker_tasks)
            if tasks:
                done, pending = await asyncio.wait(tasks, timeout=3)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            store.close()

    app = FastAPI(title="DentaVerse local coordinator", lifespan=lifespan)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0", "workers": app.state.hub.engine.state["workers"]}

    @app.get("/api/state")
    async def state():
        return JSONResponse(app.state.hub.engine.snapshot())

    @app.websocket("/ws")
    async def browser(ws: WebSocket):
        origins = {"http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5174", "http://127.0.0.1:8000", "http://localhost:8000"}
        if ws.headers.get("origin") not in origins:
            await ws.close(code=1008)
            return
        await ws.accept()
        hub = app.state.hub
        hub.browsers.add(ws)
        try:
            await ws.send_json({"type": "state", "state": hub.engine.snapshot()})
            while True:
                raw = await ws.receive_text()
                try:
                    if len(raw.encode("utf-8")) > MAX_FRAME:
                        raise ValueError("Message exceeds size limit")
                    message = Message.model_validate_json(raw)
                    if message.source != "ui":
                        raise ValueError("Browser messages must use UI source")
                    ack = await hub.dispatch(message)
                except (ValueError, TypeError, KeyError, ValidationError) as exc:
                    await ws.send_json({"type": "error", "error": str(exc)[:400]})
                    continue
                await ws.send_json(ack)
        except WebSocketDisconnect:
            pass
        finally:
            hub.browsers.discard(ws)

    if (ROOT / "frontend" / "dist").is_dir():
        app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True), name="frontend")
    return app


app = create_app()
