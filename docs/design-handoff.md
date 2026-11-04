# Interface implementation and Figma handoff

## Source direction

The supplied presentation defines a warm enamel surface, dark forest workbench, pale-green primary actions, a stable specimen area and visible recovery. The current implementation follows this direction through shared CSS tokens and React components. Typography uses DM Sans/Manrope when available and Arial offline. No referenced Figma file exists yet; this implementation must not be presented as proof of a completed editable Figma source.

## Tokens

| Token | Value | Use |
|---|---|---|
| Enamel | #F3F2EC | Workspace background |
| Paper | #FCFCF8 | Cards and panels |
| Forest | #1D302C | Primary text and dark cards |
| Specimen | #182521 | 3D stage |
| Focus | #DBEEAB | Primary actions and selected states |
| Bone line | #DEDFD5 | Dividers and secondary borders |
| Muted | #737E73 | Supporting copy |
| Caution | #E9C08F | Interrupted or unavailable state |

Buttons have visible keyboard focus. Dialogs make the background inert and trap Tab within actionable controls. Range inputs have explicit labels. Statuses use words in addition to color. Reduced-motion preference removes transitions. Touch and narrow-screen layouts reflow the inspector underneath the specimen. The workstation is the primary target.

## Screen mapping

| Design area | React implementation | State or behavior |
|---|---|---|
| Studio | App studio branch | Atlas and setup entry points |
| Atlas | App atlas branch, ToothMap | Search, FDI selection, isolate |
| Setup | App setup branch | Worker, visibility and calibration status |
| Isolated specimen | App workbench, Specimen | Licensed molar; drag to rotate, wheel to zoom, draggable instrument grip, slider/keyboard alternatives and illustrative tissues |
| Recovery | App dialog branch | Paused state and explicit resume |
| Camera unavailable | Setup status/error | Actual worker status, manual route |
| Reset confirmation | App dialog branch | Retain or reset transforms |
| Review | App review branch | Interaction checkpoints and reflection |
| Journal and empty journal | App journal branch | Per-user saved entries |
| Preferences | App preferences branch | Input mode, profile preview, template collection |
| Gesture guide | App guide branch | Current V/circle/Z vocabulary |
| Bluetooth identity | BluetoothPanel | Filtered discovery and explicit device selection |

## Editable Figma work still required

Create the frames, components, tokens, variants and flows in an editable Figma file. Include disconnected, paused, unavailable-camera, identity-switch and empty-journal states. Include Hands/Body/Both overlays and independent left/right 21-point hand readouts for open palm, fist, pinch, partial and lost tracking. Match the implemented command vocabulary and distinguish live hand signals from scene bindings. Provide the actual share link and compare frames against the running UI. Screenshot imports alone do not establish editable component work.


## Generated import package

[Download DentaVerse_Figma_Kit.zip](../deliverables/DentaVerse_Figma_Kit.zip), or open the [SVG board](../deliverables/DentaVerse_Figma_Kit/DentaVerse-Editable-Screens.svg) and [local preview](../deliverables/DentaVerse_Figma_Kit/preview.html). [Arabic import instructions](../deliverables/DentaVerse_Figma_Kit/README_AR.md) explain creating a user-owned development plugin, replacing its code.js, and saving/sharing the resulting Design file.

The source contains 17 desktop screens, three component families with nine variants, paint/text styles, and 124 navigation targets. The bundled importer creates native frames, text nodes, instances and prototype reactions using the Plugin API. The model reference is a newly rendered, attributed still from the licensed GLB; there are no camera frames or participant records. Mirror artwork is an editable vector illustration.

The package passed JavaScript syntax, local object-graph contract checks and SVG browser rendering, including a Studio-to-Atlas click. These are **not execution inside Figma**. The current session exposes the Figma skills but no whoami/create_new_file/use_figma tools, so it has not created a native .fig or cloud share link. S4-02 and S4-07 remain open until the importer is run, the resulting file is reviewed in the editor, and its real link is recorded. SVG/screenshot imports alone do not verify native component work.

Rebuild with `node tools/export_figma_model.mjs` (only when the licensed preview asset changes), then `.venv/Scripts/python.exe tools/build_figma_kit.py`. Check the local importer contract with `node tools/check_figma_kit.mjs`; render the local SVG preview with `node tools/preview_figma_kit.mjs`.
