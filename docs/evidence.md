# Rubric evidence register

Status distinguishes implemented code, synthetic/local automated checks, and pending human/hardware validation.

| Criterion | Available artifact | Verification | Remaining evidence |
|---|---|---|---|
| Scenario | requirements.md, scenarios.md | Acceptance conditions mapped to runtime behavior | Full live sensor journey |
| PACT | research/PACT.md | Decisions and validation methods documented | Update with actual participant findings |
| Survey and critical analysis | Survey, response CSV and analysis template | Prepared materials only | Real distribution, responses and critical analysis |
| Figma interface | React screens, CSS tokens, design-handoff.md | Browser verification recorded in PROGRESS.md when executed | Editable Figma source and actual link |
| MediaPipe and DollarPy | workers/vision.py, gestures.py, gesture-evaluation.md | Classifier fixtures and code checks only until live trial | Live skeleton, real templates, held-out attempts and real commands |
| Bluetooth | workers/bluetooth.py, ble-peripheral.md | ID parsing and synthetic TCP events | Radio discovery, peripheral read and two real ID trials |
| Socket programming | app.py, protocol.py, test_integration.py | Independent server process, real TCP and WebSocket connections | Repeat within the final live journey |
| Context content | context.py, engine tests | Different profile/layer/tool content and isolated journals | Identity sourced from an actual BLE read |

## Live hardware record to complete

- Software commit:
- Operating system and camera model/index:
- Bluetooth adapter and peripheral:
- Figma URL:
- Anatomical asset license and review:
- Actual gesture library counts and evaluation sample sizes:
- Actual observed successes, failures and recoveries:
- Video or screenshot evidence links:
- Trello URL:

Do not fill these fields with assumed outcomes. Test sensor events are not physical observations.
