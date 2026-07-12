import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TaskState:
    id: str
    status: str  # pending, processing, completed, failed
    progress: int = 0
    message: str = ""
    video_path: Optional[str] = None
    result_video_path: Optional[str] = None
    result_report_path: Optional[str] = None
    error: Optional[str] = None
    frame_scores: list = field(default_factory=list)
    frame_face_data: list = field(default_factory=list)
    analysis_result: Optional[dict] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskStore:
    def __init__(self):
        self._tasks: dict[str, TaskState] = {}
        self._lock = threading.Lock()

    def create(self, video_path: str) -> str:
        task_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._tasks[task_id] = TaskState(
                id=task_id,
                status="pending",
                video_path=video_path,
            )
        return task_id

    def get(self, task_id: str) -> Optional[TaskState]:
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task_id: str, **kwargs):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                for k, v in kwargs.items():
                    setattr(task, k, v)
                task.updated_at = datetime.now(timezone.utc).isoformat()

    def update_progress(self, task_id: str, progress: int, message: str = ""):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = progress
                if message:
                    task.message = message
                task.updated_at = datetime.now(timezone.utc).isoformat()


task_store = TaskStore()
