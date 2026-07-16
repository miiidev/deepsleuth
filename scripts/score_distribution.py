import sys
import json
import time
import random
import argparse
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from detector import face_detection, spatial_cnn, artifact, temporal, fusion
from detector.extraction import extract_frames

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
SPLITS_DIR = BASE_DIR / "data" / "splits"

MANIPULATION_METHODS = ["Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures"]
QUALITY = "c23"
SKIP_FRAME = 3


def find_videos(samples_per_method=0):
    by_method = {"real": []}
    for m in MANIPULATION_METHODS:
        by_method[m] = []

    real_dir = DATA_RAW / "original_sequences" / "youtube" / QUALITY / "videos"
    if real_dir.exists():
        for v in sorted(real_dir.glob("*.mp4")):
            by_method["real"].append({"path": str(v), "label": "real", "method": "real", "name": v.name})

    for method in MANIPULATION_METHODS:
        fake_dir = DATA_RAW / "manipulated_sequences" / method / QUALITY / "videos"
        if fake_dir.exists():
            for v in sorted(fake_dir.glob("*.mp4")):
                by_method[method].append({"path": str(v), "label": "fake", "method": method, "name": v.name})

    videos = []
    for method, vids in by_method.items():
        if samples_per_method > 0 and len(vids) > samples_per_method:
            vids = random.sample(vids, samples_per_method)
        videos.extend(vids)

    return videos


def _run_single(video_dict):
    video_path = video_dict["path"]
    frames, fps = extract_frames(video_path, skip=1)

    all_landmarks = []
    cnn_face_crops = []
    for i, frame in enumerate(frames):
        faces = face_detection.detect_faces(frame)
        if faces:
            all_landmarks.append(faces[0].landmarks)
        else:
            all_landmarks.append(None)
        if i % SKIP_FRAME == 0:
            cnn_face_crops.append(faces)

    all_faces_flat = [f for faces in cnn_face_crops for f in faces]
    if all_faces_flat:
        spatial_score, per_face_scores, _, _ = spatial_cnn.run(all_faces_flat)
    else:
        spatial_score = 0.5
        per_face_scores = []

    artifact_score, _ = artifact.run(cnn_face_crops)
    temporal_data = temporal.run(frames, all_landmarks, fps=fps, skip=1)
    result = fusion.fuse(spatial_score, artifact_score, temporal_data)

    return {
        "total_frames": len(frames),
        "fps": fps,
        "faces_detected": len(all_faces_flat),
        "spatial_score": result["spatial_score"],
        "artifact_score": result["artifact_score"],
        "temporal_score": result["temporal_score"],
        "fused_score": result["fused_score"],
        "suspicion_level": result["suspicion_level"],
        "per_face_count": len(per_face_scores),
        "name": video_dict["name"],
        "label": video_dict["label"],
        "method": video_dict["method"],
    }


def compute_metrics(results):
    tp = fp = fn = tn = 0
    for r in results:
        pred = 1 if r["fused_score"] >= 0.3 else 0
        actual = 1 if r["label"] == "fake" else 0
        if pred == 1 and actual == 1:
            tp += 1
        elif pred == 1 and actual == 0:
            fp += 1
        elif pred == 0 and actual == 1:
            fn += 1
        else:
            tn += 1

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    acc = (tp + tn) / max(tp + fp + fn + tn, 1)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1, "acc": acc}


def find_optimal_threshold(results, step=0.01):
    best_f1 = 0
    best_thresh = 0.3
    for thresh in np.arange(0.1, 0.9, step):
        tp = fp = fn = tn = 0
        for r in results:
            pred = 1 if r["fused_score"] >= thresh else 0
            actual = 1 if r["label"] == "fake" else 0
            if pred == 1 and actual == 1:
                tp += 1
            elif pred == 1 and actual == 0:
                fp += 1
            elif pred == 0 and actual == 1:
                fn += 1
            else:
                tn += 1
        p = tp / max(tp + fp, 1)
        r = tp / max(tp + fn, 1)
        f1 = 2 * p * r / max(p + r, 1e-8)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh
    return float(best_thresh), float(best_f1)


def main():
    parser = argparse.ArgumentParser(description="Run full pipeline on sampled videos and analyze scores")
    parser.add_argument("-n", "--samples", type=int, default=50,
                        help="Videos to sample per method (0 = all, default: 50)")
    parser.add_argument("-j", "--workers", type=int, default=4,
                        help="Number of parallel workers (default: 4)")
    args = parser.parse_args()

    videos = find_videos(samples_per_method=args.samples)
    print(f"Found {len(videos)} videos to analyze")
    if args.samples > 0:
        print(f"(Sampled {args.samples} per method)")
    print(f"Workers: {args.workers}")

    if not videos:
        print("No videos found. Check data/raw/ directory structure.")
        sys.exit(1)

    results = []
    t_start = time.time()

    if args.workers <= 1:
        for i, v in enumerate(videos):
            try:
                data = _run_single(v)
                results.append(data)
                marker = {"none": ".", "low": "o", "moderate": "O", "high": "X"}.get(data["suspicion_level"], "?")
                print(f"  [{i+1}/{len(videos)}] {marker} {v['method']:15s} {v['name']:25s} "
                      f"spatial={data['spatial_score']:.3f}  artifact={data['artifact_score']:.3f}  "
                      f"temporal={data['temporal_score']:.3f}  FUSED={data['fused_score']:.3f}  [{data['suspicion_level']}]")
            except Exception as e:
                print(f"  [{i+1}/{len(videos)}] ERROR {v['name']}: {e}")
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(_run_single, v): v for v in videos}
            done = 0
            for future in as_completed(futures):
                v = futures[future]
                done += 1
                try:
                    data = future.result()
                    results.append(data)
                    marker = {"none": ".", "low": "o", "moderate": "O", "high": "X"}.get(data["suspicion_level"], "?")
                    print(f"  [{done}/{len(videos)}] {marker} {v['method']:15s} {v['name']:25s} "
                          f"spatial={data['spatial_score']:.3f}  artifact={data['artifact_score']:.3f}  "
                          f"temporal={data['temporal_score']:.3f}  FUSED={data['fused_score']:.3f}  [{data['suspicion_level']}]")
                except Exception as e:
                    print(f"  [{done}/{len(videos)}] ERROR {v['name']}: {e}")

    elapsed = time.time() - t_start
    print(f"\nAnalyzed {len(results)} videos in {elapsed:.1f}s\n")

    overall = compute_metrics(results)
    threshold, best_f1 = find_optimal_threshold(results)

    print("=" * 70)
    print("OVERALL RESULTS (threshold=0.3)")
    print("=" * 70)
    print(f"  Accuracy:  {overall['acc']:.4f}")
    print(f"  F1:        {overall['f1']:.4f}")
    print(f"  Precision: {overall['precision']:.4f}")
    print(f"  Recall:    {overall['recall']:.4f}")
    print(f"  Confusion: TP={overall['tp']} FP={overall['fp']} FN={overall['fn']} TN={overall['tn']}")
    print(f"\n  Optimal threshold: {threshold:.2f} (F1={best_f1:.4f})")

    print("\n" + "=" * 70)
    print("PER-METHOD BREAKDOWN")
    print("=" * 70)
    for method in ["real"] + MANIPULATION_METHODS:
        method_results = [r for r in results if r["method"] == method]
        if not method_results:
            continue
        m = compute_metrics(method_results)
        scores = [r["fused_score"] for r in method_results]
        print(f"  {method:15s}: acc={m['acc']:.3f}  F1={m['f1']:.3f}  "
              f"n={len(method_results):4d}  "
              f"score_range=[{min(scores):.3f}, {max(scores):.3f}]  "
              f"mean={np.mean(scores):.3f}")

    print("\n" + "=" * 70)
    print("SCORE DISTRIBUTION BY SUSPICION LEVEL")
    print("=" * 70)
    for level in ["none", "low", "moderate", "high"]:
        level_results = [r for r in results if r["suspicion_level"] == level]
        if not level_results:
            continue
        n_real = sum(1 for r in level_results if r["label"] == "real")
        n_fake = sum(1 for r in level_results if r["label"] == "fake")
        print(f"  {level:10s}: {len(level_results):4d} videos ({n_real} real, {n_fake} fake)")

    output_path = SPLITS_DIR / "score_distribution.json"
    with open(output_path, "w") as f:
        json.dump({
            "overall": overall,
            "optimal_threshold": threshold,
            "optimal_f1": best_f1,
            "videos": results,
        }, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
