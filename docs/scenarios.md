# Usage scenarios

## A Beginner dental student

**Context:** A student learning tooth anatomy at a laptop, unfamiliar with gesture interaction. Registered profile level is beginner.

**Prerequisites:** Application running; registered BLE peripheral available; appropriate camera positioning; model identified as reviewed anatomy or schematic.

1. Discover project BLE devices, explicitly choose one, and read its UserID.
2. Load the user's beginner instructions and start the molar exercise.
3. Read the camera explanation, connect the vision worker, calibrate, and explicitly enter tracking mode.
4. Select tooth 16 from the map and confirm selection using a recorded V gesture or the equivalent manual control.
5. Isolate the specimen, rotate it, and inspect the selected layer. Record a circle to open layer exploration.
6. Select the virtual mirror, move it, and confirm placement. The interface names the active tool.
7. Review the interaction checkpoints, enter a reflection, and save.
8. Reopen Journal and verify the saved entry and note for this UserID.

**Success:** The student completes the flow, identifies the selected tooth and active tool, and finds their saved reflection. Manual operation remains available if gestures are unsuitable.

## B Experienced learner

**Context:** The same device hosts a different registered application UserID with an experienced learning profile.

1. Finish or explicitly discard the current session before changing identity.
2. Read the new UserID over BLE and load a fresh session.
3. Confirm that content now emphasizes anatomical relationships and self-directed questions, while onboarding is condensed.
4. Explore the layers, position the mirror, and save a separate reflection.

**Success:** The actual guidance differs from beginner mode. Neither progress nor notes from the previous user appear in this user's Journal.

## C Teaching demonstrator

**Context:** A demonstrator presents the specimen to a small group using a classroom display.

1. Load a registered demonstrator profile.
2. Open tooth 16, enable a layer and read the discussion prompts.
3. Name the current layer and active tool; move the model to support explanation.
4. Request reset, cancel once to preserve the view, then explicitly confirm reset when needed.

**Success:** The display provides teaching prompts and stable labels; reset does not erase saved notes.

## D Tracking loss

**Trigger:** The student is manipulating a tool or recording a gesture and their wrist leaves view or visibility becomes unreliable.

1. Cancel the incomplete gesture capture.
2. Set tracking to lost, freeze manipulation and retain the specimen and tool transforms.
3. Explain how to return to view. Allow manual mode if the user chooses it.
4. When tracking becomes available, show readiness but keep the session paused.
5. Resume only after explicit user confirmation; never replay buffered gesture commands.

**Success:** No unintended command is applied while tracking is lost, and the retained scene resumes without restarting the activity.

## E Device and network failures

- No BLE device: explain the service filter, permit retry and keep manual guest mode visibly distinct.
- Multiple devices: require selection; never use proximity alone to choose a person.
- Unknown UserID: preserve the current identity and show an actionable error.
- BLE disconnect: show identity connection loss; retain the current session and require explicit reconnect.
- Camera unavailable: show the reason and route to manual operation.
- TCP worker disconnect: mark the corresponding worker offline; vision loss pauses gesture control.
- Browser disconnect: disable changes, reconnect, and fetch a full authoritative snapshot before continuing.
