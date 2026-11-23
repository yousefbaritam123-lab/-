# Using the 60-character cast in the renderer

The renderer now resolves the complete validated assets/characters/cast_60/catalog.json
at the start of a render. A profile can be selected with an actor cast_id, or by
using the catalog profile ID as the actor's own id. Profile appearance and proportions
become defaults; explicit actor overrides take precedence. Every profile uses the shared
canonical rig and motion runtime, so visual identity varies while animation stays consistent.

## Commands

```powershell
python -m studio.cli cast-list projects/episode-001
python -m studio.cli cast-add projects/episode-001 extra_001 --shot-id shot-001 --actor-id vendor --x 720 --action wave
python -m studio.cli validate projects/episode-001
python -m studio.cli render projects/episode-001 --frames 0:90
```

Use any ID printed by cast-list (for example extra_001). The command adds the
character record to episode.json and its actor ID to the selected shot. It refuses
unknown profiles, unknown shot IDs, and duplicate actor IDs.

## Scope and quality boundary

The 60 entries are procedural appearance/proportion variants sharing one rig
topology, not 60 separately hand-drawn rigs. This integration makes all 60
available to the real Skia renderer and its existing motion library, hands,
face controls, and cinematic effects. It does not claim 60 unique animation rigs
or automatically generate new detailed artwork for each profile.
