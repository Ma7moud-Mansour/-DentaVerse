# Working agreements

For implementation work on the DentaVerse checklist:

- Read `IMPLEMENTATION_PLAN.md` and `PROGRESS.md` before continuing. Preserve the phased plan without introducing dates or assigning people.
- Complete coherent tasks, run relevant verification, then mark only those task checkboxes complete. Update the progress log with the evidence and any remaining limitations in the same commit.
- The user has requested incremental GitHub delivery: commit completed steps and push them to the existing upstream branch. Never force-push or overwrite another contributor's work. Fetch and reconcile remote changes before pushing when necessary.
- Phase completion requires all required tasks, including external verification. Prepared research materials are not real survey results. Synthetic sensor events are not live camera or BLE evidence. Code or screenshots are not an editable Figma file.
- Keep runtime databases, camera material, gesture captures, secrets and `.review` out of Git. Keep the server bound to loopback.
- Verify backend with `.venv/Scripts/python.exe -m pytest -q`; build frontend with `npm --prefix frontend run build`; run relevant browser checks with `npm --prefix frontend run test:e2e`. Browser checks have dedicated ports and a separate database.
- Use the existing source architecture and design direction. The current procedural specimen must remain labelled as schematic until a licensed anatomical asset is reviewed.
