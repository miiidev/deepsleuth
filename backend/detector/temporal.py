import cv2
import numpy as np

LEFT_EYE = [362, 380, 374, 263, 386, 385]
RIGHT_EYE = [33, 159, 158, 133, 153, 145]

NOSE_TIP = 4
CHIN = 199
LEFT_EYE_CORNER = 33
RIGHT_EYE_CORNER = 263
LEFT_MOUTH = 61
RIGHT_MOUTH = 291

MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0),
], dtype=np.float64)

EAR_THRESHOLD = 0.21
CONSEC_FRAMES = 3
EXPECTED_BLINKS_PER_MINUTE = 17


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


def _estimate_head_pose(landmarks: np.ndarray, image_w: int, image_h: int) -> tuple[float, float, float]:
    indices = [NOSE_TIP, CHIN, LEFT_EYE_CORNER, RIGHT_EYE_CORNER, LEFT_MOUTH, RIGHT_MOUTH]
    image_points = np.array([
        [landmarks[i][0], landmarks[i][1]] for i in indices
    ], dtype=np.float64)

    focal_length = image_w
    center = (image_w / 2, image_h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1],
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))

    success, rvec, tvec = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
    )
    if not success:
        return 0.0, 0.0, 0.0

    rmat, _ = cv2.Rodrigues(rvec)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
    return float(angles[0]), float(angles[1]), float(angles[2])


def _compute_blink_stats(all_landmarks: list[np.ndarray], fps: float) -> dict:
    blink_count = 0
    frame_counter = 0

    for landmarks in all_landmarks:
        if landmarks is None:
            continue
        left_ear = _eye_aspect_ratio(LEFT_EYE, landmarks)
        right_ear = _eye_aspect_ratio(RIGHT_EYE, landmarks)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < EAR_THRESHOLD:
            frame_counter += 1
        else:
            if frame_counter >= CONSEC_FRAMES:
                blink_count += 1
            frame_counter = 0

    duration_minutes = len(all_landmarks) / fps / 60.0 if fps > 0 else 1.0
    if duration_minutes < 1e-6:
        return {"blink_score": 0.5, "blink_count": 0, "blinks_per_min": 0.0}

    actual_rate = blink_count / duration_minutes
    deviation = abs(actual_rate - EXPECTED_BLINKS_PER_MINUTE) / EXPECTED_BLINKS_PER_MINUTE
    return {
        "blink_score": float(np.clip(deviation, 0.0, 1.0)),
        "blink_count": blink_count,
        "blinks_per_min": round(actual_rate, 1),
    }


def _compute_pose_stats(all_landmarks: list[np.ndarray], image_w: int, image_h: int) -> dict:
    yaws, pitches, rolls = [], [], []

    for landmarks in all_landmarks:
        if landmarks is None:
            continue
        yaw, pitch, roll = _estimate_head_pose(landmarks, image_w, image_h)
        yaws.append(yaw)
        pitches.append(pitch)
        rolls.append(roll)

    if len(yaws) < 2:
        return {"pose_score": 0.5, "yaw_var": 0.0, "pitch_var": 0.0, "roll_var": 0.0}

    yaw_var = float(np.var(yaws))
    pitch_var = float(np.var(pitches))
    roll_var = float(np.var(rolls))

    total_var = yaw_var + pitch_var + roll_var
    score = total_var / 50.0
    return {
        "pose_score": float(np.clip(score, 0.0, 1.0)),
        "yaw_var": round(yaw_var, 2),
        "pitch_var": round(pitch_var, 2),
        "roll_var": round(roll_var, 2),
    }


def run(frames: list, all_landmarks: list, fps: float = 30.0) -> dict:
    if not frames or not all_landmarks:
        return {"score": 0.5, "blink_score": 0.5, "pose_score": 0.5,
                "blink_count": 0, "blinks_per_min": 0.0,
                "yaw_var": 0.0, "pitch_var": 0.0, "roll_var": 0.0}

    h, w = frames[0].shape[:2]

    blink = _compute_blink_stats(all_landmarks, fps)
    pose = _compute_pose_stats(all_landmarks, w, h)

    temporal_score = 0.5 * blink["blink_score"] + 0.5 * pose["pose_score"]
    return {
        "score": float(np.clip(temporal_score, 0.0, 1.0)),
        "blink_score": blink["blink_score"],
        "pose_score": pose["pose_score"],
        "blink_count": blink["blink_count"],
        "blinks_per_min": blink["blinks_per_min"],
        "yaw_var": pose["yaw_var"],
        "pitch_var": pose["pitch_var"],
        "roll_var": pose["roll_var"],
    }
