from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    task_id: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    filename: str = ""
    error: Optional[str] = None
    frame_scores: list = []
    frame_face_data: list = []
    analysis_result: Optional[dict] = None
    created_at: str
    updated_at: str
