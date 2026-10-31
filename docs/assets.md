# Asset provenance and anatomical review

| Asset | Source and license | Current status |
|---|---|---|
| External molar surface | University of Dundee, School of Dentistry; CC BY 4.0; original model and pinned redistribution documented in `frontend/public/models/ATTRIBUTION.md` | Licensed educational mesh, re-centered and mirrored at runtime; independent anatomy review pending |
| Dentin and pulp illustrations | Original runtime illustration in `frontend/src/Specimen.jsx`; scaled external envelope and schematic chamber/canals | Explicitly illustrative; not segmented tissues from the source GLB |
| Virtual instruments | Original geometry in the same file | Simplified interaction objects, no clinical simulation |
| Interface icons | lucide-react, ISC license | Installed dependency; preserve its license |
| Interface fonts | Google Fonts DM Sans and Manrope, SIL Open Font License | Optional remote stylesheet; Arial is offline fallback |
| MediaPipe Pose Lite model | Google MediaPipe model host, version 1 URL in download tool | Local runtime asset; consult the model card and distribution terms before redistribution |

The previous sphere-and-cone placeholder has been removed. The bundled full-resolution molar is attributed visibly in the viewer and includes its original attribution metadata. See the asset attribution file for provenance, SHA-256 and runtime adaptations. The source is a left maxillary first molar and is mirrored for the right-sided activity. Verify the adaptation and tissue illustrations with the reviewer and record the outcome before checking S5-02.

The specimen in the presentation is not extracted and reused as a licensed anatomical mesh. No patient material is needed for this coursework implementation.
