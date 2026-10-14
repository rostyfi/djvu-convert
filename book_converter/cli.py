"""Command-line entry point: `python app.py` or `python -m book_converter`."""

import shutil

from .config import Settings
from .web import create_app


def main(settings=None):
    settings = settings or Settings.from_env()
    app = create_app(settings)
    if shutil.which("ddjvu") is None:
        print("WARNING: 'ddjvu' (djvulibre) not found on PATH — install it first:")
        print("  Debian/Ubuntu: sudo apt-get install djvulibre-bin")
        print("  macOS:         brew install djvulibre")
    app.run(host=settings.host, port=settings.port, threaded=True)
