from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routers import upload, status, download
import os

app = FastAPI(title="DeepSleuth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/v1")
app.include_router(status.router, prefix="/api/v1")
app.include_router(download.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


if os.path.isdir(settings.FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=settings.FRONTEND_DIST, html=True), name="frontend")
