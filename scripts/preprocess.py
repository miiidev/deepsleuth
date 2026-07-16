import cv2
import os
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

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


def _process_single_video(args):
    vpath, out_dir, quality, stem = args
    from detector.face_detection import detect_faces

    frames, fps = extract_frames(str(vpath), skip=SKIP_FRAME)
    count = 0
    for i, frame in enumerate(frames):
        faces = detect_faces(frame)
        if not faces:
            continue
        face = faces[0].crop
        face = cv2.resize(face, (TARGET_SIZE, TARGET_SIZE))
        fname = f"{quality}_{stem}_f{i}.jpg"
        cv2.imwrite(str(out_dir / fname), face)
        count += 1

    return count


def process_videos(video_dir: Path, label: str, quality: str, method: str = "",
                   limit: int = 0, workers: int = 1):
    if method:
        out_dir = DATA_OUT / label / method
    else:
        out_dir = DATA_OUT / label
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(video_dir.glob("*.mp4"))
    if limit:
        videos = videos[:limit]

    tasks = [(v, out_dir, quality, v.stem) for v in videos]

    count = 0
    t0 = time.time()

    if workers <= 1:
        for task in tasks:
            count += _process_single_video(task)
            elapsed = time.time() - t0
            rate = count / elapsed if elapsed > 0 else 0
            print(f"\r  [{label}/{method or 'all'}] {count} crops ({rate:.0f}/s)", end="", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process_single_video, t): t for t in tasks}
            done = 0
            for future in as_completed(futures):
                try:
                    c = future.result()
                    count += c
                except Exception as e:
                    vpath = futures[future][0]
                    print(f"\n  ERROR processing {vpath.name}: {e}")
                done += 1
                elapsed = time.time() - t0
                rate = count / elapsed if elapsed > 0 else 0
                print(f"\r  [{label}/{method or 'all'}] {done}/{len(tasks)} videos, {count} crops ({rate:.0f}/s)   ",
                      end="", flush=True)

    elapsed = time.time() - t0
    tag = f"{label}/{method}" if method else label
    print(f"\n  [{tag}] Done — {count} crops from {len(videos)} videos in {elapsed:.1f}s")
    return count


def find_quality_dirs():
    available = []
    for q in QUALITY_LEVELS:
        real_dir = DATA_RAW / "original_sequences" / "youtube" / q / "videos"
        if real_dir.exists():
            available.append(q)
    return available


def main():
    parser = argparse.ArgumentParser(description="Preprocess FaceForensics++ videos")
    parser.add_argument("-j", "--workers", type=int, default=4,
                        help="Number of parallel workers (default: 4)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit videos per source (0 = all)")
    args = parser.parse_args()

    available = find_quality_dirs()
    if not available:
        print("No quality directories found under data/raw/")
        print("Expected: data/raw/original_sequences/youtube/c23/videos/")
        sys.exit(1)

    print("=== Preprocessing FaceForensics++ ===")
    print(f"Quality levels: {', '.join(available)}")
    print(f"Workers: {args.workers}")
    print()

    total_real = 0
    total_fake = 0

    for quality in available:
        print(f"--- Quality: {quality} ---")
        print()

        real_dir = DATA_RAW / "original_sequences" / "youtube" / quality / "videos"
        print(f"Processing REAL videos ({quality})...")
        real_count = process_videos(real_dir, "real", quality, workers=args.workers, limit=args.limit)
        total_real += real_count

        print()
        for src in FAKE_SOURCES:
            fake_dir = DATA_RAW / "manipulated_sequences" / src / quality / "videos"
            if not fake_dir.exists():
                print(f"  Skipping {src}/{quality} (not found)")
                continue
            print(f"Processing FAKE ({src}/{quality})...")
            cnt = process_videos(fake_dir, "fake", quality, method=src,
                                 workers=args.workers, limit=args.limit)
            total_fake += cnt

        print()

    print(f"Total real crops: {total_real}")
    print(f"Total fake crops: {total_fake}")
    print(f"Grand total:      {total_real + total_fake}")


if __name__ == "__main__":
    main()
