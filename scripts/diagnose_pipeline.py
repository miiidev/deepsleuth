import sys
import time
import numpy as np
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from detector import face_detection, spatial_cnn, artifact, temporal, fusion, extraction
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed" / "images"


def print_section(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def diagnose_video(video_path: str):
    print_section("VIDEO INFO")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ERROR: Cannot open {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    cap.release()

    print(f"  Path:      {video_path}")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS:       {fps:.1f}")
    print(f"  Frames:    {total_frames}")
    print(f"  Duration:  {duration:.1f}s")

    print_section("STEP 1: FRAME EXTRACTION")
    t0 = time.time()
    frames, fps = extraction.extract_frames(video_path, skip=1)
    print(f"  Extracted {len(frames)} frames in {time.time()-t0:.1f}s")

    print_section("STEP 2: FACE DETECTION")
    t0 = time.time()
    all_landmarks = []
    cnn_face_crops = []
    frame_face_counts = []
    crop_sizes = []

    for i, frame in enumerate(frames):
        faces = face_detection.detect_faces(frame)
        frame_face_counts.append(len(faces))
        if faces:
            all_landmarks.append(faces[0].landmarks)
            if i % settings.SKIP_FRAME == 0:
                for f in faces:
                    h, w = f.crop.shape[:2]
                    crop_sizes.append((w, h))
                cnn_face_crops.append(faces)
        else:
            all_landmarks.append(None)

    elapsed = time.time() - t0
    frames_with_faces = sum(1 for c in frame_face_counts if c > 0)
    total_crops = sum(len(c) for c in cnn_face_crops)

    print(f"  Time: {elapsed:.1f}s")
    print(f"  Frames with faces: {frames_with_faces}/{len(frames)} ({frames_with_faces/len(frames)*100:.0f}%)")
    print(f"  Face crops for CNN: {total_crops} (every {settings.SKIP_FRAME} frames)")

    if crop_sizes:
        widths = [s[0] for s in crop_sizes]
        heights = [s[1] for s in crop_sizes]
        print(f"  Crop size range: [{min(widths)}x{min(heights)}] to [{max(widths)}x{max(heights)}]")
        print(f"  Crop size mean:  {np.mean(widths):.0f}x{np.mean(heights):.0f}")

    if frames_with_faces == 0:
        print("  WARNING: No faces detected in any frame!")
        print("  This video may not contain a detectable face.")

    print_section("STEP 3: SPATIAL CNN")
    t0 = time.time()
    all_faces_flat = [f for faces in cnn_face_crops for f in faces]

    if all_faces_flat:
        spatial_score, per_face_scores, _, per_face_regions = spatial_cnn.run(all_faces_flat)
    else:
        spatial_score = 0.5
        per_face_scores = []

    elapsed = time.time() - t0
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Spatial score: {spatial_score:.4f}")

    if per_face_scores:
        scores_arr = np.array(per_face_scores)
        print(f"  Per-face fake_prob stats:")
        print(f"    Mean:   {scores_arr.mean():.4f}")
        print(f"    Median: {np.median(scores_arr):.4f}")
        print(f"    Std:    {scores_arr.std():.4f}")
        print(f"    Min:    {scores_arr.min():.4f}")
        print(f"    Max:    {scores_arr.max():.4f}")
        print(f"    >0.5:   {(scores_arr > 0.5).sum()}/{len(scores_arr)} ({(scores_arr > 0.5).mean()*100:.0f}%)")
        print(f"    >0.7:   {(scores_arr > 0.7).sum()}/{len(scores_arr)} ({(scores_arr > 0.7).mean()*100:.0f}%)")
        print(f"    >0.9:   {(scores_arr > 0.9).sum()}/{len(scores_arr)} ({(scores_arr > 0.9).mean()*100:.0f}%)")

        buckets = [0, 0, 0, 0, 0]
        for s in per_face_scores:
            if s < 0.2: buckets[0] += 1
            elif s < 0.4: buckets[1] += 1
            elif s < 0.6: buckets[2] += 1
            elif s < 0.8: buckets[3] += 1
            else: buckets[4] += 1
        labels = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
        max_bar = max(buckets) if max(buckets) > 0 else 1
        print(f"    Distribution:")
        for lbl, cnt in zip(labels, buckets):
            bar = "#" * int(cnt / max_bar * 30)
            print(f"      {lbl}: {cnt:4d} {bar}")
    else:
        print("  No face scores computed (no faces detected)")

    print_section("STEP 4: ARTIFACT ANALYSIS")
    t0 = time.time()
    artifact_score, per_face_artifact = artifact.run(cnn_face_crops)
    elapsed = time.time() - t0
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Artifact score: {artifact_score:.4f}")
    if per_face_artifact:
        art_arr = np.array(per_face_artifact)
        print(f"  Per-face artifact stats: mean={art_arr.mean():.4f} std={art_arr.std():.4f} "
              f"min={art_arr.min():.4f} max={art_arr.max():.4f}")

    print_section("STEP 5: TEMPORAL ANALYSIS")
    t0 = time.time()
    temporal_data = temporal.run(frames, all_landmarks, fps=fps, skip=1)
    elapsed = time.time() - t0
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Temporal score: {temporal_data['score']:.4f}")
    print(f"  Blink count:    {temporal_data['blink_count']} ({temporal_data['blinks_per_min']:.1f}/min)")
    print(f"  Blink score:    {temporal_data['blink_score']:.4f}")
    print(f"  Flickering:     {temporal_data['flickering_score']:.4f}")
    print(f"  Landmark stab:  {temporal_data['landmark_stability']:.4f}")

    print_section("STEP 6: SCORE FUSION")
    t0 = time.time()
    result = fusion.fuse(spatial_score, artifact_score, temporal_data)
    elapsed = time.time() - t0

    print(f"  Time: {elapsed:.1f}s")
    print(f"  +{'-'*48}+")
    print(f"  | Spatial:   {result['spatial_score']:.4f}  (weight: 0.55)  = {result['spatial_score']*0.55:.4f} |")
    print(f"  | Artifact:  {result['artifact_score']:.4f}  (weight: 0.15)  = {result['artifact_score']*0.15:.4f} |")
    print(f"  | Temporal:  {result['temporal_score']:.4f}  (weight: 0.35)  = {result['temporal_score']*0.35:.4f} |")
    print(f"  +{'-'*48}+")
    print(f"  | FUSED:     {result['fused_score']:.4f}                         |")
    print(f"  | Level:     {result['suspicion_level']:10s}                   |")
    print(f"  +{'-'*48}+")
    print(f"\n  Summary: {result['summary']}")

    print_section("DIAGNOSIS")
    issues = []
    if frames_with_faces < len(frames) * 0.5:
        issues.append(f"Face detection failed on {len(frames)-frames_with_faces}/{len(frames)} frames")
    if crop_sizes:
        avg_w = np.mean([s[0] for s in crop_sizes])
        if avg_w < 80:
            issues.append(f"Face crops are very small (avg {avg_w:.0f}px) — model may struggle")
    if per_face_scores:
        if spatial_score < 0.3:
            issues.append("Spatial score is LOW — CNN thinks faces are mostly REAL")
            if np.mean(per_face_scores) > 0.5:
                issues.append("  BUT per-face mean > 0.5 — possible aggregation issue")
        elif spatial_score < 0.5:
            issues.append("Spatial score is BORDERLINE — CNN is uncertain")
    if artifact_score < 0.2:
        issues.append("Artifact score is very low — signal may not be discriminating")
    if temporal_data["blink_count"] == 0:
        issues.append("No blinks detected — temporal blink signal is dead")
    if temporal_data["flickering_score"] < 0.2:
        issues.append("Flickering score is very low — may indicate stable (good) deepfake")

    if issues:
        for issue in issues:
            print(f"  [!] {issue}")
    else:
        print(f"  [OK] No obvious issues detected")

    return result


def compare_with_training_data():
    print_section("COMPARISON: PIPELINE vs TRAINING DATA")
    train_dir = DATA_PROCESSED / "fake"
    if not train_dir.exists():
        print("  No training data found at", train_dir)
        return

    all_crops = []
    for method_dir in train_dir.iterdir():
        if method_dir.is_dir():
            for f in list(method_dir.glob("*.jpg"))[:50]:
                img = cv2.imread(str(f))
                if img is not None:
                    all_crops.append({"path": str(f), "method": method_dir.name, "img": img})

    if not all_crops:
        print("  No training images found")
        return

    sizes = [(c["img"].shape[1], c["img"].shape[0]) for c in all_crops]
    brightness = [c["img"].mean() for c in all_crops]
    sharpness = [cv2.Laplacian(cv2.cvtColor(c["img"], cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() for c in all_crops]

    print(f"  Training data stats ({len(all_crops)} samples):")
    print(f"    Size:      {np.mean([s[0] for s in sizes]):.0f}x{np.mean([s[1] for s in sizes]):.0f} "
          f"(all {sizes[0][0]}x{sizes[0][1]} after resize)")
    print(f"    Brightness: {np.mean(brightness):.1f} ± {np.std(brightness):.1f}")
    print(f"    Sharpness:  {np.mean(sharpness):.1f} ± {np.std(sharpness):.1f}")
    print(f"    By method:")
    for method in ["Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures"]:
        method_crops = [c for c in all_crops if c["method"] == method]
        if method_crops:
            method_sharp = [cv2.Laplacian(cv2.cvtColor(c["img"], cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
                           for c in method_crops]
            print(f"      {method:15s}: {len(method_crops):4d} crops, sharpness={np.mean(method_sharp):.1f}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_pipeline.py <video_path>")
        print("       python diagnose_pipeline.py --compare")
        sys.exit(1)

    if sys.argv[1] == "--compare":
        compare_with_training_data()
        return

    video_path = sys.argv[1]
    if not Path(video_path).exists():
        print(f"File not found: {video_path}")
        sys.exit(1)

    diagnose_video(video_path)


if __name__ == "__main__":
    main()
