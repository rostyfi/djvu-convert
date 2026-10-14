"""Output-format abstraction — the extension point for new ebook formats.

To add a format, subclass OutputFormat, implement build(), and add an
instance to DEFAULT_FORMATS in formats/__init__.py. Order matters: a format
can rely on artifacts earlier formats leave in the conversion context (MOBI
needs the EPUB path, for example).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ConversionContext:
    """Everything an output format needs, produced by the pipeline."""

    workdir: str
    out_dir: str
    name: str                        # book title / base filename
    page_markdowns: list[str]        # one markdown string per page
    image_files: list[tuple[str, str]]  # (filename, path on disk)
    markdown: str                    # all pages joined into one document
    epub_path: str | None = None     # set by the EPUB format


@dataclass(frozen=True)
class OutputFile:
    """A finished download: where it is and how to serve it."""

    path: str
    mimetype: str
    filename: str


class OutputFormat(ABC):
    """One downloadable output format (epub, mobi, pdf, ...)."""

    key: str = ""              # download key: /download/<job>/<key>
    required: bool = True      # a failure fails the whole job
    status: str | None = None  # progress status shown while building

    @abstractmethod
    def build(self, ctx: ConversionContext) -> list[tuple[str, OutputFile]]:
        """Build the output(s); returns [(key, OutputFile), ...]."""
