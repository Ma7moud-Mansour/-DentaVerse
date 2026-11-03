# DentaVerse requirements and acceptance criteria

## Core scope

A local desktop-browser educational workbench for exploring FDI 16, the upper-right first permanent molar. A beginner, experienced student, or teaching demonstrator receives different learning guidance. BLE supplies an application UserID; the server loads its registered profile. Pose landmarks supply a wrist trajectory; DollarPy classifies deliberately recorded geometric gestures. Independent Python workers send events to a coordinator over TCP. The browser receives state over WebSocket.

The first complete learning activity is: identify tooth 16, inspect its form, explore its layers, position a virtual mirror, review, and save a reflection. Both manual controls and gestures must use the same validated server actions.

## Acceptance matrix

| ID | Requirement | Observable acceptance | Rubric |
|---|---|---|---|
| R01 | Scenario coverage | Beginner, experienced learner, demonstrator, and recovery stories include prerequisites and outcomes | Scenario |
| R02 | PACT | Every PACT observation has an implementation implication and verification method | PACT |
| R03 | Research | Actual participant counts, anonymous responses, limitations and evidence-to-change links | Survey and critical analysis |
| R04 | UI implementation | Editable Figma source maps to implemented screens and recovery states | Figma |
| R05 | Skeleton | Live camera displays body connections and wrist coordinates with visibility checks | MediaPipe |
| R06 | Classification | A held-out live wrist gesture passes DollarPy, produces one event, and changes the correct UI state | DollarPy |
| R07 | Identity | Filtered BLE discovery, explicit device selection, GATT UserID read and registered profile resolution | Bluetooth |
| R08 | Communication | Worker and coordinator are independent processes; framed TCP event results in a WebSocket state change | Sockets |
| R09 | Context | Different registered profiles load substantively different guidance; tooth, layer, tool and tracking changes update content | Context |
| R10 | Persistence | Saved session and reflection survive restart and remain isolated by UserID | Core journey |
| R11 | Recovery | Tracking or worker loss stops gesture actions; recovery needs explicit resume | Scenario and context |
| R12 | Repeat safety | Duplicate, stale and wrong-session events cannot repeat or misdirect a command | Sockets |

## State and identity rules

- Local development starts in a clearly labelled manual guest workspace. Guest mode never claims BLE identification.
- User profile IDs are registered application identifiers, not Bluetooth names or MAC addresses. No automatic profile switch while a learning session is active.
- A profile change requires save-and-switch or discard confirmation. Journal ownership comes from the active server session.
- The server is authoritative for progress, tool, layer, pause state and session identity. Client-supplied role or completion counts are not trusted.
- Tracking loss clears any gesture capture and blocks gesture actions. Recovering visibility does not automatically resume the workbench.
- A transient network interruption must show a disconnected state and disable mutating controls until a fresh snapshot is received.
- Completed interaction checkpoints describe practice progress, not clinical skill or treatment accuracy.

## Content and assets

- A schematic specimen may be used while building interaction. It must be visibly labelled and cannot satisfy the reviewed anatomical asset requirement.
- Record asset source, creator, license, modifications and faculty/anatomy review before claiming anatomical validation.
- Camera frames are processed locally, never included in TCP messages, and are not recorded by default.
- Collected gesture templates need permission for use; store trajectories without participant names.

## Deferred scope

Full treatment simulation, diagnosis, scoring clinical performance, recognizing physical dental instruments, a full 3D dentition, cloud accounts, instructor rosters and mobile delivery. The user explicitly expanded scope to both hands and all fingers: dedicated Hand Landmarker, live per-hand pose/motion signals and independent overlays are now required. Binding those signals to scene commands and physically validating them remain separate tasks. The existing DollarPy vocabulary uses deliberately recorded V, circle and Z paths.

## Open rubric questions

The visible weights sum to 9 although the cover uses /10. The Bluetooth row ends with “discover” without specifying its object. Confirm whether the Figma criterion expects both editable source and implemented UI; plan for both until clarified. No additional scoring rules or participant minimums are invented here.
