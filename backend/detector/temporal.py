import cv2
import numpy as np

LEFT_EYE = [33, 160, 158, 133, 153, 145]
RIGHT_EYE = [362, 385, 387, 263, 380, 374]

EAR_THRESHOLD = 0.21
BLINK_MIN_DURATION_SEC = 0.05
BLINK_MAX_DURATION_SEC = 0.5
EXPECTED_BLINKS_PER_MINUTE = 17

DCT_SIZE = 224
HIGH_FREQ_CUTOFF = 32


def _eye_aspect_ratio(eye_indices: list[int], landmarks: np.ndarray) -> float:
    p1 = landmarks[eye_indices[0]][:2]
    p2 = landmarks[eye_indices[1]][:2]
    p3 = landmarks[eye_indices[2]][:2]
    p4 = landmarks[eye_indices[3]][:2]
    p5 = landmarks[eye_indices[4]][:2]
    p6 = landmarks[eye_indices[5]][:2]

    A = np.linalg.norm(p2 - p6)
    B = np.linalg.norm(p3 - p5)
    C = np.linalg.norm(p1 - p4)

    if C < 1e-6:
        return 0.3
    return float((A + B) / (2.0 * C))


def _compute_blink_stats(all_landmarks: list, fps: float, skip: int) -> dict:
    blink_count = 0
    eyes_closed = False
    closed_start_time = 0.0
    valid_frames = 0

    time_per_frame = skip / fps if fps > 0 else 1.0 / 30.0

    for i, landmarks in enumerate(all_landmarks):
        t = i * time_per_frame
        if landmarks is None:
            if eyes_closed:
                eyes_closed = False
            continue

        valid_frames += 1
        left_ear = _eye_aspect_ratio(LEFT_EYE, landmarks)
        right_ear = _eye_aspect_ratio(RIGHT_EYE, landmarks)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < EAR_THRESHOLD:
            if not eyes_closed:
                eyes_closed = True
                closed_start_time = t
        else:
            if eyes_closed:
                duration = t - closed_start_time
                if BLINK_MIN_DURATION_SEC <= duration <= BLINK_MAX_DURATION_SEC:
                    blink_count += 1
                eyes_closed = False

    valid_duration_sec = valid_frames * time_per_frame
    if valid_duration_sec < 2.0:
        return {"blink_score": 0.5, "blink_count": 0, "blinks_per_min": 0.0}

    duration_minutes = valid_duration_sec / 60.0
    actual_rate = blink_count / duration_minutes
    deviation = abs(actual_rate - EXPECTED_BLINKS_PER_MINUTE) / EXPECTED_BLINKS_PER_MINUTE
    return {
        "blink_score": float(np.clip(deviation, 0.0, 1.0)),
        "blink_count": blink_count,
        "blinks_per_min": round(actual_rate, 1),
    }


def _extract_face_region(frame: np.ndarray, landmarks: np.ndarray) -> np.ndarray | None:
    h, w = frame.shape[:2]
    x_min = int(landmarks[:, 0].min())
    y_min = int(landmarks[:, 1].min())
    x_max = int(landmarks[:, 0].max())
    y_max = int(landmarks[:, 1].max())

    pad = 10
    x_min = max(0, x_min - pad)
    y_min = max(0, y_min - pad)
    x_max = min(w, x_max + pad)
    y_max = min(h, y_max + pad)

    crop = frame[y_min:y_max, x_min:x_max]
    if crop.size == 0:
        return None
    return crop


def _dct_high_freq_vector(face: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (DCT_SIZE, DCT_SIZE)).astype(np.float32)
    dct = cv2.dct(gray)
    return dct[HIGH_FREQ_CUTOFF:, HIGH_FREQ_CUTOFF:].flatten()


def _compute_flickering(frames: list, all_landmarks: list, skip: int, fps: float) -> float:
    vectors = []

    for i, (frame, landmarks) in enumerate(zip(frames, all_landmarks)):
        if landmarks is None:
            continue
        face = _extract_face_region(frame, landmarks)
        if face is None:
            continue
        vec = _dct_high_freq_vector(face)
        if vec is not None:
            vectors.append(vec)

    if len(vectors) < 3:
        return 0.5

    vectors = np.array(vectors)
    coeff_var = np.var(vectors, axis=0)
    mean_var = float(np.mean(coeff_var))

    score = np.clip(mean_var / 1500.0, 0.0, 1.0)
    return float(score)


def _compute_landmark_stability(all_landmarks: list) -> float:
    valid = [lm for lm in all_landmarks if lm is not None]
    if len(valid) < 3:
        return 0.5

    centered = []
    for lm in valid:
        centroid = lm[:, :2].mean(axis=0)
        centered.append(lm[:, :2] - centroid)

    centered = np.array(centered)
    x_var = np.var(centered[:, :, 0])
    y_var = np.var(centered[:, :, 1])
    total_var = float(x_var + y_var)

    score = np.clip(total_var / 200.0, 0.0, 1.0)
    return float(score)


def run(frames: list, all_landmarks: list, fps: float = 30.0, skip: int = 3) -> dict:
    if not frames or not all_landmarks:
        return {"score": 0.5, "blink_score": 0.5, "blink_count": 0,
                "blinks_per_min": 0.0, "flickering_score": 0.5,
                "landmark_stability": 0.5}

    blink = _compute_blink_stats(all_landmarks, fps, skip)
    flickering = _compute_flickering(frames, all_landmarks, skip, fps)
    stability = _compute_landmark_stability(all_landmarks)

    temporal_score = (
        0.35 * blink["blink_score"]
        + 0.40 * flickering
        + 0.25 * stability
    )
    return {
        "score": float(np.clip(temporal_score, 0.0, 1.0)),
        "blink_score": blink["blink_score"],
        "blink_count": blink["blink_count"],
        "blinks_per_min": blink["blinks_per_min"],
        "flickering_score": flickering,
        "landmark_stability": stability,
    }
