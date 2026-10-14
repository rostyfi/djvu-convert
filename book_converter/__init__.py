"""Book converter: turn a DJVU book into an ebook using Mistral OCR.

Pipeline: .djvu -> page images (ddjvu + Pillow) -> per-page Mistral OCR
(text + image detection) -> .epub -> .mobi, plus .md+images / .txt / .pdf.
The PDF renders the LaTeX formulas that Mistral OCR emits as vector graphics.
"""

__version__ = "1.0.0"
