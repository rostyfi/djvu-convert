"""MOBI (Kindle) output format — EPUB -> MOBI via calibre's ebook-convert."""

import os
import shutil

from ..process import run_checked
from .base import OutputFile, OutputFormat


class MobiFormat(OutputFormat):
    key = "mobi"
    required = False  # a bonus format — never fail the whole job

    def build(self, ctx):
        if not ctx.epub_path:
            raise RuntimeError("MOBI output requires the EPUB to be built first")
        mobi_path = os.path.join(ctx.out_dir, f"{ctx.name}.mobi")
        convert_epub_to_mobi(ctx.epub_path, mobi_path)
        return [("mobi", OutputFile(mobi_path, "application/x-mobipocket-ebook",
                                    f"{ctx.name}.mobi"))]


def convert_epub_to_mobi(epub_path, mobi_path):
    """Convert an EPUB to MOBI (Kindle format) using calibre's ebook-convert."""
    if shutil.which("ebook-convert") is None:
        raise RuntimeError(
            "'ebook-convert' (calibre) not found — install it first: "
            "sudo apt-get install calibre (Debian/Ubuntu), "
            "brew install --cask calibre (macOS)"
        )
    run_checked(["ebook-convert", epub_path, mobi_path])
    if not os.path.exists(mobi_path) or os.path.getsize(mobi_path) == 0:
        raise RuntimeError("ebook-convert finished but produced no output file")

