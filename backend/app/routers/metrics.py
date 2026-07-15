import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

_metrics: dict | None = None

SPLITS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "splits" / "splits.json"
PYPROJECT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "pyproject.toml"


def _load_metrics() -> dict:
    global _metrics
    if _metrics is not None:
        return _metrics

    version = "0.1.0"
    if PYPROJECT_PATH.exists():
        for line in PYPROJECT_PATH.read_text().splitlines():
            if line.strip().startswith("version"):
                version = line.split("=")[1].strip().strip('"').strip("'")
                break

    benchmark: dict = {}
    if SPLITS_PATH.exists():
        data = json.loads(SPLITS_PATH.read_text())
        benchmark = {
            "dataset": "FaceForensics++",
            "quality": "c40",
            "test_samples": data.get("test_real", 0) + data.get("test_fake", 0),
            "accuracy": round(data.get("test_accuracy", 0), 4),
            "f1": round(data.get("test_f1", 0), 4),
            "precision": round(data.get("test_precision", 0), 4),
            "recall": round(data.get("test_recall", 0), 4),
            "split_ratio": "80/10/10",
            "model": "XceptionNet",
            "epochs": 40,
        }

    _metrics = {"version": version, "benchmark": benchmark}
    return _metrics


@router.get("/metrics")
async def get_metrics():
    return _load_metrics()
