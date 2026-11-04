"""A stalled display must not turn a healthy camera into a tracking outage."""
import asyncio
import time

import pytest

from backend.app import Hub
from backend.engine import Engine
from backend.protocol import Message
from backend.storage import Store


@pytest.fixture
def hub(tmp_path):
    store = Store(tmp_path / "backpressure.db")
    value = Hub(Engine(store))
    value.engine.worker_status("vision", True)
    value.engine.state["session"].update(
        mode="hand", screen="workbench", isolated=True, selected_tooth=16,
    )
    yield value
    store.close()


def frame(hub):
    session = hub.engine.state["session"]
    return Message(source="vision", type="POSE_FRAME", session_id=session["id"],
                   timestamp=time.time(), payload={"landmarks": [], "hands": [],
                   "hand_tracking": True, "control_epoch": session["gesture_epoch"]})


async def test_slow_browser_does_not_block_camera_and_only_latest_preview_survives(hub):
    started, release = asyncio.Event(), asyncio.Event()
    delivered = []

    class SlowBrowser:
        async def send_json(self, data):
            started.set()
            await release.wait()
            delivered.append(data)

    hub.browsers.add(SlowBrowser())
    first = frame(hub)
    try:
        assert (await hub.dispatch(first))["status"] == "preview"
        await asyncio.wait_for(started.wait(), 1)
        # Longer than the real 0.8s camera-loss threshold, with a deliberately
        # blocked browser. Sensor frames/ACKs must keep reaching the engine.
        for _ in range(30):
            latest = frame(hub)
            ack = await asyncio.wait_for(hub.dispatch(latest), 0.5)
            assert ack["status"] == "preview"
            assert not hub.engine.expire_hand_tracking()
            await asyncio.sleep(0.03)
        assert not hub.engine.state["session"]["paused"]
        assert hub.pending_pose[1]["pose"]["timestamp"] == latest.timestamp
        release.set()
        await asyncio.wait_for(hub.pose_task, 1)
        assert [d["pose"]["timestamp"] for d in delivered] == [first.timestamp, latest.timestamp]
        assert hub.pending_pose is None
    finally:
        release.set()
        if hub.pose_task:
            await asyncio.gather(hub.pose_task, return_exceptions=True)


async def test_queued_pose_from_previous_control_epoch_is_discarded(hub):
    delivered = []

    class Browser:
        async def send_json(self, data):
            delivered.append(data)

    hub.browsers.add(Browser())
    async with hub.broadcast_lock:
        await hub.dispatch(frame(hub))
        await asyncio.sleep(0)
        hub.engine._action("set_mode", {"mode": "manual"})
    await hub.pose_task
    assert delivered == []
    assert hub.pending_pose is None
