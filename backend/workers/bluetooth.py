"""Real BLE discovery and GATT UserID reads; scan only on explicit request."""
import argparse
import asyncio
import logging
import re

from bleak import BleakClient, BleakScanner

from backend.workers.client import WorkerClient

SERVICE_UUID = "7d8f0001-9c7a-4b82-8f10-2da6d7e04a31"
USER_ID_UUID = "7d8f0002-9c7a-4b82-8f10-2da6d7e04a31"


def parse_user_id(data: bytes) -> str:
    if not 1 <= len(data) <= 64:
        raise ValueError("UserID must be 1–64 UTF-8 bytes")
    value = data.decode("utf-8", errors="strict").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise ValueError("UserID must contain only letters, digits, hyphens or underscores")
    return value


async def run(port: int):
    transport = WorkerClient("bluetooth", port)
    network = asyncio.create_task(transport.run())
    devices = {}
    peripheral = None
    try:
        while True:
            await transport.connected.wait()
            command = await transport.commands.get()
            if command.get("session_id") != transport.session_id:
                continue
            try:
                kind = command["command"]
                if kind == "shutdown":
                    return
                if kind == "ble_scan":
                    await transport.emit("BLE_STATUS", {"status": "scanning"})
                    found = await BleakScanner.discover(timeout=5, service_uuids=[SERVICE_UUID], return_adv=True)
                    devices = {address: device for address, (device, adv) in found.items() if SERVICE_UUID in [s.lower() for s in (adv.service_uuids or [])]}
                    devices = dict(list(devices.items())[:50])
                    await transport.emit("BLE_DEVICES", {"devices": [{"id": key, "name": (device.name or "DentaVerse peripheral")[:100]} for key, device in devices.items()]})
                    await transport.emit("BLE_STATUS", {"status": "connected" if peripheral and peripheral.is_connected else "idle", "error": "No DentaVerse service found. Configure a peripheral with the documented UUID." if not devices else ""})
                elif kind == "ble_connect":
                    device_id = command["payload"].get("device_id")
                    if device_id not in devices:
                        raise ValueError("Device is not in the latest project scan")
                    if peripheral:
                        await peripheral.disconnect()
                    await transport.emit("BLE_STATUS", {"status": "connecting"})
                    loop = asyncio.get_running_loop()
                    def disconnected(_):
                        loop.call_soon_threadsafe(lambda: asyncio.create_task(transport.emit("BLE_STATUS", {"status": "disconnected"})))
                    peripheral = BleakClient(devices[device_id], disconnected_callback=disconnected, timeout=15)
                    await peripheral.connect()
                    value = await peripheral.read_gatt_char(USER_ID_UUID)
                    user_id = parse_user_id(bytes(value))
                    # Do not switch workspace ownership based on a delayed read from an older session.
                    if command["session_id"] != transport.session_id:
                        await peripheral.disconnect()
                        continue
                    await transport.emit("USER_IDENTIFIED", {"user_id": user_id}, command["session_id"], wait_ack=True)
                    await transport.emit("BLE_STATUS", {"status": "connected"})
                elif kind == "ble_disconnect":
                    if peripheral:
                        await peripheral.disconnect()
                        peripheral = None
                    await transport.emit("BLE_STATUS", {"status": "disconnected"})
            except Exception as exc:
                await transport.emit("BLE_STATUS", {"status": "error", "error": str(exc)[:300]})
    finally:
        network.cancel()
        await asyncio.gather(network, return_exceptions=True)
        if peripheral and peripheral.is_connected:
            await peripheral.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run(args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
