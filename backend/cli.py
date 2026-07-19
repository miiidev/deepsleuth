import sys
import typer
import webbrowser
import threading
import time
import requests
import hashlib
from pathlib import Path
from rich.progress import Progress

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.main import app
import uvicorn

cli = typer.Typer()

WEIGHT_URLS = {
    "xception_best.pth": {
        "url": "https://github.com/miiidev/deepsleuth/releases/download/v0.1.0/xception_best.pth",
        "sha256": "760a7b4573197d921fb39ab2f3cd78eb7fecb180758d4d15ac4c0478da419187",
    },
    "face_landmarker.task": {
        "url": "https://github.com/miiidev/deepsleuth/releases/download/v0.1.0/face_landmarker.task",
        "sha256": "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
    },
}


@cli.command()
def download_weights(
    force: bool = typer.Option(False, "--force", "-f", help="Re-download even if present"),
):
    """Download model weights required for deepfake detection."""
    weights_dir = Path(settings.WEIGHTS_DIR)
    weights_dir.mkdir(parents=True, exist_ok=True)

    for filename, meta in WEIGHT_URLS.items():
        dest = weights_dir / filename
        if dest.exists() and not force:
            typer.echo(f"{filename} already exists, skipping (use --force to re-download)")
            continue

        tmp = dest.with_suffix(dest.suffix + ".part")
        typer.echo(f"Downloading {filename}...")
        try:
            with Progress() as progress:
                task = progress.add_task(f"[cyan]Downloading {filename}...", total=None)
                response = requests.get(meta["url"], stream=True, timeout=300)
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                if total:
                    progress.update(task, total=total)
                downloaded = 0
                with open(tmp, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            progress.update(task, completed=downloaded)
                progress.update(task, completed=total or downloaded)

            sha256 = hashlib.sha256()
            with open(tmp, "rb") as f:
                while True:
                    block = f.read(65536)
                    if not block:
                        break
                    sha256.update(block)
            actual = sha256.hexdigest()
            if actual != meta["sha256"]:
                tmp.unlink(missing_ok=True)
                typer.echo(
                    f"SHA256 mismatch for {filename}: expected {meta['sha256']}, got {actual}",
                    err=True,
                )
                raise typer.Exit(code=1)

            tmp.rename(dest)
        except Exception:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise

    typer.echo("All weights downloaded successfully.")


def _check_weights() -> bool:
    weights_dir = Path(settings.WEIGHTS_DIR)
    for filename in WEIGHT_URLS:
        if not (weights_dir / filename).is_file():
            return False
    return True


@cli.callback(invoke_without_command=True)
def serve(
    ctx: typer.Context,
    host: str = typer.Option(settings.HOST, "--host", "-h", help="Host to bind"),
    port: int = typer.Option(settings.PORT, "--port", "-p", help="Port to bind"),
    open_browser: bool = typer.Option(True, "--open", "-o", help="Open browser automatically"),
):
    if ctx.invoked_subcommand is not None:
        return

    if not _check_weights():
        typer.echo(
            "Model weights not found. Run 'deepsleuth download-weights' first.",
            err=True,
        )
        raise typer.Exit(code=1)

    url = f"http://{host}:{port}"
    typer.echo(f"DeepSleuth starting at {url}")

    if open_browser:
        threading.Thread(
            target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True
        ).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    cli()
