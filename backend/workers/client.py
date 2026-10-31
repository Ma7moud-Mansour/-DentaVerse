import asyncio
import logging

from backend.protocol import Message, read_frame, write_frame

log = logging.getLogger("dentaverse.worker")


class WorkerClient:
    def __init__(self, source: str, port: int = 8766):
        self.source = source
        self.port = port
        self.writer = None
        self.session_id = None
        self.gesture_active = False
        self.epoch = 0
        self.commands: asyncio.Queue = asyncio.Queue(maxsize=16)
        self.connected = asyncio.Event()

    async def emit(self, kind: str, payload: dict, session_id: str | None = None):
        if self.writer is None or not self.connected.is_set():
            return False  # Never buffer sensor events across reconnects.
        await write_frame(self.writer, Message(source=self.source, type=kind, session_id=session_id or self.session_id, payload=payload))
        return True

    async def _heartbeat(self):
        while True:
            await asyncio.sleep(5)
            if self.writer:
                await write_frame(self.writer, {"type": "heartbeat"})

    async def run(self):
        while True:
            heartbeat = None
            try:
                reader, self.writer = await asyncio.open_connection("127.0.0.1", self.port)
                await write_frame(self.writer, {"type": "hello", "version": 1, "source": self.source})
                welcome = await read_frame(reader)
                if welcome.get("type") != "welcome":
                    raise ValueError("Coordinator did not accept worker")
                self.session_id = welcome["session_id"]
                self.connected.set()
                log.info("%s connected", self.source)
                heartbeat = asyncio.create_task(self._heartbeat())
                while True:
                    msg = await read_frame(reader)
                    if msg.get("type") == "context":
                        self.session_id = msg["session_id"]
                        self.gesture_active = msg["gesture_active"]
                        self.epoch = msg["epoch"]
                    elif msg.get("type") == "command":
                        try:
                            self.commands.put_nowait(msg)
                        except asyncio.QueueFull:
                            log.warning("Worker command queue full; retry the action")
                    elif msg.get("type") == "ack" and msg.get("status") == "rejected":
                        log.warning("Event rejected: %s", msg.get("error"))
            except (OSError, ValueError, asyncio.IncompleteReadError, asyncio.TimeoutError):
                log.info("Waiting for coordinator at 127.0.0.1:%d", self.port)
            finally:
                self.connected.clear()
                self.session_id = None
                self.gesture_active = False
                while not self.commands.empty():
                    self.commands.get_nowait()
                if heartbeat:
                    heartbeat.cancel()
                    await asyncio.gather(heartbeat, return_exceptions=True)
                if self.writer:
                    self.writer.close()
                    try:
                        await self.writer.wait_closed()
                    except OSError:
                        pass
                self.writer = None
            await asyncio.sleep(2)
