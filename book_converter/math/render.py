"""Formula rendering: mathtext -> vector SVG, environments -> HTML tables.

A formula that cannot be parsed falls back to showing the raw LaTeX in a
<code> span, so it is never silently lost.
"""

import base64
import io
import re
import warnings

from .environments import (
    _CASES_ENVS,
    _CENTERED_ALIGN_ENVS,
    _ENV_DELIMS,
    _MATRIX_ENVS,
    _split_cells,
    _split_env_segments,
    _split_rows,
)
from .exceptions import MathUnsupported
from .normalize import _fix_unknown_cmd, _has_row_break, normalize_tex


PDF_MARGIN_MM = 18            # side margins (top/bottom are 20mm, in the CSS)
PDF_FONT_SIZE = 10.5          # pt — math is rendered at this size to match text
# A5 is 148 mm wide; the text column width in points:
PDF_CONTENT_WIDTH_PT = (148 - 2 * PDF_MARGIN_MM) * 72 / 25.4
_MATH_ROW_PAD_PT = 1.05       # vertical padding per matrix row (td: 0.05em)

_MATHTEXT = None


def _mathtext():
    """Lazily import matplotlib's mathtext engine (heavy import)."""
    global _MATHTEXT
    if _MATHTEXT is None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            matplotlib.rcParams["mathtext.fontset"] = "cm"  # Computer Modern look
            from matplotlib import mathtext
            from matplotlib.font_manager import FontProperties
        except ImportError as exc:
            raise RuntimeError(
                "The 'matplotlib' package is not installed — run: pip install matplotlib "
                "(needed to render formulas in the PDF output)"
            ) from exc
        _MATHTEXT = (mathtext, FontProperties)
    return _MATHTEXT


def _render_math_svg(tex, size=PDF_FONT_SIZE):
    """Render a mathtext-compatible formula to a self-contained SVG.

    Returns (svg, width_pt, height_pt, depth_pt); depth is the distance from
    the baseline to the bottom of the box (used for vertical alignment).
    Raises MathUnsupported if the SVG is missing or degenerate.
    """
    mathtext, FontProperties = _mathtext()
    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        depth = mathtext.math_to_image(f"${tex}$", buf, dpi=300, format="svg",
                                       prop=FontProperties(size=size))
    svg = buf.getvalue().decode("utf-8")
    start = svg.find("<svg")
    if start == -1:
        raise MathUnsupported("no SVG output")
    svg = svg[start:]  # drop the XML declaration and DOCTYPE
    m = re.search(r'width="([\d.]+)pt" height="([\d.]+)pt"', svg)
    if not m:
        raise MathUnsupported("SVG has no size")
    width, height = float(m.group(1)), float(m.group(2))
    if width <= 0 or height <= 0:
        raise MathUnsupported("degenerate SVG")
    return svg, width, height, depth


_UNRENDERABLE_MARKERS = (
    r"\xymatrix", r"\tikz", r"\chemfig", r"\feynman",
    r"\begin{asy}", r"\begin{circuitikz}", r"\begin{forest}", r"\begin{pgfplot}",
)

_LEFT_DELIM_RE = re.compile(r"\\left\s*(\\[{}()\[\]|.]|[()\[\]|.])\s*$")
_RIGHT_DELIM_RE = re.compile(r"^\s*\\right\s*(\\[{}()\[\]|.]|[()\[\]|.])")


def _strip_dangling_delims(tex):
    """Remove a trailing \\left<delim> / leading \\right<delim>."""
    tex = re.sub(r"\\left\s*(\\[{}()\[\]|.]|[()\[\]|.])\s*$", "", tex)
    tex = re.sub(r"^\s*\\right\s*(\\[{}()\[\]|.]|[()\[\]|.])", "", tex)
    return tex


def _math_img_html(svg, width, height, depth, alt, max_w):
    """An <img> tag for a rendered formula, scaled down to max_w if needed."""
    from xml.sax.saxutils import escape
    if max_w and width > max_w:
        scale = max_w / width
        width, height, depth = width * scale, height * scale, depth * scale
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    alt = escape(" ".join(alt.split()), {'"': "&quot;"})
    return (
        f'<img class="math" alt="{alt}" src="data:image/svg+xml;base64,{b64}" '
        f'style="width:{width:.2f}pt;height:{height:.2f}pt;'
        f'vertical-align:-{depth:.2f}pt">'
    )


def _delim_html(glyph_tex, height_pt):
    """A stretched delimiter glyph (paren/bracket/brace) as an SVG <img>."""
    from xml.sax.saxutils import escape
    _, _, h100, _ = _render_math_svg(glyph_tex, size=100.0)
    size = 100.0 * height_pt / h100 if h100 > 0 else 100.0
    size = min(max(size, 5.0), 500.0)
    svg, width, height, _ = _render_math_svg(glyph_tex, size=size)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        f'<img class="mdelim" alt="{escape(glyph_tex)}" '
        f'src="data:image/svg+xml;base64,{b64}" '
        f'style="width:{width:.2f}pt;height:{height:.2f}pt">'
    )


def _math_node(tex, max_w):
    """Render a plain (environment-free) formula; returns (html, height_pt)."""
    for marker in _UNRENDERABLE_MARKERS:
        if marker in tex:
            raise MathUnsupported(f"unrenderable: {marker}")
    tex = normalize_tex(tex)
    if not tex.strip():
        raise MathUnsupported("empty formula")
    if _has_row_break(tex):
        tex = "\\substack{" + tex + "}"  # stack multi-line formulas
    current = tex
    for _ in range(12):
        try:
            svg, width, height, depth = _render_math_svg(current)
        except ValueError as exc:  # mathtext ParseException
            m = re.search(r"Unknown symbol: (\\[A-Za-z]+)", str(exc))
            if not m:
                raise MathUnsupported(str(exc)) from exc
            current = _fix_unknown_cmd(current, m.group(1))
            continue
        return _math_img_html(svg, width, height, depth, tex, max_w), height
    raise MathUnsupported("too many unknown commands")


def _grid_node(env, body, max_w):
    """Render a matrix/cases/array environment as an HTML table."""
    if env in ("numcases", "subnumcases"):
        body = re.sub(r"^\s*\\\{", "", body)
    cell_max_w = max_w * 0.5
    rows_html = []
    height = 0.0
    for row in _split_rows(body):
        tds = []
        row_height = 0.0
        for cell in _split_cells(row):
            if cell.strip():
                html, h = _formula_node(cell, cell_max_w)
            else:
                html, h = "", 0.0
            tds.append(f"<td>{html}</td>")
            row_height = max(row_height, h)
        rows_html.append("<tr>" + "".join(tds) + "</tr>")
        height += max(row_height, PDF_FONT_SIZE) + _MATH_ROW_PAD_PT
    height = max(height - _MATH_ROW_PAD_PT, 0.0)
    left, right = _ENV_DELIMS.get(env, (None, None))
    parts = []
    if left:
        parts.append(_delim_html(left, height * 1.12))
    parts.append('<table class="mgrid">' + "".join(rows_html) + "</table>")
    if right:
        parts.append(_delim_html(right, height * 1.12))
    return '<span class="mwrap">' + "".join(parts) + "</span>", height


def _align_node(env, body, max_w):
    """Render an align/gather/multline environment as an aligned HTML table."""
    cell_max_w = max_w * 0.5
    centered = env in _CENTERED_ALIGN_ENVS
    rows_html = []
    height = 0.0
    for row in _split_rows(body):
        tds = []
        row_height = 0.0
        for i, cell in enumerate(_split_cells(row)):
            if cell.strip():
                html, h = _formula_node(cell, cell_max_w)
            else:
                html, h = "", 0.0
            if centered:
                cls = ""
            else:
                cls = ' class="al-r"' if i % 2 == 0 else ' class="al-l"'
            tds.append(f"<td{cls}>{html}</td>")
            row_height = max(row_height, h)
        rows_html.append("<tr>" + "".join(tds) + "</tr>")
        height += max(row_height, PDF_FONT_SIZE) + _MATH_ROW_PAD_PT
    height = max(height - _MATH_ROW_PAD_PT, 0.0)
    return '<table class="mgrid">' + "".join(rows_html) + "</table>", height


def _env_node(env, body, max_w):
    if env in _MATRIX_ENVS or env in _CASES_ENVS:
        return _grid_node(env, body, max_w)
    return _align_node(env, body, max_w)


def _formula_node(tex, max_w):
    """Render a formula to (html, height_pt); raises MathUnsupported."""
    segments = list(_split_env_segments(tex))
    # Group segments into render units; \left<delim> env \right<delim> becomes
    # one unit rendered with stretched delimiter glyphs around the table.
    units = []  # ("math", text) | ("env", env, body) | ("wrap", env, body, l, r)
    i = 0
    while i < len(segments):
        text, env, body = segments[i]
        if env is not None:
            units.append(("env", env, body))
            i += 1
            continue
        left_m = _LEFT_DELIM_RE.search(text)
        if (left_m and i + 2 < len(segments)
                and segments[i + 1][1] is not None and segments[i + 2][1] is None):
            right_m = _RIGHT_DELIM_RE.match(segments[i + 2][0])
            if right_m:
                pre = text[:left_m.start()]
                post = segments[i + 2][0][right_m.end():]
                if pre.strip():
                    units.append(("math", pre))
                units.append(("wrap", segments[i + 1][1], segments[i + 1][2],
                              left_m.group(1), right_m.group(1)))
                if post.strip():
                    units.append(("math", post))
                i += 3
                continue
        units.append(("math", text))
        i += 1

    parts = []
    height = 0.0
    for unit in units:
        if unit[0] == "math":
            try:
                html, h = _math_node(unit[1], max_w)
            except MathUnsupported:
                # e.g. a dangling \left( before an environment — drop it
                stripped = _strip_dangling_delims(unit[1])
                if not stripped.strip():
                    continue
                html, h = _math_node(stripped, max_w)
        elif unit[0] == "env":
            html, h = _env_node(unit[1], unit[2], max_w)
        else:  # wrap
            _, env, body, left_glyph, right_glyph = unit
            env_html, env_h = _env_node(env, body, max_w)
            html = ""
            if left_glyph != ".":
                html += _delim_html(left_glyph, env_h * 1.12)
            html += env_html
            if right_glyph != ".":
                html += _delim_html(right_glyph, env_h * 1.12)
            h = env_h
        parts.append(html)
        height = max(height, h)
    if not parts:
        raise MathUnsupported("empty formula")
    return "".join(parts), height


def formula_to_html(tex, display):
    """Render one OCR formula to HTML (vector SVG, assembled table, or raw)."""
    from xml.sax.saxutils import escape
    max_w = PDF_CONTENT_WIDTH_PT * (1.0 if display else 0.9)
    try:
        html, _ = _formula_node(tex, max_w)
    except MathUnsupported:
        html = f'<code class="math-raw">{escape(" ".join(tex.split()))}</code>'
    if display:
        return f'<div class="math-display">{html}</div>'
    return html

