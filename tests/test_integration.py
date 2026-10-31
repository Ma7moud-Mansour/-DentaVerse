"""Real local processes and sockets, using explicitly synthetic sensor events."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
import websockets

from backend.protocol import Message, read_frame, write_frame


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def running_server(tmp_path):
    http, tcp = free_port(), free_port()
    env = {**os.environ, "DENTAVERSE_DB": str(tmp_path / "integration.db"), "DENTAVERSE_TCP_PORT": str(tcp)}
    with (tmp_path / "server.log").open("w") as logs:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", str(http)],
            cwd=Path(__file__).resolve().parents[1], env=env, stdout=logs, stderr=logs)
        try:
            for _ in range(200):
                if process.poll() is not None:
                    pytest.fail((tmp_path / "server.log").read_text())
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{http}/api/health", timeout=0.3):
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                pytest.fail("Coordinator did not become ready")
            yield http, tcp
        finally:
            process.terminate()
            process.wait(timeout=10)


async def receive_until(ws, predicate):
    for _ in range(40):
        msg = json.loads(await asyncio.wait_for(ws.recv(), 5))
        if predicate(msg):
            return msg
    raise AssertionError("Expected message not received")


async def test_tcp_worker_event_changes_websocket_context(running_server):
    http, tcp = running_server
    async with websockets.connect(f"ws://127.0.0.1:{http}/ws", origin="http://127.0.0.1:5173") as browser:
        initial = await receive_until(browser, lambda m: m["type"] == "state")
        assert initial["state"]["identity_source"] == "manual_guest"
        reader, writer = await asyncio.open_connection("127.0.0.1", tcp)
        await write_frame(writer, {"type": "hello", "source": "bluetooth", "version": 1})
        assert (await read_frame(reader))["type"] == "welcome"
        await read_frame(reader)  # Worker context snapshot.
        event = Message(source="bluetooth", type="USER_IDENTIFIED", payload={"user_id": "DV-STUDENT-02"})
        await write_frame(writer, event)
        changed = await receive_until(browser, lambda m: m["type"] == "state" and m["state"]["profile"]["id"] == "DV-STUDENT-02")
        assert changed["state"]["identity_source"] == "bluetooth"
        assert changed["state"]["content"]["prompts"] != initial["state"]["content"]["prompts"]
        await read_frame(reader)  # Context after event.
        assert (await read_frame(reader))["status"] == "applied"
        await write_frame(writer, event)
        await read_frame(reader)
        assert (await read_frame(reader))["status"] == "duplicate"
        writer.close()
        await writer.wait_closed()


async def test_browser_cannot_impersonate_sensor(running_server):
    http, _ = running_server
    async with websockets.connect(f"ws://127.0.0.1:{http}/ws", origin="http://127.0.0.1:5173") as browser:
        initial = await receive_until(browser, lambda m: m["type"] == "state")
        await browser.send(Message(source="bluetooth", type="USER_IDENTIFIED", session_id=initial["state"]["session"]["id"], payload={"user_id": "DV-STUDENT-02"}).model_dump_json())
        error = await receive_until(browser, lambda m: m["type"] == "error")
        assert "UI source" in error["error"]
