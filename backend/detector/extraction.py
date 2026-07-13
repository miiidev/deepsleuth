import cv2
import numpy as np


def extract_frames(video_path: str, skip: int = 3) -> tuple[list[np.ndarray], float]:
    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or not np.isfinite(fps):
            fps = 30.0

        frames = []
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % skip == 0:
                frames.append(frame)
            idx += 1

        if not frames:
            raise ValueError("No frames could be read from the video file")

        return frames, fps
    finally:
        cap.release()
