"""Tahoma2D native batch-render adapter with portable profile discovery."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def find_tcomposer(executable=None):
    candidates = [executable] if executable else []
    candidates.extend(["tcomposer", "tcomposer-cli"])
    for candidate in candidates:
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return str(candidate)
    raise FileNotFoundError("Tahoma2D tcomposer was not found on PATH.")


def _tahoma_environment(executable: str) -> dict[str, str]:
    """Resolve the adjacent Tahoma stuff directory used by official installs."""
    env = os.environ.copy()
    resolved = shutil.which(executable) or executable
    try:
        binary = Path(resolved).resolve()
    except (OSError, RuntimeError):
        return env

    roots = [parent / "tahomastuff" for parent in binary.parents]
    stuff = next((candidate for candidate in roots if candidate.is_dir()), None)
    if stuff is None:
        # Some packaged layouts keep the data directory beside the application bundle.
        roots = [parent / "stuff" for parent in binary.parents]
        stuff = next((candidate for candidate in roots if candidate.is_dir()), None)
    if stuff is None:
        return env

    folders = {
        "TAHOMA2DROOT": stuff,
        "TAHOMA2DCONFIG": stuff / "config",
        "TAHOMA2DFXPRESETS": stuff / "fxs",
        "TAHOMA2DLIBRARY": stuff / "library",
        "TAHOMA2DPROFILES": stuff / "profiles",
        "TAHOMA2DPROJECTS": stuff / "projects",
        "TAHOMA2DSTUDIOPALETTE": stuff / "studiopalette",
        "TAHOMA2DCACHEROOT": stuff / "cache",
    }
    for key, path in folders.items():
        env.setdefault(key, str(path))

    # Linux packages rely on SystemVar.ini to locate the shared Tahoma stuff tree.
    # Preserve any existing user configuration; create only when it is absent.
    if os.name == "posix":
        config_home = Path(env.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        system_var = config_home / "Tahoma2D" / "SystemVar.ini"
        if not system_var.exists():
            system_var.parent.mkdir(parents=True, exist_ok=True)
            keys = (
                "TAHOMA2DROOT", "TAHOMA2DPROFILES", "TAHOMA2DCONFIG",
                "TAHOMA2DFXPRESETS", "TAHOMA2DLIBRARY", "TAHOMA2DPROJECTS",
                "TAHOMA2DSTUDIOPALETTE", "TAHOMA2DCACHEROOT",
            )
            lines = ["[General]"] + [
                f'{key}="{env[key]}"' for key in keys if env.get(key)
            ]
            system_var.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    return env


def render_tahoma2d_scene(scene, output, *, executable=None, start_frame=1,
                          end_frame=None, step=1, threads=None, timeout=None):
    scene, output = Path(scene).resolve(), Path(output).resolve()
    if not scene.is_file() or scene.suffix.lower() != ".tnz":
        raise FileNotFoundError(f"Expected an existing native Tahoma2D .tnz scene: {scene}")
    if start_frame < 1 or (end_frame is not None and end_frame < start_frame):
        raise ValueError("Frame range must be 1-based and end_frame >= start_frame")
    if step < 1 or (threads is not None and threads < 1):
        raise ValueError("step and threads must be >= 1")
    binary = find_tcomposer(executable)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [binary, str(scene), "-o", str(output)]
    if end_frame is not None:
        command.extend(["-range", str(start_frame), str(end_frame)])
    elif start_frame != 1:
        raise ValueError("end_frame is required when start_frame is not 1")
    if step != 1:
        command.extend(["-step", str(step)])
    command.extend(["-multimedia", "1"])
    if threads is not None:
        command.extend(["-nthreads", str(threads)])
    result = subprocess.run(
        command, capture_output=True, text=True,
        env=_tahoma_environment(binary), timeout=timeout, check=False,
    )
    log = output.parent / "tahoma2d_render.log"
    log.write_text(
        "COMMAND: " + " ".join(command) + "\n\nSTDOUT:\n" +
        result.stdout + "\nSTDERR:\n" + result.stderr,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Tahoma2D render failed ({result.returncode}); see {log}\n"
            f"{(result.stderr or result.stdout)[-2500:]}"
        )
    if not output.exists():
        raise RuntimeError(
            f"Tahoma2D did not create requested output {output}; inspect {log}. "
            "Output format depends on scene render settings."
        )
    if output.is_file() and output.stat().st_size < 1024:
        raise RuntimeError(f"Tahoma2D output is unexpectedly small: {output}")
    return output


def tahoma2d_runtime_report(executable=None):
    try:
        binary = find_tcomposer(executable)
    except FileNotFoundError as exc:
        return {"available": False, "renderer": None, "error": str(exc)}
    env = _tahoma_environment(binary)
    return {
        "available": True,
        "renderer": binary,
        "engine": "Tahoma2D tcomposer",
        "profile_root": env.get("TAHOMA2DROOT"),
    }
