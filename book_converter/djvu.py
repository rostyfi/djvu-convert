"""DJVU page rendering (djvulibre + Pillow)."""

import io
import os
import shutil

from .process import run_checked


def djvu_page_images(djvu_path, out_dir, dpi):
    """Render every page of a DJVU file to PNG at the given DPI.

    Returns the PNG paths in page order.
    """
    if shutil.which("ddjvu") is None:
        raise RuntimeError(
            "'ddjvu' (djvulibre) not found on PATH — install it first: "
            "sudo apt-get install djvulibre-bin (Debian/Ubuntu), "
            "brew install djvulibre (macOS)"
        )
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is not installed — run: pip install pillow") from exc

    count = run_checked(["djvused", djvu_path, "-e", "n"], text=True)
    try:
        total = int(count.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"Could not read DJVU file: unexpected 'djvused' output {count.stdout!r}"
        ) from exc
    if total < 1:
        raise RuntimeError("No pages found — is this a valid DJVU file?")

    paths = []
    for page_no in range(1, total + 1):
        proc = run_checked(
            ["ddjvu", "-format=ppm", f"-page={page_no}", f"-scale={dpi}", djvu_path, "-"]
        )
        png = os.path.join(out_dir, f"page-{page_no:04d}.png")
        with Image.open(io.BytesIO(proc.stdout)) as image:
            image.save(png)
        paths.append(png)
    return paths

