# BLE peripheral setup and live verification

For the available Android phone, follow the [Arabic nRF Connect setup guide](android-ble-setup.md).

The worker starts without scanning. Click Discover devices in Session setup or Preferences to scan only for the DentaVerse service. A laptop Bluetooth adapter and a peripheral capable of advertising a custom BLE GATT service are required. A compatible phone GATT-server app or an available development board may be used; ordinary phone Bluetooth visibility alone does not expose the required characteristic.

| Property | Value |
|---|---|
| Service UUID | `7d8f0001-9c7a-4b82-8f10-2da6d7e04a31` |
| Readable UserID characteristic UUID | `7d8f0002-9c7a-4b82-8f10-2da6d7e04a31` |
| Encoding | UTF-8, 1–64 bytes; letters, numbers, `_` and `-` |
| Example values | `DV-STUDENT-01`, `DV-STUDENT-02`, `DV-TEACHER-01` |

1. Create the service and readable characteristic on the peripheral. Advertise the service UUID.
2. Put one registered ID in the characteristic value. Run `python -m backend.workers.bluetooth`.
3. Click Discover devices, choose the intended device and select Connect & read ID.
4. Confirm the workspace reports Bluetooth identity and displays the correct profile content.
5. Save a note. Disconnect, change the advertised application's ID to another registered ID (or use another peripheral), then reconnect/read again.
6. Verify different content and isolated journals. Restore the first ID and confirm its note is retained.
7. Test an unknown ID, multiple matching devices, peripheral disconnect and disabled adapter.

Record actual hardware model, OS, peripheral configuration, observed results and software commit in `docs/evidence.md`. Never describe the synthetic integration test as proof of radio discovery or a GATT read.

These IDs select local educational profiles. They are demonstration registrations, not real student records or a production authentication mechanism.
