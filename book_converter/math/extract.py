"""Markdown -> HTML for the PDF: pull out LaTeX math, render it, convert."""

import re

from .render import formula_to_html


_MATH_TOKEN = "MATHFORMULA%06dPLACEHOLDER"

_MATH_SEGMENT_RES = [
    (re.compile(r"(?<!\\)\$\$(.+?)(?<!\\)\$\$", re.S), "display"),
    (re.compile(r"(?<!\\)\\\[((?:\\.|[^\\])+?)\\\]", re.S), "display"),
    (re.compile(r"(?<!\\)\\\((.+?)\\\)", re.S), "inline"),
]
_MATH_DOLLAR_RE = re.compile(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$")
_MATHISH_RE = re.compile(r"\\[a-zA-Z]|[\\^_]")


def extract_math(text):
    """Replace LaTeX math segments in OCR markdown with placeholder tokens.

    Returns (text_with_tokens, [(tex, mode)]) where mode is "inline"/"display".
    """
    formulas = []

    def register(tex, mode):
        tex = tex.strip()
        if not tex:
            return ""
        formulas.append((tex, mode))
        return _MATH_TOKEN % (len(formulas) - 1)

    for pattern, mode in _MATH_SEGMENT_RES:
        text = pattern.sub(lambda m: register(m.group(1), mode), text)

    def dollar_sub(m):
        body = m.group(1).strip()
        if _MATHISH_RE.search(body) or re.fullmatch(r"[a-zA-Z]", body):
            return register(body, "inline")
        return m.group(0)  # e.g. "$5 and $10" — not math

    text = _MATH_DOLLAR_RE.sub(dollar_sub, text)
    return text, formulas


def page_to_html(text, md_lib):
    """Convert one page of OCR markdown to HTML, rendering the formulas."""
    text, formulas = extract_math(text)
    body = md_lib.markdown(text, extensions=["tables", "fenced_code"])
    for i, (tex, mode) in enumerate(formulas):
        token = _MATH_TOKEN % i
        html = formula_to_html(tex, mode == "display")
        if mode == "display":
            body, n = re.subn(r"<p>\s*" + token + r"\s*</p>", lambda m: html, body)
            if n:
                continue
        body = body.replace(token, html)
    return body

