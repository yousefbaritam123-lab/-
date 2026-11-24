"""Dialogue script coverage and timing quality gates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def audit_dialogue(project_dir: Path) -> dict[str, Any]:
    project = Path(project_dir)
    episode = json.loads((project / "episode.json").read_text(encoding="utf-8"))
    known = {item["id"]: item.get("name", item["id"]) for item in episode.get("characters", [])}
    errors: list[str] = []
    warnings: list[str] = []
    total_lines = 0
    total_words = 0
    timed_words = 0
    timed_seconds = 0.0
    elapsed = 0.0
    shot_reports = []
    for shot in episode.get("shots", []):
        shot_id = str(shot.get("id", "unknown"))
        duration = float(shot.get("duration_seconds", 0))
        actors = set(shot.get("actors", []))
        lines = shot.get("dialogue", [])
        intervals: dict[str, list[tuple[float, float, int]]] = {}
        shot_words = 0
        for index, line in enumerate(lines, start=1):
            total_lines += 1
            text = str(line.get("text", "")).strip()
            speaker = str(line.get("speaker", ""))
            if not text:
                errors.append(f"{shot_id} line {index}: dialogue text is empty")
                continue
            if speaker not in known:
                errors.append(f"{shot_id} line {index}: unknown speaker '{speaker}'")
            elif speaker not in actors:
                errors.append(f"{shot_id} line {index}: speaker '{speaker}' is not staged in this shot")
            words = len(text.split())
            total_words += words
            shot_words += words
            try:
                start = float(line["start_seconds"])
                end = float(line["end_seconds"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{shot_id} line {index}: start_seconds and end_seconds are required")
                continue
            if start < 0 or end <= start or end > duration + 0.001:
                errors.append(f"{shot_id} line {index}: timing {start:.2f}-{end:.2f}s is outside shot duration {duration:.2f}s")
                continue
            timed_words += words
            timed_seconds += end - start
            intervals.setdefault(speaker, []).append((start, end, index))
            rate = words / max(end - start, 0.01)
            if rate > 5.5:
                warnings.append(f"{shot_id} line {index}: fast dialogue pace ({rate:.1f} words/sec)")
            if len(text) > 150:
                warnings.append(f"{shot_id} line {index}: long caption ({len(text)} characters)")
        for speaker, spans in intervals.items():
            spans.sort()
            for previous, current in zip(spans, spans[1:]):
                if current[0] < previous[1] - 0.03:
                    errors.append(
                        f"{shot_id}: lines {previous[2]} and {current[2]} overlap for speaker {known.get(speaker, speaker)}"
                    )
        shot_reports.append({
            "shot_id": shot_id,
            "dialogue_lines": len(lines),
            "word_count": shot_words,
            "staged_speakers": sorted({line.get("speaker") for line in lines if line.get("speaker") in actors}),
            "status": "failed" if any(error.startswith(shot_id) for error in errors) else "review",
        })
        elapsed += duration
    if not total_lines:
        warnings.append("Episode contains no dialogue; this is acceptable for a silent scene but not a dialogue-led episode.")
    report = {
        "schema_version": 1,
        "episode_id": episode.get("id"),
        "dialogue_lines": total_lines,
        "word_count": total_words,
        "timed_word_count": timed_words,
        "shot_count": len(shot_reports),
        "duration_seconds": elapsed,
        "average_words_per_second": round(timed_words / max(timed_seconds, 0.001), 2),
        "status": "failed" if errors else ("passed_with_warnings" if warnings else "passed"),
        "errors": errors,
        "warnings": warnings,
        "shots": shot_reports,
        "creative_review_required": True,
        "note": "Automated checks cover structure and pacing only; they cannot judge humor, natural Algerian dialect, emotional truth or story quality.",
    }
    target = project / "production" / "script_quality_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
