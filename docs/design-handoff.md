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
| Isolated specimen | App workbench, Specimen | Three.js rotation, zoom, layers and instruments |
| Recovery | App dialog branch | Paused state and explicit resume |
| Camera unavailable | Setup status/error | Actual worker status, manual route |
| Reset confirmation | App dialog branch | Retain or reset transforms |
| Review | App review branch | Interaction checkpoints and reflection |
| Journal and empty journal | App journal branch | Per-user saved entries |
| Preferences | App preferences branch | Input mode, profile preview, template collection |
| Gesture guide | App guide branch | Current V/circle/Z vocabulary |
| Bluetooth identity | BluetoothPanel | Filtered discovery and explicit device selection |

## Editable Figma work still required

Create the frames, components, tokens, variants and flows in an editable Figma file. Include disconnected, paused, unavailable-camera, identity-switch and empty-journal states. Match the final implemented vocabulary rather than copying the presentation's earlier pinch vocabulary. Provide the actual share link and compare frames against the running UI. Screenshot imports alone do not establish editable component work.
