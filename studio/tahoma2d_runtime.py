"""Tahoma2D native batch-render adapter."""
from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path

def find_tcomposer(executable=None):
    candidates = [executable] if executable else []
    candidates.extend(["tcomposer", "tcomposer-cli"])
    for candidate in candidates:
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return str(candidate)
    raise FileNotFoundError("Tahoma2D tcomposer was not found on PATH.")

def render_tahoma2d_scene(scene, output, *, executable=None, start_frame=1, end_frame=None, step=1, threads=None, timeout=None):
    scene, output = Path(scene).resolve(), Path(output).resolve()
    if not scene.is_file() or scene.suffix.lower() != ".tnz":
        raise FileNotFoundError(f"Expected an existing native Tahoma2D .tnz scene: {scene}")
    if start_frame < 1 or (end_frame is not None and end_frame < start_frame):
        raise ValueError("Frame range must be 1-based and end_frame >= start_frame")
    if step < 1 or (threads is not None and threads < 1):
        raise ValueError("step and threads must be >= 1")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [find_tcomposer(executable), str(scene), "-o", str(output)]
    if end_frame is not None:
        command.extend(["-range", str(start_frame), str(end_frame)])
    elif start_frame != 1:
        raise ValueError("end_frame is required when start_frame is not 1")
    if step != 1:
        command.extend(["-step", str(step)])
    command.extend(["-multimedia", "1"])
    if threads is not None:
        command.extend(["-nthreads", str(threads)])
    result = subprocess.run(command, capture_output=True, text=True, env=os.environ.copy(), timeout=timeout, check=False)
    log = output.parent / "tahoma2d_render.log"
    log.write_text("COMMAND: " + " ".join(command) + "\n\nSTDOUT:\n" + result.stdout + "\nSTDERR:\n" + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"Tahoma2D render failed ({result.returncode}); see {log}\n{(result.stderr or result.stdout)[-2500:]}")
    if not output.exists():
        raise RuntimeError(f"Tahoma2D did not create requested output {output}; inspect {log}. Output format depends on scene render settings.")
    if output.is_file() and output.stat().st_size < 1024:
        raise RuntimeError(f"Tahoma2D output is unexpectedly small: {output}")
    return output

def tahoma2d_runtime_report(executable=None):
    try:
        binary = find_tcomposer(executable)
    except FileNotFoundError as exc:
        return {"available": False, "renderer": None, "error": str(exc)}
    return {"available": True, "renderer": binary, "engine": "Tahoma2D tcomposer"}
