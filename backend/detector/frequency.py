import numpy as np
import cv2
from detector.face_detection import FaceRegion


def _sigmoid(x: float, center: float = 0.5, scale: float = 10.0) -> float:
    return float(1.0 / (1.0 + np.exp(-scale * (x - center))))


def _dct_energy_ratio(face: np.ndarray) -> float:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (224, 224)).astype(np.float32)
    dct = cv2.dct(gray)

    total_energy = float(np.sum(dct ** 2))
    if total_energy < 1e-8:
        return 0.5

    high_energy = float(np.sum(dct[80:, :] ** 2) + np.sum(dct[:80, 80:] ** 2))
    ratio = high_energy / total_energy
    return _sigmoid(ratio, center=0.25, scale=12.0)


def _spectral_flatness(face: np.ndarray) -> float:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (224, 224)).astype(np.float32)
    dct = cv2.dct(gray)

    power = dct ** 2 + 1e-10
    log_mean = float(np.mean(np.log(power)))
    mean_power = float(np.mean(power))
    if mean_power < 1e-10:
        return 0.5

    flatness = np.exp(log_mean) / mean_power
    return _sigmoid(float(flatness), center=0.3, scale=15.0)


def _laplacian_variance(face: np.ndarray) -> float:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (224, 224))

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    var = float(np.var(laplacian))
    normalized = var / 10000.0
    return _sigmoid(normalized, center=0.5, scale=10.0)


def _face_frequency_score(face: np.ndarray) -> float:
    dct_score = _dct_energy_ratio(face)
    flatness_score = _spectral_flatness(face)
    laplacian_score = _laplacian_variance(face)
    return (dct_score + flatness_score + laplacian_score) / 3.0


def _block_dct_score(block: np.ndarray) -> float:
    dct = cv2.dct(block)
    total_energy = float(np.sum(dct ** 2))
    if total_energy < 1e-8:
        return 0.5
    high_energy = float(np.sum(dct[4:, 4:] ** 2))
    ratio = high_energy / total_energy
    return _sigmoid(ratio, center=0.3, scale=12.0)


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
            cell = gray[y0: y0 + 8, x0: x0 + 8]
            heatmap.append(_block_dct_score(cell))
    return heatmap


def run(faces_list: list[list[FaceRegion]]) -> tuple[float, list[float]]:
    scores = []
    for faces in faces_list:
        for face_region in faces:
            scores.append(_face_frequency_score(face_region.crop))
    mean = np.mean(scores) if scores else 0.5
    return float(mean), scores
