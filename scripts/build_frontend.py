import subprocess
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"


def main():
    print("Building frontend...")
    subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_DIR),
        check=True,
    )

    if STATIC_DIR.exists():
        shutil.rmtree(STATIC_DIR)
    shutil.copytree(str(FRONTEND_DIR / "dist"), str(STATIC_DIR))
    print(f"Frontend built and copied to {STATIC_DIR}")


if __name__ == "__main__":
    main()
