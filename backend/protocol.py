"""Bounded, versioned, length-prefixed JSON over local TCP."""
import asyncio
import json
import math
import struct
import time
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

MAX_FRAME = 65536
MAX_AGE = 15.0


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal[1] = 1
    event_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=100)
    source: Literal["ui", "vision", "bluetooth", "coordinator"]
    type: str = Field(min_length=1, max_length=60)
    session_id: str | None = Field(default=None, max_length=100)
    timestamp: float = Field(default_factory=time.time, allow_inf_nan=False)
    payload: dict[str, Any] = Field(default_factory=dict)


def encode_frame(message: Message | dict) -> bytes:
    data = message.model_dump() if isinstance(message, Message) else message
    body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if not body or len(body) > MAX_FRAME:
        raise ValueError("Frame exceeds the 64 KiB limit")
    return struct.pack("!I", len(body)) + body


async def read_frame(reader: asyncio.StreamReader, timeout: float = 20) -> dict:
    size = struct.unpack("!I", await asyncio.wait_for(reader.readexactly(4), timeout))[0]
    if size < 2 or size > MAX_FRAME:
        raise ValueError("Invalid frame length")
    body = await asyncio.wait_for(reader.readexactly(size), timeout)
    data = json.loads(body.decode("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
    if not isinstance(data, dict):
        raise ValueError("Frame must contain an object")
    return data


async def write_frame(writer: asyncio.StreamWriter, data: Message | dict) -> None:
    writer.write(encode_frame(data))
    await asyncio.wait_for(writer.drain(), 5)


def check_fresh(message: Message) -> None:
    age = time.time() - message.timestamp
    if not math.isfinite(age) or age > MAX_AGE or age < -5:
        raise ValueError("Event is stale or has a future timestamp; capture a fresh action")
