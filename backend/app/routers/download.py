from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.task_store import task_store

router = APIRouter()


@router.get("/result/{task_id}/video")
async def download_video(task_id: str):
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.status != "completed" or not task.result_video_path:
        raise HTTPException(400, "Video not ready yet")
    return FileResponse(task.result_video_path, media_type="video/mp4", filename="result.mp4")


@router.get("/result/{task_id}/original")
async def download_original(task_id: str):
    task = task_store.get(task_id)
    if not task or not task.video_path:
        raise HTTPException(404, "Task or video not found")
    return FileResponse(task.video_path, media_type="video/mp4", filename="original.mp4")


@router.get("/result/{task_id}/report")
async def download_report(task_id: str):
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.status != "completed" or not task.result_report_path:
        raise HTTPException(400, "Report not ready yet")
    return FileResponse(task.result_report_path, media_type="application/pdf", filename="report.pdf")
