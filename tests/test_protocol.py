import asyncio
import json
import struct

import pytest

from backend.protocol import MAX_FRAME, Message, encode_frame, read_frame


async def test_fragmented_and_coalesced_frames():
    reader = asyncio.StreamReader()
    a = encode_frame(Message(source="vision", type="TRACKING_STATUS", payload={"status": "lost"}))
    b = encode_frame(Message(source="vision", type="TRACKING_STATUS", payload={"status": "ready"}))
    async def feed():
        for chunk in (a[:2], a[2:6], a[6:] + b):
            reader.feed_data(chunk)
            await asyncio.sleep(0)
    task = asyncio.create_task(feed())
    assert (await read_frame(reader))["payload"]["status"] == "lost"
    assert (await read_frame(reader))["payload"]["status"] == "ready"
    await task


@pytest.mark.parametrize("body", [struct.pack("!I", MAX_FRAME + 1), struct.pack("!I", 0), struct.pack("!I", 3) + b"bad"])
async def test_invalid_frame_rejected(body):
    reader = asyncio.StreamReader()
    reader.feed_data(body)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        await read_frame(reader)
