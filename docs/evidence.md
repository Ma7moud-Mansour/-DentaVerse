# Rubric evidence register

Status distinguishes implemented code, synthetic/local automated checks, and pending human/hardware validation.

| Criterion | Available artifact | Verification | Remaining evidence |
|---|---|---|---|
| Scenario | requirements.md, scenarios.md | Acceptance conditions mapped to runtime behavior | Full live sensor journey |
| PACT | research/PACT.md | Decisions and validation methods documented | Update with actual participant findings |
| Survey and critical analysis | Local consent/export form, CSV analyzer, critical-analysis.md and analysis template | Export/consent/no-upload browser check and denominator/duplicate checks; actual development feedback analyzed separately | Actual 12-question survey distribution/responses and resulting participant analysis |
| Figma interface | React screens, CSS tokens, design-handoff.md | Browser verification recorded in PROGRESS.md when executed | Editable Figma source and actual link |
| MediaPipe and DollarPy | workers/vision.py, wave.py, gestures.py, wave-control.md and camera-verification.md | Real camera/33-point body and user-confirmed 21-point hands; actual DollarPy matcher on declared synthetic wave and TCP/WebSocket tool switching; manually recorded shapes retained separately | Human wave accuracy and held-out recorded-shape trials; authored wave reference is not a human capture |
| Bluetooth | workers/bluetooth.py, ble-peripheral.md, android-ble-setup.md | ID parsing/synthetic TCP events and previous real radio scan; Android setup prepared, no USB phone attached for autonomous setup | Compatible peripheral configuration, two actual UserID reads and resulting content changes |
| Socket programming | app.py, protocol.py, test_integration.py | Independent server process, real TCP and WebSocket connections | Repeat within the final live journey |
| Context content | context.py, engine tests | Different profile/layer/tool content and isolated journals | Identity sourced from an actual BLE read |

Software verification: 102 local Python tests and 8 browser scenarios passed. The browser fixture uses an isolated database/ports and clearly synthetic sensor inputs; image evidence does not establish a physical sensor or clinical accuracy result. [Reviewed interface images](submission/README.md). [Complete Phase II submission map](phase-ii-submission.md).

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
