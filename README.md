# DentaVerse

Gesture-based dental anatomy learning workbench for the HCI Phase II project. The first activity explores FDI 16 with a local React/Three.js interface, Python coordinator, SQLite journal, TCP sensor workers and context-dependent learning guidance.

## Track implementation

- [Execution checklist in Arabic](IMPLEMENTATION_PLAN.md)
- [Progress and verification log](PROGRESS.md)
- [Rubric evidence and outstanding real-world checks](docs/evidence.md)

Completed code and automated checks do not imply completed participant research, live camera/BLE validation, editable Figma work or anatomical review. The external specimen uses a licensed University of Dundee model, mirrored for the right-sided activity. Internal tissue views remain illustrative. [Model attribution and adaptations](frontend/public/models/ATTRIBUTION.md).

## Quick start on Windows

Use Python 3.12 and Node.js 22.19+ or a newer supported LTS. Open PowerShell in the repository.

```powershell
powershell -File tools/setup.ps1
powershell -File tools/run.ps1
```

Open http://127.0.0.1:8000. The default is a clearly labelled manual guest workspace; no sensors are fabricated. Choose Anatomy atlas → Inspect specimen. Drag the tooth to rotate, scroll over it to zoom, and drag the selected instrument or its circular grip to move it. Focus the viewer and use arrow keys to rotate, or +/- to zoom. Sliders remain available. Then Finish & review → Save reflection → Open journal.

Preferences includes **Manual profile preview** to inspect beginner, experienced and demonstrator content. This is explicitly manual and does not count as Bluetooth evidence. Profile changes preserve ownership and request a decision if an activity is unsaved.

### Enable the real camera and Bluetooth workers

```powershell
powershell -File tools/setup.ps1 -WithVision
powershell -File tools/run.ps1
```

Open **Session setup → Start camera**. The page displays live camera video with body points over the same mirrored frame. Video and coordinates travel only through the local coordinator; frames are kept in memory and are not recorded. Saved gesture templates contain coordinate paths only. Choose your preferred hand, keep both shoulders and that wrist in frame, and select **Calibrate position**. Hold your upper body still until stable calibration completes, then enter gesture mode. Stop camera releases the camera and returns to manual input. The camera index selector can try other attached cameras.

Select **Start Bluetooth service**, then **Discover devices** when ready. A compatible BLE peripheral must advertise the [documented service](docs/ble-peripheral.md); starting the service alone does not scan. Collect actual movement templates before gesture recognition; none are shipped as fake captures. See the [collection and evaluation procedure](docs/gesture-evaluation.md). The optional `-Vision -Bluetooth` launcher flags remain available for terminal use; `-Vision` opens an additional local camera preview.

Before a live trial, `python tools/check_vision_runtime.py` verifies model/API initialization on a blank image without opening the camera. Run `.venv\Scripts\python.exe -m pip check` to verify the full installation. A successful blank-image check is not evidence of live tracking.

For a bounded real-camera diagnostic, stop any active camera service first, then run `.venv\Scripts\python.exe tools/check_camera_runtime.py --camera 0`. This opens a separate coordinator with isolated storage and an ephemeral TCP port, prints landmark-count/status metadata for 15 previews, and releases the camera. It does not record images, save templates, calibrate a participant or measure gesture accuracy. See the [observed hardware check](docs/camera-verification.md).

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
- `frontend/`: interface, licensed molar surface, internal tissue illustrations and browser tests.
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
