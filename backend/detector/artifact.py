import numpy as np
import cv2
from detector.face_detection import FaceRegion

EYES = np.array([
    33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246,
    362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398,
])
FOREHEAD = np.array([
    10, 151, 9, 8, 107, 66, 105, 63, 70, 336, 296, 334, 293, 300, 285, 282, 283, 276,
])
CHEEKS = np.array([
    36, 205, 206, 207, 187, 123, 116, 117, 118, 119, 100,
    266, 425, 426, 427, 411, 352, 345, 346, 347, 348, 329,
])
JAWLINE = np.array([
    152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
])


def _sigmoid(x: float, center: float = 0.5, scale: float = 10.0) -> float:
    return float(1.0 / (1.0 + np.exp(-scale * (x - center))))


def _region_mask(shape, landmarks_crop, indices):
    valid = indices[indices < len(landmarks_crop)]
    if len(valid) < 3:
        return None
    pts = landmarks_crop[valid, :2].astype(np.int32)
    mask = np.zeros(shape, dtype=np.uint8)
    hull = cv2.convexHull(pts)
    cv2.fillConvexPoly(mask, hull, 255)
    return mask


def _region_texture_var(gray, landmarks_crop, indices):
    mask = _region_mask(gray.shape, landmarks_crop, indices)
    if mask is None:
        return None
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    pix = mask > 0
    if pix.sum() < 10:
        return None
    return float(np.var(lap[pix]))


def _texture_incongruence(gray, landmarks_crop):
    cheek_var = _region_texture_var(gray, landmarks_crop, CHEEKS)
    forehead_var = _region_texture_var(gray, landmarks_crop, FOREHEAD)

    if cheek_var is None or forehead_var is None:
        return 0.5

    mx = max(cheek_var, forehead_var)
    if mx < 1e-8:
        return 0.5

    ratio = min(cheek_var, forehead_var) / mx
    return _sigmoid(1.0 - ratio, center=0.3, scale=8.0)


def _boundary_gradient_score(gray, landmarks_crop):
    jaw_mask = _region_mask(gray.shape, landmarks_crop, JAWLINE)
    if jaw_mask is None:
        return 0.5

    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobelx ** 2 + sobely ** 2)

    boundary = cv2.dilate(jaw_mask, np.ones((3, 3), np.uint8), iterations=1)
    boundary = boundary & ~cv2.erode(jaw_mask, np.ones((3, 3), np.uint8), iterations=1)
    pix = boundary > 0
    if pix.sum() < 10:
        return 0.5

    boundary_mag = magnitude[pix]
    all_mag = magnitude[magnitude > 0]
    if len(all_mag) == 0:
        return 0.5

    p90 = np.percentile(all_mag, 90)
    high_ratio = float(np.mean(boundary_mag > p90))
    return _sigmoid(high_ratio, center=0.15, scale=12.0)


def _specular_highlight_score(gray, landmarks_crop):
    eye_mask = _region_mask(gray.shape, landmarks_crop, EYES)
    if eye_mask is None:
        return 0.5

    region_pix = gray[eye_mask > 0]
    if len(region_pix) < 10:
        return 0.5

    bright_thresh = np.percentile(region_pix, 95)
    bright_mask = (gray > bright_thresh) & (eye_mask > 0)
    bright_count = int(bright_mask.sum())
    total_count = int(eye_mask.sum())

    if bright_count < 5:
        return 0.3

    highlight_ratio = bright_count / total_count
    highlight_intensity = float(np.mean(gray[bright_mask])) / 255.0

    size_score = _sigmoid(highlight_ratio, center=0.05, scale=20.0)
    intensity_score = _sigmoid(highlight_intensity, center=0.8, scale=10.0)
    return 0.5 * size_score + 0.5 * intensity_score


def _noise_consistency_score(gray):
    blurred = cv2.GaussianBlur(gray, (21, 21), 5.0)
    residual = gray.astype(np.float64) - blurred.astype(np.float64)

    block_size = 16
    h, w = gray.shape
    rows = h // block_size
    cols = w // block_size

    block_vars = []
    for gy in range(rows):
        for gx in range(cols):
            y0 = gy * block_size
            x0 = gx * block_size
            block = residual[y0:y0 + block_size, x0:x0 + block_size]
            block_vars.append(float(np.var(block)))

    if not block_vars:
        return 0.5

    arr = np.array(block_vars)
    mean_v = float(np.mean(arr))
    std_v = float(np.std(arr))

    if mean_v < 1e-8:
        return 0.5

    cv = std_v / mean_v
    return _sigmoid(cv, center=0.5, scale=8.0)


def _artifact_score(face_region: FaceRegion) -> float:
    gray = cv2.cvtColor(face_region.crop, cv2.COLOR_BGR2GRAY)

    lm = face_region.landmarks.copy()
    lm[:, 0] -= face_region.bbox[0]
    lm[:, 1] -= face_region.bbox[1]

    texture = _texture_incongruence(gray, lm)
    boundary = _boundary_gradient_score(gray, lm)
    highlight = _specular_highlight_score(gray, lm)
    noise = _noise_consistency_score(gray)

    boundary_total = 0.6 * boundary + 0.4 * highlight
    return 0.40 * texture + 0.35 * boundary_total + 0.25 * noise


def run(faces_list: list[list[FaceRegion]]) -> tuple[float, list[float]]:
    scores = []
    for faces in faces_list:
        for face_region in faces:
            scores.append(_artifact_score(face_region))
    mean = np.mean(scores) if scores else 0.5
    return float(mean), scores
