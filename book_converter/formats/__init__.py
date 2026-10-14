"""Output formats and the default registry."""

from .base import ConversionContext, OutputFile, OutputFormat
from .epub import EpubFormat
from .markdown import MarkdownFormat
from .mobi import MobiFormat
from .pdf import PdfFormat

# Order matters: later formats may use artifacts earlier ones leave in the
# conversion context (MOBI needs the EPUB built first).
DEFAULT_FORMATS = [MarkdownFormat(), EpubFormat(), PdfFormat(), MobiFormat()]

__all__ = [
    "ConversionContext",
    "OutputFile",
    "OutputFormat",
    "EpubFormat",
    "MarkdownFormat",
    "MobiFormat",
    "PdfFormat",
    "DEFAULT_FORMATS",
]
