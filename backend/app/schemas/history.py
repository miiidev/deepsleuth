from pydantic import BaseModel
from typing import Optional


class HistoryEntry(BaseModel):
    id: str
    filename: str
    suspicion_level: str
    fused_score: float
    created_at: str


class HistoryListResponse(BaseModel):
    items: list[HistoryEntry]
    total: int
    page: int
    per_page: int


class HistoryDetail(BaseModel):
    task_id: str
    filename: str
    status: str
    progress: int
    message: str
    video_path: Optional[str] = None
    result_report_path: Optional[str] = None
    error: Optional[str] = None
    frame_scores: list = []
    frame_face_data: list = []
    analysis_result: Optional[dict] = None
    created_at: str
    updated_at: str
