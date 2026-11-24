# Lossless preparation of the existing 60-character SVG cast

Run from the repository root:

```powershell
python -m studio.cli prepare-svg-cast assets/characters/cast_60/contact_sheet.svg assets/characters/prepared_cast_60
```

The command extracts the 60 existing `extra-001` … `extra-060` groups into
individual SVG files. It excludes the contact-sheet background, grid, title
and labels, while retaining each character group's vector elements, path data,
colors, stroke properties and original geometry. The source contact sheet is
never edited. It refuses to overwrite a non-empty output directory.

Each original direct SVG element is wrapped in a named source layer and
recorded in `cast_manifest.json`. This is deliberately conservative: some
source paths contain two arms or two legs in one compound path, so an element
boundary is not automatically an anatomical boundary. The extraction stage
does **not** claim that these assets are fully rigged or ready for joint
animation. The next stage must map and, where needed, split compound paths
without changing their rendered appearance, then add pivots and validate
poses against the original source.

## Joint-map and articulation preparation

The extraction now also writes one `*.rig.json` file per character with a
15-point skeleton landmark map: head, neck, both shoulders, elbows, wrists,
pelvis, hips, knees and ankles. It defines parent-child bone links for the
head, torso, arms and legs. These are initial 2D pivot coordinates in the
200×220 character-cell coordinate space, not a claim of validated motion.

A companion `*.rig_layers.svg` now exports each original arm as four segments per
side: upper-arm outline/skin and forearm outline/skin, split exactly at the
elbow vertex already present in the source `M/L` path. The source line widths,
colors and round caps are retained. The left/right arm endpoints are also used
to derive shoulder, elbow and wrist coordinates for each character. Paired foot
subpaths are exported when present.
The original full paths remain intact in the main extracted SVG; the new
articulation file is an additional derivative and does not overwrite source
artwork.

## Original Youssef and Adam model sheets

The Blender bridge also extracts the character-only vector group from
`assets/characters/youssef/design_sheet.svg` and
`assets/characters/adam/design_sheet.svg`. The surrounding model-sheet
background, title and notes are excluded; the original character group,
colors, linework and transforms are preserved. This gives the main two actors
their actual approved model-sheet drawings in Blender instead of the legacy
procedural substitute.

## Blender source-art integration

`studio.blender_bridge` prepares the extracted cast automatically when a Blender
render includes `cast_id` values such as `extra_001`. It also extracts the
character-only groups from the official Youssef and Adam model sheets.

Each original SVG is rasterized to a transparent PNG at 3× its viewBox dimensions
with CairoSVG. Blender displays that image on a transparent emission plane under
the actor transform. This keeps open strokes, outlines, fills, clothing and face
details that Blender's built-in SVG importer omits. It uses the source artwork,
not a procedural puppet replacement.

The current Blender integration animates the complete artwork plane as one
character. The separated arm paths and joint maps are not yet connected to
independent Blender pivots. The lower-body silhouette remains connected and is
not yet separated into moving thighs and shins. Hands/fingers are not separately
drawn in the source art. The 60-character cast and the named Youssef/Adam art
must pass the visual review before this can be called a production-ready rig.
