"""Plain-text helpers."""

import os
import re


def markdown_to_text(markdown):
    """Plain-text version of the OCR markdown (image embeds removed)."""
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)



def sanitize_book_name(filename):
    """Filesystem-safe base name (no extension) for an uploaded book file."""
    stem = os.path.splitext(filename)[0]
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("_") or "book"
