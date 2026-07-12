import cv2
import numpy as np


def apply_overlay(
    frame: np.ndarray,
    face_bboxes: list[tuple[int, int, int, int]],
    face_scores: list[float],
) -> np.ndarray:
    result = frame.copy()

    for (x, y, w, h), score in zip(face_bboxes, face_scores):
        intensity = int(255 * score)
        if score > 0.5:
            color = (0, 0, intensity)
        else:
            color = (intensity, 0, 0)

        overlay = result.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
        result = cv2.addWeighted(result, 0.6, overlay, 0.4, 0)

        label = f"Fake: {score:.2f}" if score > 0.5 else f"Real: {1-score:.2f}"
        text_color = (0, 0, 255) if score > 0.5 else (0, 255, 0)
        cv2.putText(result, label, (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

    if not face_bboxes:
        label = "No face detected"
        cv2.putText(result, label, (12, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)

    return result
