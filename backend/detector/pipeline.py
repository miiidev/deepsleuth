import os
import numpy as np
from app.config import settings
from app.task_store import task_store
from detector import extraction, face_detection, spatial_cnn, frequency, temporal, fusion, report


def _progress_callback(task_id: str, pct: int, msg: str):
    task_store.update_progress(task_id, pct, msg)


def _merge_region_scores(all_regions: list[dict[str, float]]) -> dict[str, float]:
    if not all_regions:
        return {}
    keys = all_regions[0].keys()
    merged = {}
    for k in keys:
        vals = [r[k] for r in all_regions if k in r]
        merged[k] = float(np.mean(vals)) if vals else 0.0
    return merged


def run_pipeline(video_path: str, task_id: str, result_dir: str):
    try:
        task_store.update(task_id, status="processing", progress=0, message="Extracting frames...")

        frames = extraction.extract_frames(video_path, skip=settings.SKIP_FRAME)
        total = len(frames)
        if total == 0:
            raise ValueError("No frames extracted from video")

        _progress_callback(task_id, 5, f"Extracted {total} frames")

        all_face_crops = []
        per_frame_scores = []
        frame_face_data = []

        for i, frame in enumerate(frames):
            faces = face_detection.detect_faces(frame)
            all_face_crops.append(faces)
            frame_idx = i * settings.SKIP_FRAME
            frame_face_data.append({
                "frame": frame_idx,
                "faces": [{"bbox": list(fr.bbox), "score": 0.5} for fr in faces],
            })
            pct = 5 + int((i / total) * 30)
            _progress_callback(task_id, pct, f"Detecting faces... ({i+1}/{total})")

        _progress_callback(task_id, 35, "Running spatial CNN...")
        all_faces_flat = [f for faces in all_face_crops for f in faces]
        spatial_score, per_face_scores, per_face_heatmaps, per_face_regions = spatial_cnn.run(all_faces_flat)

        _progress_callback(task_id, 50, "Running frequency analysis...")
        frequency_score, per_face_freq_scores = frequency.run(all_face_crops)

        _progress_callback(task_id, 65, "Running temporal analysis...")
        all_landmarks = []
        for faces in all_face_crops:
            if faces:
                all_landmarks.append(faces[0].landmarks)
            else:
                all_landmarks.append(None)
        temporal_data = temporal.run(frames, all_landmarks, fps=30.0)

        _progress_callback(task_id, 80, "Fusing scores...")
        merged_regions = _merge_region_scores(per_face_regions)
        fusion_result = fusion.fuse(spatial_score, frequency_score, temporal_data, merged_regions)

        _progress_callback(task_id, 85, "Building face data...")
        heatmap_idx = 0
        face_score_idx = 0
        freq_score_idx = 0
        for entry in frame_face_data:
            n = len(entry["faces"])
            for j in range(n):
                entry["faces"][j]["score"] = per_face_scores[face_score_idx + j]
                entry["faces"][j]["heatmap"] = per_face_heatmaps[heatmap_idx + j]
                per_frame_scores.append(per_face_scores[face_score_idx + j])
            face_score_idx += n
            heatmap_idx += n
            freq_score_idx += n

        _progress_callback(task_id, 90, "Generating report...")
        out_dir = os.path.join(result_dir, task_id)
        os.makedirs(out_dir, exist_ok=True)
        report_path = os.path.join(out_dir, "report.pdf")
        report.generate_report(report_path, fusion_result, task_id)

        _progress_callback(task_id, 95, "Finalizing...")
        task_store.update(
            task_id,
            status="completed",
            progress=100,
            message="Complete!",
            result_report_path=report_path,
            frame_scores=per_frame_scores,
            frame_face_data=frame_face_data,
            analysis_result=fusion_result,
        )

    except Exception as e:
        task_store.update(task_id, status="failed", error=str(e), progress=0, message="Failed")
