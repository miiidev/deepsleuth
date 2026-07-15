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

FAKE_SOURCES = [
    "Deepfakes",
    "Face2Face",
    "FaceSwap",
    "NeuralTextures",
]

TARGET_SIZE = 299

QUALITY_LEVELS = ["c23"]


def find_quality_dirs():
    available = []
    for q in QUALITY_LEVELS:
        real_dir = DATA_RAW / "original_sequences" / "youtube" / q / "videos"
        if real_dir.exists():
            available.append(q)
    return available


def process_videos(video_dir: Path, label: str, quality: str, method: str = "real", limit: int = 0):
    out_dir = DATA_OUT / label
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(video_dir.glob("*.mp4"))
    if limit:
        videos = videos[:limit]

    count = 0
    for vpath in videos:
        stem = vpath.stem
        frames, fps = extract_frames(str(vpath), skip=SKIP_FRAME)
        for i, frame in enumerate(frames):
            faces = detect_faces(frame)
            if not faces:
                continue
            face = faces[0].crop
            face = cv2.resize(face, (TARGET_SIZE, TARGET_SIZE))
            fname = f"{quality}_{method}_{stem}_f{i}.jpg"
            cv2.imwrite(str(out_dir / fname), face)
            count += 1

        if (count + 1) % 500 == 0:
            print(f"  [{label}] {count} crops so far...")

    print(f"  [{label}] Done — {count} crops from {len(videos)} videos")
    return count


def main():
    available = find_quality_dirs()
    if not available:
        print("No quality directories found under data/raw/")
        print("Expected: data/raw/original_sequences/youtube/c40/videos/")
        sys.exit(1)

    print("=== Preprocessing FaceForensics++ ===")
    print(f"Quality levels: {', '.join(available)}")
    print()

    total_real = 0
    total_fake = 0

    for quality in available:
        print(f"--- Quality: {quality} ---")
        print()

        real_dir = DATA_RAW / "original_sequences" / "youtube" / quality / "videos"
        print(f"Processing REAL videos ({quality})...")
        real_count = process_videos(real_dir, "real", quality, method="real")
        total_real += real_count

        print()
        for src in FAKE_SOURCES:
            fake_dir = DATA_RAW / "manipulated_sequences" / src / quality / "videos"
            if not fake_dir.exists():
                print(f"  Skipping {src}/{quality} (not found)")
                continue
            print(f"Processing FAKE ({src}/{quality})...")
            cnt = process_videos(fake_dir, "fake", quality, method=src)
            total_fake += cnt

        print()

    print(f"Total real crops: {total_real}")
    print(f"Total fake crops: {total_fake}")
    print(f"Grand total:      {total_real + total_fake}")


if __name__ == "__main__":
    main()
