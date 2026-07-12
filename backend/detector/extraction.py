import cv2
import numpy as np


def extract_frames(video_path: str, skip: int = 3) -> list[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % skip == 0:
            frames.append(frame)
        idx += 1
    cap.release()
    return frames
