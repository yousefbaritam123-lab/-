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
