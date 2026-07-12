import cv2
import numpy as np
import os
import time
from typing import NamedTuple

from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions
from mediapipe.tasks.python.vision.core.image import Image as MpImage, ImageFormat
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

from app.config import settings

_landmarker = None


def _get_landmarker():
    global _landmarker
    if _landmarker is not None:
        return _landmarker
    model_path = os.path.join(settings.WEIGHTS_DIR, "face_landmarker.task")
    base = BaseOptions(model_asset_path=model_path)
    options = FaceLandmarkerOptions(
        base_options=base,
        running_mode=VisionTaskRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    _landmarker = FaceLandmarker.create_from_options(options)
    return _landmarker


class FaceRegion(NamedTuple):
    crop: np.ndarray
    bbox: tuple[int, int, int, int]
    landmarks: np.ndarray


def detect_faces(frame: cv2.Mat) -> list[FaceRegion]:
    landmarker = _get_landmarker()
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = MpImage(image_format=ImageFormat.SRGB, data=rgb)
    timestamp_ms = int(time.time() * 1000)
    result = landmarker.detect_for_video(mp_img, timestamp_ms)

    if not result.face_landmarks:
        return []

    faces = []
    for face_lms in result.face_landmarks:
        points = np.array([[lm.x * w, lm.y * h, lm.z] for lm in face_lms])

        x_min = int(points[:, 0].min())
        y_min = int(points[:, 1].min())
        x_max = int(points[:, 0].max())
        y_max = int(points[:, 1].max())

        pad = 10
        x_min = max(0, x_min - pad)
        y_min = max(0, y_min - pad)
        x_max = min(w, x_max + pad)
        y_max = min(h, y_max + pad)

        crop = frame[y_min:y_max, x_min:x_max]
        if crop.size == 0:
            continue

        faces.append(FaceRegion(
            crop=crop,
            bbox=(x_min, y_min, x_max - x_min, y_max - y_min),
            landmarks=points,
        ))

    return faces
