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
        self.pending: dict[str, asyncio.Future] = {}

    async def emit(self, kind: str, payload: dict, session_id: str | None = None, wait_ack: bool = False):
        if self.writer is None or not self.connected.is_set():
            if wait_ack:
                raise ConnectionError("Coordinator is disconnected")
            return False  # Never buffer sensor events across reconnects.
        message = Message(source=self.source, type=kind, session_id=session_id or self.session_id, payload=payload)
        if wait_ack:
            self.pending[message.event_id] = asyncio.get_running_loop().create_future()
        try:
            await write_frame(self.writer, message)
            if wait_ack:
                ack = await asyncio.wait_for(self.pending[message.event_id], 8)
                if ack.get("status") == "rejected":
                    raise ValueError(ack.get("error", "Event rejected"))
                return ack
            return True
        finally:
            self.pending.pop(message.event_id, None)

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
                    elif msg.get("type") == "ack":
                        future = self.pending.get(msg.get("event_id"))
                        if future and not future.done():
                            future.set_result(msg)
                        elif msg.get("status") == "rejected":
                            log.warning("Event rejected: %s", msg.get("error"))
            except (OSError, ValueError, asyncio.IncompleteReadError, asyncio.TimeoutError):
                log.info("Waiting for coordinator at 127.0.0.1:%d", self.port)
            finally:
                self.connected.clear()
                self.session_id = None
                self.gesture_active = False
                for future in list(self.pending.values()):
                    if not future.done():
                        future.set_exception(ConnectionError("Coordinator disconnected before acknowledgement"))
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
