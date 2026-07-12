import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    UPLOAD_DIR: str = str(BASE_DIR / "backend" / "uploads")
    RESULT_DIR: str = str(BASE_DIR / "backend" / "results")
    WEIGHTS_DIR: str = str(BASE_DIR / "weights")
    FRONTEND_DIST: str = str(BASE_DIR / "frontend" / "dist")
    MAX_VIDEO_DURATION: int = 180
    SKIP_FRAME: int = 3
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    def __init__(self):
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.RESULT_DIR, exist_ok=True)
        os.makedirs(self.WEIGHTS_DIR, exist_ok=True)


settings = Settings()
