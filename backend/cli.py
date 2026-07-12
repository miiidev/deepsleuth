import sys
import typer
import webbrowser
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.main import app
import uvicorn

cli = typer.Typer()


@cli.callback(invoke_without_command=True)
def serve(
    ctx: typer.Context,
    host: str = typer.Option(settings.HOST, "--host", "-h", help="Host to bind"),
    port: int = typer.Option(settings.PORT, "--port", "-p", help="Port to bind"),
    open_browser: bool = typer.Option(True, "--open", "-o", help="Open browser automatically"),
):
    if ctx.invoked_subcommand is not None:
        return
    url = f"http://{host}:{port}"
    typer.echo(f"DeepSleuth starting at {url}")

    if open_browser:
        threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    cli()
