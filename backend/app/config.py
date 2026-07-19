import os
from pathlib import Path
from platformdirs import user_data_dir

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings:
    def __init__(self):
        if (BASE_DIR / ".git").exists():
            data_dir = BASE_DIR
        else:
            data_dir = Path(user_data_dir("deepsleuth", ensure_exists=True))

        self.DATA_DIR = data_dir
        self.UPLOAD_DIR = str(data_dir / "backend" / "uploads")
        self.RESULT_DIR = str(data_dir / "backend" / "results")
        self.HISTORY_DIR = str(data_dir / "backend" / "history")
        self.WEIGHTS_DIR = str(data_dir / "weights")
        self.FRONTEND_DIST = str(BASE_DIR / "backend" / "app" / "static")
        self.MAX_VIDEO_DURATION = 180
        self.SKIP_FRAME = 3
        self.HOST = "127.0.0.1"
        self.PORT = 8000

        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.RESULT_DIR, exist_ok=True)
        os.makedirs(self.HISTORY_DIR, exist_ok=True)
        os.makedirs(self.WEIGHTS_DIR, exist_ok=True)


settings = Settings()
