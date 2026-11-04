# PACT analysis

These are design assumptions pending the survey and observed-use study. Do not describe them as participant findings.

| Dimension | Observation or assumption | Implementation decision | Verification |
|---|---|---|---|
| People | Beginners may not know FDI notation or gestures | Tooth number plus name, full guidance, visible gesture guide | Ask learners to identify the selected tooth without prompting |
| People | Experienced learners may want less onboarding | Server-selected concise content and deeper prompts | Compare content for two registered profiles |
| People | Demonstrators explain to groups | Teaching prompts, persistent anatomical labels | Demonstrator walkthrough |
| People | Dominant hand and movement comfort vary | Choose dominant wrist for recorded paths; fixed left-tooth/right-instrument roles follow the requested bimanual design; offer manual operation and explicit pause | Test both configured hands and keyboard controls |
| Activities | Find and isolate a tooth | Tooth map, selected identity, isolate command | Complete the FDI 16 selection task |
| Activities | Inspect layers and use tools | Layer controls, named active tool, task-specific help | Ask which object the next action will move |
| Activities | Save and reflect | Review and per-user journal | Save, restart, then retrieve the note |
| Contexts | Camera setup and lighting vary | Setup explanation, visibility feedback, calibration | Actual camera trials under documented conditions |
| Contexts | Hands may leave view | Cancel capture, pause, retain transforms, explicit resume | Interrupt tracking during manipulation |
| Contexts | Several BLE peripherals may be near the workstation | Filter by service and require device selection | Multiple-device test |
| Contexts | Network workers can disconnect | Worker status, stale-event rejection and reconnect snapshot | Disconnect worker and browser independently |
| Technologies | Body and detailed finger tracking require separate models | Pose plus two-hand Hand Landmarker, required by the user's updated scope | Check both 21-point hands, finger states, loss and body overlay separately |
| Technologies | DollarPy is a point-cloud template matcher | Different geometric shapes, calibration and held-out evaluation | Evaluate genuine templates versus new captures |
| Technologies | TCP is a byte stream | Length-prefixed messages and bounded reads | Fragmentation/coalescing tests |
| Technologies | BLE device identity is not a person's account identity | GATT application ID mapped to local registered profile | Unknown ID and identity switching tests |

## Questions for research

Which explanations are necessary? Is the geometric gesture vocabulary understandable and comfortable? Can learners identify the selected tooth and active tool? Do they understand why interaction paused and how to recover? Does the beginner/experienced distinction match user needs?
