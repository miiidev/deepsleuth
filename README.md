# DeepSleuth

Local, offline deepfake video detection tool. Upload a video, get a forensic analysis with heatmap overlays, per-region breakdowns, and a downloadable PDF report.

No cloud upload. No black box. Every signal and threshold is disclosed.

## Overview

DeepSleuth applies three independent forensic signals to detect manipulation artifacts in video:

- **Spatial (55%)** — XceptionNet CNN classifies face crops as real/fake with Grad-CAM heatmaps showing which pixels influenced the decision. Per-region scoring across 6 facial zones (eyes, nose, mouth, forehead, cheeks, jawline).
- **Artifact (15%)** — Forensic artifact detection analyzing skin texture incongruence between face regions, boundary gradient anomalies at face-swap seams, specular highlight consistency, and spatial noise pattern uniformity.
- **Temporal (30%)** — Blink rate analysis (deviation from ~17 blinks/min), frame-to-frame flickering via multi-scale pixel differences, and facial landmark stability.

Scores are fused into a weighted composite. No single signal is definitive — the result reflects agreement across independent detection methods.

## Quick Start

### Windows (Recommended)

1. Go to the [Releases page](https://github.com/miiidev/deepsleuth/releases)
2. Download the latest `deepsleuth-v*.zip`
3. Extract the zip anywhere (e.g. `C:\Users\You\DeepSleuth`)
4. Double-click `install.ps1` — it will:
   - Check for Python 3.11+ (prompt to install if missing)
   - Create a virtual environment and install dependencies
   - Download the required model weights
   - Optionally create a desktop shortcut

That's it. When the script finishes, run DeepSleuth from the desktop shortcut or terminal:
```bash
.\.venv\Scripts\deepsleuth
```

### Prerequisites (all platforms)

- Python 3.11+
- CUDA-capable GPU recommended (CPU inference works but is slower)

### Manual Installation (alternative)

```bash
git clone https://github.com/miiidev/deepsleuth.git
cd deepsleuth

# Backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -e .

# Download model weights (required)
# Place xception_best.pth and face_landmarker.task in weights/

# Frontend (only needed if developing the UI)
# cd frontend
# npm install
# npm run build
```

### Running

```bash
deepsleuth
# or
python -m backend.cli
```

Opens at `http://127.0.0.1:8000`. Upload a video (MP4, MOV, AVI, or WEBM, max 3 minutes, 500 MB) and view the analysis.

## Architecture

```
Upload video
     |
     v
 Frame Extraction (OpenCV, every Nth frame)
     |
     v
 Face Detection (MediaPipe FaceLandmarker, 478 landmarks)
     |
     +---> Spatial CNN (XceptionNet + Grad-CAM + per-region scoring)
     |
     +---> Artifact Detection (texture + boundaries + highlights + noise)
     |
     +---> Temporal Analysis (blinks + flickering + landmark stability)
     |
     v
 Score Fusion (weighted sum -> suspicion level + explanations)
     |
     v
 PDF Report + Frontend Results Dashboard
```

### Suspicion Levels

| Level | Fused Score | Meaning |
|-------|-------------|---------|
| NONE | < 0.3 | No significant anomalies detected |
| LOW | 0.3 – 0.5 | Minor deviations, consistent with authentic footage |
| MODERATE | 0.5 – 0.7 | Anomalies detected, further review recommended |
| HIGH | >= 0.7 | Strong anomalies consistent with manipulation |

## Project Structure

```
deepsleuth/
├── backend/
│   ├── app/                  # FastAPI application
│   │   ├── main.py           # App instance, CORS, static file serving
│   │   ├── config.py         # Paths, limits, server settings
│   │   ├── task_store.py     # In-memory task state tracking
│   │   ├── history_store.py  # JSON-file persistence for past analyses
│   │   ├── routers/          # API routes (upload, status, download, history, metrics)
│   │   └── schemas/          # Pydantic request/response models
│   ├── detector/             # Core detection pipeline
│   │   ├── extraction.py     # Frame extraction from video
│   │   ├── face_detection.py # MediaPipe face detection + cropping
│   │   ├── spatial_cnn.py    # XceptionNet inference + Grad-CAM
│   │   ├── artifact.py       # Forensic artifact detection
│   │   ├── temporal.py       # Blink/flickering/stability analysis
│   │   ├── fusion.py         # Score fusion + explanations
│   │   ├── heatmap.py        # Bounding box overlay rendering
│   │   ├── report.py         # PDF report generation (ReportLab)
│   │   └── pipeline.py       # Pipeline orchestrator
│   └── cli.py                # Typer CLI entry point
├── frontend/
│   └── src/
│       ├── pages/            # Landing, Upload, Processing, Results, History, About, Methodology
│       ├── components/       # VideoPlayer, ConfidenceGraph, Sidebar, etc.
│       └── api/client.ts     # Axios API client + TypeScript interfaces
├── scripts/
│   ├── preprocess.py         # FaceForensics++ dataset preprocessing
│   ├── train.py              # XceptionNet training (AdamW, cosine annealing, mixed precision)
│   ├── evaluate.py           # Model evaluation with per-method breakdown
│   ├── score_distribution.py # Full pipeline evaluation on sampled videos
│   └── diagnose_pipeline.py  # Per-step pipeline debugging tool
├── weights/                  # Model weights (gitignored)
│   ├── xception_best.pth     # Trained PyTorch checkpoint
│   └── face_landmarker.task  # MediaPipe face detection model
├── data/
│   ├── raw/                  # FaceForensics++ dataset
│   ├── processed/            # Extracted face crops
│   └── splits/               # Train/test splits + evaluation results
└── pyproject.toml
```

## Technical Details

### Model

- **Architecture:** XceptionNet (depthwise separable convolutions, 12 residual blocks)
- **Input:** 224x224 RGB face crops
- **Output:** Binary classification (real vs fake) with softmax probability
- **Training:** FaceForensics++ c23 quality, 80/10/10 stratified split with identity leakage prevention, AdamW optimizer with cosine annealing + warmup, label smoothing, gradient clipping, mixed precision
- **Post-retrain accuracy:** 99.07% on test set

### Face Detection

MediaPipe FaceLandmarker with 478 facial landmarks. Faces are cropped and resized to 224x224 for CNN input. Landmarks are used for per-region scoring, blink detection, and artifact analysis.

### Dataset

FaceForensics++ with 4 manipulation methods:
- **Deepfakes** — autoencoder-based face swap
- **Face2Face** — face reenactment
- **FaceSwap** — 3D morphable model face swap
- **NeuralTextures** — neural texture manipulation

## Limitations

- Videos longer than 3 minutes are not supported
- Only one face per frame is analyzed (primary detected face)
- The model was trained on FaceForensics++ (c23 quality) — performance may vary on other manipulation methods or compression levels
- No automated system achieves 100% accuracy — false positives and false negatives occur
- Results should be interpreted alongside other evidence and domain expertise

## Tech Stack

**Backend:** Python, FastAPI, PyTorch, MediaPipe, OpenCV, ReportLab

**Frontend:** React 19, TypeScript, Tailwind CSS v4, Recharts, Axios, Vite

**Dataset:** FaceForensics++ (YouTube faces, 4 manipulation methods)
