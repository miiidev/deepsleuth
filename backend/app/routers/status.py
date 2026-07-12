from fastapi import APIRouter, HTTPException
from app.task_store import task_store
from app.schemas.task import TaskStatus

router = APIRouter()


@router.get("/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return TaskStatus(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        message=task.message,
        error=task.error,
        frame_scores=task.frame_scores,
        frame_face_data=task.frame_face_data,
        analysis_result=task.analysis_result,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
