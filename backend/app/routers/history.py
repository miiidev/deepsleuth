from fastapi import APIRouter, HTTPException, Query
from app.history_store import history_store
from app.schemas.history import HistoryListResponse, HistoryEntry, HistoryDetail

router = APIRouter()


@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    items, total = history_store.list(page=page, per_page=per_page)
    return HistoryListResponse(
        items=[HistoryEntry(**e) for e in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/history/{task_id}", response_model=HistoryDetail)
async def get_history_detail(task_id: str):
    data = history_store.get(task_id)
    if not data:
        raise HTTPException(404, "History entry not found")
    return HistoryDetail(**data)


@router.delete("/history/{task_id}")
async def delete_history(task_id: str):
    ok = history_store.delete(task_id)
    if not ok:
        raise HTTPException(404, "History entry not found")
    return {"status": "deleted"}
