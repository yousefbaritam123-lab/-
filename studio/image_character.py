"""Prepare a still image as a reusable 2D character source package.

Optional rembg removes the background; optional MediaPipe estimates pose
landmarks. A flat image is not a production-ready puppet: limb layers, hidden
pixels, pivots and face controls still need manual review and artwork.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def _remove_background(source: Path, destination: Path) -> None:
    try:
        from rembg import remove
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install optional image tools: pip install rembg onnxruntime") from exc
    with Image.open(source) as image:
        remove(image.convert("RGBA")).save(destination, "PNG")

def _pose_landmarks(image_path: Path, segmentation_path: Path | None = None) -> list[dict[str, Any]]:
    try:
        import mediapipe as mp
        import cv2
    except ImportError:
        return []
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pose_api = mp.solutions.pose
    with pose_api.Pose(static_image_mode=True, model_complexity=1,
                       enable_segmentation=True, min_detection_confidence=0.5) as pose:
        result = pose.process(rgb)
    if segmentation_path is not None and result.segmentation_mask is not None:
        import numpy as np
        from PIL import Image
        mask = np.clip(result.segmentation_mask * 255.0, 0, 255).astype("uint8")
        Image.fromarray(mask, mode="L").save(segmentation_path, format="PNG")
    if not result.pose_landmarks:
        return []
    landmarks = result.pose_landmarks.landmark
    return [{"name": item.name.lower(), "x": round(landmarks[item.value].x, 6),
             "y": round(landmarks[item.value].y, 6),
             "visibility": round(landmarks[item.value].visibility, 4)}
            for item in pose_api.PoseLandmark]

def prepare_character_image(source: Path, output_dir: Path, character_id: str) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    if not character_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in character_id):
        raise ValueError("character_id may contain only letters, numbers, '-' and '_'")
    output_dir.mkdir(parents=True, exist_ok=True)
    cutout = output_dir / f"{character_id}_cutout.png"
    _remove_background(source, cutout)
    segmentation_mask = output_dir / f"{character_id}_person_mask.png"
    landmarks = _pose_landmarks(cutout, segmentation_mask)
    manifest = {
        "schema_version": 2, "id": character_id, "source_image": source.name,
        "cutout": cutout.name,
        "segmentation_mask": segmentation_mask.name if segmentation_mask.is_file() else None,
        "coordinate_space": "normalized_image_0_to_1",
        "pose_detector": "mediapipe_pose_with_optional_person_segmentation",
        "pose_landmarks": landmarks,
        "rig_status": "needs_manual_layer_separation_and_rig_review",
        "required_manual_work": [
            "separate head, torso, upper/lower arms, hands, upper/lower legs and feet",
            "paint hidden regions behind joints to prevent gaps during rotation",
            "set pivots, joint limits, hand poses and facial controls",
            "review front/side poses and motion tests before episode use"
        ]
    }
    target = output_dir / f"{character_id}.character-image.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
