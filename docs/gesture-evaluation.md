# Gesture collection and evaluation

The repository ships with zero real templates. The vision worker uses MediaPipe Pose wrist trajectories and DollarPy. Synthetic fixtures in tests exercise the algorithm only; they are never installed into the working library.

## Collect

1. Obtain permission for anonymous coordinate-path collection. Do not record video or names.
2. Download the model, start the coordinator and vision worker, then calibrate in Session setup.
3. Open Preferences. Click Record V, Record circle or Record Z. Draw one clear shape with the chosen wrist and click Save capture.
4. Keep both shoulders and the chosen wrist visible. Losing visibility, control context or connection cancels capture. Captures last at most eight seconds.
5. Collect several repetitions and variation across consenting people. Template counts update only after actual successful saves.

Paths are smoothed and normalized relative to the calibrated shoulder center and width. The live library is ignored by Git at `data/templates/gestures.json`. Keep actual participant metadata separately and anonymously if needed.

## Evaluate

Use new attempts that were not added to the library. For each attempt log anonymous code, intended shape, recognized shape, matching score, accepted/rejected status, intended action, observed action, camera/lighting and commit. Do not tune the threshold on the same final evaluation attempts without disclosing it.

The initial matching threshold of 0.72 is a development hypothesis, not measured accuracy or a rubric requirement. Report a confusion table, rejection rate, accidental commands, latency and relevant sample sizes. Set the final threshold based on observed tradeoffs and retain rejected attempts in the report.

$P ignores stroke order and direction. A left-to-right line and the same line drawn right-to-left must not be treated as distinct commands based only on DollarPy. V confirms the current selection or mirror placement; circle selects enamel exploration; Z pauses. The scene must be explicitly ready for the action. Pause/resume/input-mode changes invalidate old captures through the control epoch.
