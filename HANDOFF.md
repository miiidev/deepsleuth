# DeepSleuth — Handoff Document

## Project Overview

DeepSleuth is a deepfake detector web app. User uploads a video (max 3 min), the system analyzes it using a three-stream ensemble pipeline, and returns an MP4 with Grad-CAM++ heatmap overlay on suspicious face regions plus a PDF report.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| **Backend** | FastAPI + Celery + Redis |
| **Database** | SQLite (via SQLAlchemy + aiosqlite) |
| **ML Runtime** | ONNX Runtime (CPU, no GPU needed) |
| **Face Detection** | MediaPipe |
| **Spatial CNN** | XceptionNet → ONNX (trained on FaceForensics++) |
| **Grad-CAM** | Grad-CAM++ |
| **Frequency Analysis** | DCT coefficient anomaly (zero-shot) |
| **Temporal Analysis** | EAR (blink) + head pose (PNP) |
| **Frontend** | React + Vite + TailwindCSS |
| **Charts** | recharts |
| **PDF** | ReportLab |
| **Video Overlay** | Canvas compositing on `<video>` element |
| **Hosting** | Oracle Cloud Free Tier (Ampere A1 ARM, 2 vCPU, 12GB RAM) |
| **Deployment** | Docker Compose |

---

## Project Structure

```
deep-sleuth/
├── data/
│   ├── raw/                        # FF++ videos (gitignored)
│   │   ├── original_sequences/
│   │   │   └── c40/
│   │   │       └── videos/
│   │   └── manipulated_sequences/
│   │       └── c40/
│   │           └── videos/
│   ├── processed/                  # Extracted frames / face crops (gitignored)
│   └── splits/                     # Train/val/test CSV splits
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Settings (env vars, paths)
│   │   ├── database.py             # SQLite connection + models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py           # POST /upload
│   │   │   ├── status.py           # GET /task/{id}
│   │   │   └── download.py         # GET /result/{id}/video, /result/{id}/report
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── task.py             # Pydantic models
│   │
│   ├── detector/
│   │   ├── __init__.py
│   │   ├── pipeline.py             # Orchestrator: runs 3 streams → fusion
│   │   ├── extraction.py           # Frame extraction via OpenCV
│   │   ├── face_detection.py       # MediaPipe face detection + cropping
│   │   ├── spatial_cnn.py          # XceptionNet ONNX inference
│   │   ├── frequency.py            # DCT coefficient anomaly scoring
│   │   ├── temporal.py             # EAR (blink) + head pose analysis
│   │   ├── fusion.py               # Late fusion (weighted ensemble)
│   │   ├── heatmap.py              # Grad-CAM++ overlay generation
│   │   └── report.py               # ReportLab PDF generation
│   │
│   ├── celery_app.py               # Celery app definition
│   ├── tasks.py                    # Celery task (calls pipeline)
│   ├── uploads/                    # Uploaded videos (gitignored)
│   ├── results/                    # Output videos + PDFs (gitignored)
│   └── requirements.txt
│
├── weights/
│   └── xception_ffpp.onnx          # Trained model weights
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts           # Axios instance
│       ├── pages/
│       │   ├── Upload.tsx          # Drag-and-drop upload
│       │   ├── Processing.tsx      # Progress bar + polling
│       │   └── Results.tsx         # Video viewer + download report
│       └── components/
│           ├── VideoPlayer.tsx     # Side-by-side / overlay toggling
│           ├── ConfidenceGraph.tsx  # Per-frame timeline
│           └── ReportPreview.tsx    # Preview before download
│
├── infra/
│   └── docker-compose.yml
│
├── .gitignore
├── README.md
└── HANDOFF.md
```

---

## Where We Left Off

### Completed
- Project idea fully scoped via grilling session
- Architecture designed (three-stream ensemble, late fusion)
- Hosting platform chosen (Oracle Cloud Free Tier)
- Project structure outlined
- This handoff document written

### Not Started
- Environment setup (Python venv, Node modules, Redis)
- Any code — backend, frontend, ML pipeline, or infrastructure
- Dataset is being downloaded to `data/raw/`

---

## How to Continue (Next Steps, In Order)

### 1. Local Environment Setup

**Python (backend):**
```bash
cd deep-sleuth/backend
python -m venv venv
venv\Scripts\activate    # Windows
# or: source venv/bin/activate  # Linux/Mac

pip install fastapi uvicorn celery redis sqlalchemy aiosqlite
pip install onnxruntime opencv-python mediapipe numpy reportlab
pip install python-multipart Pillow aiofiles
pip freeze > requirements.txt
```

**Node.js (frontend):**
```bash
cd deep-sleuth/frontend
npm create vite@latest . -- --template react-ts
npm install tailwindcss @tailwindcss/vite recharts axios
```

**Redis (Windows — use WSL or Docker):**
```bash
# Option A: Docker
docker run -d -p 6379:6379 redis:alpine

# Option B: WSL (if you have WSL installed)
# wsl --install -d Ubuntu, then inside WSL: sudo apt install redis
```

**ffmpeg:** Install from https://ffmpeg.org/ and ensure it's on your PATH.

### 2. ML Pipeline (offline, local dev)

Build and test each module in `backend/detector/` in this order:

1. `extraction.py` — extract every 3rd frame from a video
2. `face_detection.py` — detect + crop faces using MediaPipe
3. `spatial_cnn.py` — load ONNX model, run inference on face crops
4. `frequency.py` — DCT block artifact scoring
5. `temporal.py` — EAR calculation + head pose estimation
6. `fusion.py` — weighted averaging of three scores
7. `heatmap.py` — Grad-CAM++ overlay rendering
8. `pipeline.py` — wire everything together end-to-end
9. `report.py` — generate PDF from results

### 3. Obtain the XceptionNet ONNX Model

**Option A: Download public pretrained weights (recommended)**
- Search GitHub for "FaceForensics++ XceptionNet ONNX" or "xception_ffpp.onnx"
- Place at `weights/xception_ffpp.onnx`

**Option B: Train from scratch (Google Colab)**
- Download FaceForensics++ to `data/raw/`
- Use Colab (free GPU) to train XceptionNet → export to ONNX
- Script references:
  - `data/splits/` for train/val split CSVs
  - Input: face crops from `data/processed/`
  - Output: `weights/xception_ffpp.onnx`

### 4. Backend API

Build the FastAPI app:
1. `database.py` — SQLite with SQLAlchemy async (task table: id, status, progress, video_path, result_path, created_at)
2. `celery_app.py` + `tasks.py` — Celery task that runs pipeline
3. `routers/upload.py` — accept video, create task, enqueue celery job
4. `routers/status.py` — return task status + progress %
5. `routers/download.py` — serve result video and PDF
6. `main.py` — wire everything, add CORS, static file serving

### 5. Frontend

Build the React app:
1. `Upload.tsx` — drag-and-drop file upload with 3-min validation
2. `Processing.tsx` — polls `GET /task/{id}` every 2s, shows progress bar
3. `Results.tsx` — video player with side-by-side / overlay toggle
4. `VideoPlayer.tsx` — canvas-overlaid heatmap + original toggle
5. `ConfidenceGraph.tsx` — interactive per-frame recharts line chart
6. `ReportPreview.tsx` — summary before PDF download

### 6. Deployment

1. Write `Dockerfile` for backend (python:3.11-slim + ONNX + OpenCV + MediaPipe)
2. Write `docker-compose.yml` (fastapi, celery-worker, redis)
3. Provision Oracle Cloud Free Tier ARM VM
4. Install Docker on VM, clone repo, `docker compose up -d`
5. (Optional) Set up Nginx reverse proxy + domain

---

## Design Decisions (Don't Change Lightly)

| Decision | Rationale |
|----------|-----------|
| Skip every 3rd frame | Balance of accuracy vs speed on CPU |
| Grad-CAM++ over Score-CAM | Good quality without heavy compute |
| ONNX over TensorFlow Lite | Better cross-platform, easier ARM deployment |
| Late fusion (simple weighted avg) | Easy to debug, easy to tweak weights per stream |
| SQLite over PostgreSQL | Zero infrastructure — just a file |
| Long-polling over WebSocket | Simpler, no persistent connection needed |
| No email notification | User keeps tab open, polling handles it |

---

## Performance Estimates (CPU, Oracle ARM)

| Video Length | Frames Processed | Est. Processing Time |
|-------------|-----------------|---------------------|
| 30 seconds  | ~300 (30fps / 3) | ~3-4 min |
| 1 minute    | ~600            | ~6-8 min |
| 3 minutes   | ~1800           | ~18-25 min |

---

## Dataset Notes

- FaceForensics++ c40 (highly compressed) is the recommended variant — closest to real-world upload conditions
- Dataset will only be used for training (or verifying pretrained weights)
- The deployed app never needs the dataset — only the ONNX model weights
- `data/` is gitignored — keep it out of version control

---

## Resources & References

- [FaceForensics++](https://github.com/ondyari/FaceForensics)
- [MediaPipe Face Detection](https://developers.google.com/mediapipe/solutions/vision/face_detector)
- [XceptionNet paper](https://arxiv.org/abs/1610.02357)
- [Grad-CAM++ paper](https://arxiv.org/abs/1710.11063)
- [ONNX Runtime docs](https://onnxruntime.ai/docs/)
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [FastAPI docs](https://fastapi.tiangolo.com/)
- [Celery docs](https://docs.celeryq.dev/)
- [ReportLab docs](https://www.reportlab.com/docs/)

---

## Contact

Built during a `/grilling` session via opencode. Refer to session history for full discussion on scope, architecture, and trade-offs.
