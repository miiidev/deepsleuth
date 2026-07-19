import sys
import typer
import webbrowser
import threading
import time
import requests
from pathlib import Path
from rich.progress import Progress

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.main import app
import uvicorn

cli = typer.Typer()

WEIGHT_URLS = {
    "xception_best.pth": "https://github.com/miiidev/deepsleuth/releases/download/v0.1.0/xception_best.pth",
    "face_landmarker.task": "https://github.com/miiidev/deepsleuth/releases/download/v0.1.0/face_landmarker.task",
}


@cli.command()
def download_weights(
    force: bool = typer.Option(False, "--force", "-f", help="Re-download even if present"),
):
    """Download model weights required for deepfake detection."""
    weights_dir = Path(settings.WEIGHTS_DIR)
    weights_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in WEIGHT_URLS.items():
        dest = weights_dir / filename
        if dest.exists() and not force:
            typer.echo(f"{filename} already exists, skipping (use --force to re-download)")
            continue

        typer.echo(f"Downloading {filename}...")
        with Progress() as progress:
            task = progress.add_task(f"[cyan]Downloading {filename}...", total=None)
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            if total:
                progress.update(task, total=total)
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        progress.update(task, completed=downloaded)
            progress.update(task, completed=total or downloaded)

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
