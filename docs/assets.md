# Asset provenance and anatomical review

| Asset | Source and license | Current status |
|---|---|---|
| Procedural 3D specimen | Original geometry in `frontend/src/Specimen.jsx`; repository code | Interaction schematic only; not validated anatomical geometry |
| Virtual instruments | Original geometry in the same file | Simplified interaction objects, no clinical simulation |
| Interface icons | lucide-react, ISC license | Installed dependency; preserve its license |
| Interface fonts | Google Fonts DM Sans and Manrope, SIL Open Font License | Optional remote stylesheet; Arial is offline fallback |
| MediaPipe Pose Lite model | Google MediaPipe model host, version 1 URL in download tool | Local runtime asset; consult the model card and distribution terms before redistribution |

The visual schematic is labelled in the interface. A clinically reviewed external model has not been acquired. Replace or supplement it with an appropriately licensed model, record creator/source/license/modifications, verify FDI identity and tissue labels with the reviewer, and record the review outcome before checking S5-02.

The specimen in the presentation is not extracted and reused as a licensed anatomical mesh. No patient material is needed for this coursework implementation.
