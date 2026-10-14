"""Markdown + plain-text output formats (.md, .txt and .md+images .zip)."""

import os
import zipfile

from ..text import markdown_to_text
from .base import OutputFile, OutputFormat


class MarkdownFormat(OutputFormat):
    key = "md"

    def build(self, ctx):
        md_path = os.path.join(ctx.out_dir, f"{ctx.name}.md")
        txt_path = os.path.join(ctx.out_dir, f"{ctx.name}.txt")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(ctx.markdown)
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(markdown_to_text(ctx.markdown))

        zip_path = os.path.join(ctx.out_dir, f"{ctx.name}-md-with-images.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(md_path, f"{ctx.name}.md")
            for fname, fullpath in ctx.image_files:
                zf.write(fullpath, f"images/{fname}")

        return [
            ("md", OutputFile(zip_path, "application/zip",
                              f"{ctx.name}-md-with-images.zip")),
            ("txt", OutputFile(txt_path, "text/plain", f"{ctx.name}.txt")),
        ]
