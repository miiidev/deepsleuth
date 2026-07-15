import json
import os
import threading
from pathlib import Path
from app.config import settings
from app.task_store import TaskState


class HistoryStore:
    def __init__(self, history_dir: str):
        self._dir = history_dir
        self._lock = threading.Lock()
        os.makedirs(self._dir, exist_ok=True)

    def _path(self, task_id: str) -> str:
        return os.path.join(self._dir, f"{task_id}.json")

    def _index_path(self) -> str:
        return os.path.join(self._dir, "index.json")

    def _load_index(self) -> list[dict]:
        path = self._index_path()
        if not os.path.isfile(path):
            return []
        with open(path, "r") as f:
            return json.load(f)

    def _save_index(self, index: list[dict]):
        path = self._index_path()
        with open(path, "w") as f:
            json.dump(index, f, indent=2)

    def _entry_from_task(self, task: TaskState, filename: str) -> dict:
        return {
            "id": task.id,
            "filename": filename,
            "suspicion_level": task.analysis_result.get("suspicion_level", "none") if task.analysis_result else "none",
            "fused_score": task.analysis_result.get("fused_score", 0.0) if task.analysis_result else 0.0,
            "created_at": task.created_at,
        }

    def save(self, task: TaskState, filename: str):
        data = {
            "task_id": task.id,
            "filename": filename,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "video_path": task.video_path,
            "result_report_path": task.result_report_path,
            "error": task.error,
            "frame_scores": task.frame_scores,
            "frame_face_data": task.frame_face_data,
            "analysis_result": task.analysis_result,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
        with self._lock:
            path = self._path(task.id)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

            index = self._load_index()
            entry = self._entry_from_task(task, filename)
            existing = [e for e in index if e["id"] == task.id]
            if existing:
                existing[0].update(entry)
            else:
                index.append(entry)
            index.sort(key=lambda e: e["created_at"], reverse=True)
            self._save_index(index)

    def list(self, page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
        with self._lock:
            index = self._load_index()
        total = len(index)
        start = (page - 1) * per_page
        end = start + per_page
        items = index[start:end]
        return items, total

    def get(self, task_id: str) -> dict | None:
        path = self._path(task_id)
        if not os.path.isfile(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    def delete(self, task_id: str) -> bool:
        with self._lock:
            path = self._path(task_id)
            existed = os.path.isfile(path)
            if existed:
                os.remove(path)
            index = self._load_index()
            new_index = [e for e in index if e["id"] != task_id]
            if len(new_index) != len(index):
                self._save_index(new_index)
            return existed


history_store = HistoryStore(settings.HISTORY_DIR)
