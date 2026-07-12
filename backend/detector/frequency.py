import numpy as np
import cv2
from detector.face_detection import FaceRegion


def _dct_anomaly_score(face: np.ndarray) -> float:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, (224, 224))
    gray = gray.astype(np.float32)

    dct = cv2.dct(gray)
    high_freq = dct[16:, 16:]
    energy = np.mean(np.abs(high_freq))
    total = np.mean(np.abs(dct))
    if total < 1e-8:
        return 0.5
    score = energy / total
    score = np.clip(score / 0.3, 0.0, 1.0)
    return float(score)


def _block_dct_score(block: np.ndarray) -> float:
    dct = cv2.dct(block)
    high_freq = dct[4:, 4:]
    energy = float(np.mean(np.abs(high_freq)))
    total = float(np.mean(np.abs(dct)))
    if total < 1e-8:
        return 0.5
    score = energy / total
    return float(np.clip(score / 0.3, 0.0, 1.0))


def run_block_heatmap(face: np.ndarray, grid_size: int = 28) -> list[float]:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
    size = grid_size * 8
    gray = cv2.resize(gray, (size, size))
    gray = gray.astype(np.float32)

    heatmap = []
    for gy in range(grid_size):
        for gx in range(grid_size):
            y0 = gy * 8
            x0 = gx * 8
            cell = gray[y0 : y0 + 8, x0 : x0 + 8]
            heatmap.append(_block_dct_score(cell))
    return heatmap


def run(faces_list: list[list[FaceRegion]]) -> tuple[float, list[float]]:
    scores = []
    for faces in faces_list:
        for face_region in faces:
            scores.append(_dct_anomaly_score(face_region.crop))
    mean = np.mean(scores) if scores else 0.5
    return float(mean), scores
