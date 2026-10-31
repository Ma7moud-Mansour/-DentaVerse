"""Local-only FastAPI coordinator, browser WebSocket and framed worker TCP."""
import asyncio
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

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("dentaverse")
CONTROLS = {"ble_scan": "bluetooth", "ble_connect": "bluetooth", "ble_disconnect": "bluetooth",
    "vision_calibrate": "vision", "capture_start": "vision", "capture_stop": "vision", "capture_cancel": "vision", "template_record": "vision"}


class Hub:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.browsers: set[WebSocket] = set()
        self.workers: dict[str, asyncio.StreamWriter] = {}
        self.broadcast_lock = asyncio.Lock()

    async def broadcast(self):
        async with self.broadcast_lock:
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
            context = {"type": "context", "session_id": s["id"], "gesture_active": s["mode"] == "gesture" and not s["paused"], "epoch": s["gesture_epoch"]}
            for source, writer in list(self.workers.items()):
                try:
                    await write_frame(writer, context)
                except (OSError, asyncio.TimeoutError):
                    writer.close()

    async def dispatch(self, message: Message) -> dict:
        ack = self.engine.apply(message)
        target = CONTROLS.get(message.type)
        if target and ack["status"] == "applied":
            writer = self.workers.get(target)
            if writer is None:
                raise ValueError(f"{target} worker is disconnected")
            await write_frame(writer, {"type": "command", "command": message.type, "payload": message.payload, "session_id": message.session_id, "epoch": self.engine.state["session"]["gesture_epoch"]})
            ack["status"] = "dispatched"
        await self.broadcast()
        return ack

    async def handle_worker(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        source = None
        try:
            hello = await read_frame(reader, timeout=5)
            if hello.get("type") != "hello" or hello.get("source") not in {"vision", "bluetooth"} or hello.get("version") != 1:
                raise ValueError("Expected a version 1 worker hello")
            source = hello["source"]
            if source in self.workers:
                raise ValueError("This worker is already connected")
            self.workers[source] = writer
            self.engine.worker_status(source, True)
            await write_frame(writer, {"type": "welcome", "session_id": self.engine.state["session"]["id"]})
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
        try:
            yield
        finally:
            for writer in list(app.state.hub.workers.values()):
                writer.close()
            server.close()
            await server.wait_closed()
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
