# DentaVerse

Gesture-based dental anatomy learning workbench for the HCI Phase II project. The first activity explores FDI 16 with a local React/Three.js interface, Python coordinator, SQLite journal, TCP sensor workers and context-dependent learning guidance.

## Track implementation

- [Execution checklist in Arabic](IMPLEMENTATION_PLAN.md)
- [Progress and verification log](PROGRESS.md)
- [Rubric evidence and outstanding real-world checks](docs/evidence.md)

Completed code and automated checks do not imply completed participant research, live camera/BLE validation, editable Figma work or anatomical review. The current specimen is visibly labelled as a procedural schematic.

## Quick start on Windows

Use Python 3.12 and Node.js 22.19+ or a newer supported LTS. Open PowerShell in the repository.

```powershell
powershell -File tools/setup.ps1
powershell -File tools/run.ps1
```

Open http://127.0.0.1:8000. The default is a clearly labelled manual guest workspace; no sensors are fabricated. Choose Anatomy atlas → Inspect specimen, turn the model, explore layers, place the mirror, then Finish & review → Save reflection → Open journal.

Preferences includes **Manual profile preview** to inspect beginner, experienced and demonstrator content. This is explicitly manual and does not count as Bluetooth evidence. Profile changes preserve ownership and request a decision if an activity is unsaved.

### Enable the real camera and Bluetooth workers

```powershell
powershell -File tools/setup.ps1 -WithVision
powershell -File tools/run.ps1 -Vision -Bluetooth
```

The vision option opens a local camera preview. No video is recorded or transmitted. A compatible BLE peripheral must advertise the [documented service](docs/ble-peripheral.md); the worker scans only when Discover devices is selected. Collect actual movement templates before gesture mode; none are shipped as fake captures. See the [collection and evaluation procedure](docs/gesture-evaluation.md).

Before a live trial, `python tools/check_vision_runtime.py` verifies model/API initialization on a blank image without opening the camera. Run `.venv\Scripts\python.exe -m pip check` to verify the full installation. A successful blank-image check is not evidence of live tracking.

### Development

Run these commands in separate terminals from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
npm.cmd --prefix frontend run dev
# Optional real workers:
.venv\Scripts\python.exe -m backend.workers.bluetooth
.venv\Scripts\python.exe -m backend.workers.vision --camera 0
```

Development UI: http://127.0.0.1:5173. The browser uses WebSocket; independent workers use framed TCP on port 8766. The release UI build is served directly by the coordinator after `npm.cmd --prefix frontend run build` and a server restart.

## Verify

```powershell
.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
```

Browser tests use Microsoft Edge, a separate ignored SQLite database, and dedicated ports 5174/8001/8767. They never reuse the user's running workstation. Install Edge if unavailable, or run `npx playwright install msedge` from `frontend`. The Python integration suite starts an isolated coordinator process with temporary storage and **synthetic** sensor messages to verify actual TCP/WebSocket transport.

## Files and configuration

- `backend/`: coordinator, context engine, storage, protocol, classifier and sensor workers.
- `frontend/`: interface, schematic 3D specimen and browser tests.
- `docs/`: requirements, scenarios, PACT, research materials, architecture and evidence.
- `tools/`: setup, run and official model-download tools.
- `DENTAVERSE_DB`: optional SQLite file path; default `data/dentaverse.db`.
- `DENTAVERSE_TCP_PORT`: optional coordinator worker port; default `8766`. Pass the same `--port` to manually launched workers.

Runtime databases, sensor templates, models, camera material and local review files are ignored by Git. Keep this local coursework server bound to `127.0.0.1`; BLE profile selection is not a production authentication service.

## Troubleshooting

- **Opening your workbench stays visible:** start the coordinator and verify `/api/health`.
- **Camera unavailable:** check OS permissions, close other camera apps, try another `--camera` index, and verify the model was downloaded.
- **No BLE device found:** advertise the exact service UUID; normal Bluetooth discoverability is insufficient.
- **No gesture match:** calibrate and collect genuine V, circle and Z templates. Tune the initial threshold against held-out captures.
- **Tracking recovered but paused:** explicitly Resume or choose manual controls; recovery never replays old gestures.
- **Certificate validation during install:** the setup helper requests Node's system certificate store. Fix local CA trust rather than disabling certificate validation.

See [architecture](docs/architecture.md), [protocol](docs/protocol.md), [design handoff](docs/design-handoff.md), and [asset provenance](docs/assets.md).
