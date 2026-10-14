"""LaTeX formula rendering for the PDF output.

Mistral OCR emits formulas as LaTeX; they are normalized (normalize.py),
split into environments (environments.py), rendered to vector SVGs with
matplotlib's mathtext engine (render.py) and pulled out of the OCR markdown
(extract.py).
"""

from .exceptions import MathUnsupported
from .extract import extract_math, page_to_html
from .normalize import normalize_tex
from .render import formula_to_html

__all__ = [
    "MathUnsupported",
    "extract_math",
    "page_to_html",
    "normalize_tex",
    "formula_to_html",
]
