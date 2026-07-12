import os
import threading
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from app.task_store import task_store
from app.schemas.task import UploadResponse
from detector.pipeline import run_pipeline

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}


def _validate_video(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    import cv2
    import tempfile

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(file.file.read())
    tmp.close()
    file.file.seek(0)

    cap = cv2.VideoCapture(tmp.name)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    duration = frame_count / fps if fps > 0 else 0
    os.unlink(tmp.name)

    if duration > settings.MAX_VIDEO_DURATION:
        raise HTTPException(400, f"Video too long ({duration:.0f}s). Max {settings.MAX_VIDEO_DURATION}s")

    return ext


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    ext = _validate_video(file)
    task_id = task_store.create(video_path="")
    video_dir = os.path.join(settings.UPLOAD_DIR, task_id)
    os.makedirs(video_dir, exist_ok=True)
    video_path = os.path.join(video_dir, f"input{ext}")
    content = await file.read()
    with open(video_path, "wb") as f:
        f.write(content)

    task_store.update(task_id, video_path=video_path, status="pending")

    thread = threading.Thread(
        target=run_pipeline,
        args=(video_path, task_id, settings.RESULT_DIR),
        daemon=True,
    )
    thread.start()

    return UploadResponse(task_id=task_id)
