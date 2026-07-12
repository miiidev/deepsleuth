import cv2
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from detector.face_detection import detect_faces
from detector.extraction import extract_frames

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_OUT = BASE_DIR / "data" / "processed" / "images"
SKIP_FRAME = 30

REAL_VIDEOS = DATA_RAW / "original_sequences" / "youtube" / "c40" / "videos"

FAKE_SOURCES = [
    "Deepfakes",
    "Face2Face",
    "FaceSwap",
    "NeuralTextures",
]

TARGET_SIZE = 299


def process_videos(video_dir: Path, label: str, limit: int = 0):
    out_dir = DATA_OUT / label
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(video_dir.glob("*.mp4"))
    if limit:
        videos = videos[:limit]

    count = 0
    for vpath in videos:
        stem = vpath.stem
        frames = extract_frames(str(vpath), skip=SKIP_FRAME)
        for i, frame in enumerate(frames):
            faces = detect_faces(frame)
            if not faces:
                continue
            face = faces[0]
            face = cv2.resize(face, (TARGET_SIZE, TARGET_SIZE))
            fname = f"{stem}_f{i}.jpg"
            cv2.imwrite(str(out_dir / fname), face)
            count += 1

        if (count + 1) % 500 == 0:
            print(f"  [{label}] {count} crops so far...")

    print(f"  [{label}] Done — {count} crops from {len(videos)} videos")
    return count


def main():
    print("=== Preprocessing FaceForensics++ ===")
    print()

    print("Processing REAL videos...")
    real_count = process_videos(REAL_VIDEOS, "real")

    print()
    total_fake = 0
    for src in FAKE_SOURCES:
        fake_dir = DATA_RAW / "manipulated_sequences" / src / "c40" / "videos"
        print(f"Processing FAKE ({src})...")
        cnt = process_videos(fake_dir, "fake")
        total_fake += cnt

    print()
    print(f"Total real crops: {real_count}")
    print(f"Total fake crops: {total_fake}")
    print(f"Grand total:      {real_count + total_fake}")


if __name__ == "__main__":
    main()
