"""Subtitle and non-destructive editorial timeline exports."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_subtitles(project_dir: Path, *, include_speaker: bool = False) -> Path:
    project = Path(project_dir)
    episode = json.loads((project / "episode.json").read_text(encoding="utf-8"))
    names = {item["id"]: item.get("name", item["id"]) for item in episode.get("characters", [])}
    cues = []
    shot_start = 0.0
    for shot in episode.get("shots", []):
        for line in shot.get("dialogue", []):
            text = str(line.get("text", "")).strip()
            if not text:
                continue
            start = shot_start + float(line.get("start_seconds", 0.0))
            end = shot_start + float(line.get("end_seconds", shot.get("duration_seconds", 0)))
            if end <= start:
                raise ValueError(f"Invalid subtitle timing in shot {shot.get('id')}: {line}")
            speaker = names.get(line.get("speaker"), line.get("speaker", ""))
            body = f"{speaker}: {text}" if include_speaker and speaker else text
            cues.append((start, end, body))
        shot_start += float(shot["duration_seconds"])
    cues.sort(key=lambda cue: (cue[0], cue[1]))
    lines = []
    for index, (start, end, body) in enumerate(cues, start=1):
        lines.extend([str(index), f"{_srt_time(start)} --> {_srt_time(end)}", body, ""])
    output = project / "subtitles" / f"{episode.get('id', 'episode')}.srt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8-sig")
    return output


def export_edit_plan(project_dir: Path) -> Path:
    project = Path(project_dir)
    episode = json.loads((project / "episode.json").read_text(encoding="utf-8"))
    fps = int(episode["format"]["fps"])
    cursor = 0.0
    shots = []
    for shot in episode.get("shots", []):
        duration = float(shot["duration_seconds"])
        shots.append({
            "shot_id": shot["id"],
            "start_seconds": round(cursor, 4),
            "end_seconds": round(cursor + duration, 4),
            "start_frame": round(cursor * fps),
            "duration_frames": round(duration * fps),
            "location": shot.get("location"),
            "actors": shot.get("actors", []),
            "camera": shot.get("camera", {}),
            "effects": shot.get("effects", []),
            "dialogue_lines": len(shot.get("dialogue", [])),
        })
        cursor += duration
    plan: dict[str, Any] = {
        "schema_version": 1,
        "episode_id": episode.get("id"),
        "fps": fps,
        "duration_seconds": cursor,
        "video": "renders/episode.mp4",
        "audio": "audio/final_mix.wav",
        "shots": shots,
        "subtitle": f"subtitles/{episode.get('id', 'episode')}.srt",
        "status": "editorial_plan",
    }
    folder = project / "production"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "edit_plan.json"
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        import opentimelineio as otio
    except ImportError:
        plan["otio_status"] = "not_exported_install_opentimelineio"
        output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return output
    timeline = otio.schema.Timeline(name=str(episode.get("title", episode.get("id"))))
    timeline.metadata["studio"] = {
        "episode_id": episode.get("id"),
        "shots": shots,
        "subtitle": plan["subtitle"],
    }
    picture = otio.schema.Track(name="Picture", kind=otio.schema.TrackKind.Video)
    video_path = (project / "renders" / "episode.mp4").resolve()
    picture.append(otio.schema.Clip(
        name="Episode Picture",
        media_reference=otio.schema.ExternalReference(target_url=video_path.as_uri()),
        source_range=otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(0, fps),
            duration=otio.opentime.RationalTime(round(cursor * fps), fps),
        ),
    ))
    timeline.tracks.append(picture)
    audio_path = project / "audio" / "final_mix.wav"
    if audio_path.is_file():
        sound = otio.schema.Track(name="Final Mix", kind=otio.schema.TrackKind.Audio)
        sound.append(otio.schema.Clip(
            name="Episode Audio",
            media_reference=otio.schema.ExternalReference(target_url=audio_path.resolve().as_uri()),
            source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, fps),
                duration=otio.opentime.RationalTime(round(cursor * fps), fps),
            ),
        ))
        timeline.tracks.append(sound)
    otio_path = folder / "edit_plan.otio"
    otio.adapters.write_to_file(timeline, str(otio_path))
    plan["otio_status"] = str(otio_path.relative_to(project))
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
