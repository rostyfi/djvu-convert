"""LaTeX environment parsing: matrices, cases, align-like environments.

Environments are classified (matrix / cases / align / wrapper / unrenderable)
and split into rows and cells, so render.py can assemble them as HTML tables
of individually rendered cells.
"""

import re

from .exceptions import MathUnsupported


_MATRIX_ENVS = {
    "matrix", "matrix*", "pmatrix", "pmatrix*", "bmatrix", "bmatrix*",
    "Bmatrix", "Bmatrix*", "vmatrix", "vmatrix*", "Vmatrix", "Vmatrix*",
    "smallmatrix", "psmallmatrix", "dsmallmatrix",
    "array", "darray", "subarray", "tabular", "tabular*", "longtable",
}
_CASES_ENVS = {"cases", "dcases", "dcases*", "rcases", "numcases", "subnumcases"}
_ALIGN_ENVS = {
    "align", "align*", "aligned", "split", "eqnarray", "eqnarray*",
    "flalign", "flalign*", "alignat", "alignedat", "IEEEeqnarray", "empheq",
    "gather", "gather*", "gathered", "multline", "multline*", "dmath", "multlined",
}
_CENTERED_ALIGN_ENVS = {"gather", "gather*", "gathered", "multline", "multline*",
                        "dmath", "multlined"}
_WRAPPER_ENVS = {
    "equation", "equation*", "displaymath", "math", "subequations", "fleqn",
    "theorem", "theorem*", "lemma", "proposition", "corollary", "definition",
    "example", "remark", "proof", "claim", "fact", "axiom", "conjecture",
    "hypothesis", "notation", "problem", "exercise", "solution", "answer",
    "summary", "figure", "figure*", "table", "table*", "center", "flushleft",
    "flushright", "quote", "quotation", "verse", "abstract", "itemize",
    "enumerate", "description", "document", "frame", "block", "columns",
    "semiverbatim", "minipage", "multicols",
}
_UNRENDERABLE_ENVS = {
    "tikzpicture", "tikzcd", "CD", "pgfpicture", "pgfplot", "pgfplots", "axis",
    "xymatrix", "xy", "asy", "asydef", "chemfig", "forest", "circuitikz",
    "picture", "pspicture", "lstlisting", "minted", "algorithm", "algorithmic",
    "verbatim", "Verbatim", "comment", "filecontents", "thebibliography",
    "wrapfigure", "subfigure", "sidewaysfigure", "landscape", "appendix",
    "titlepage", "keywords", "letter", "raw", "alltt", "BVerbatim", "LVerbatim",
    "FVerbatim", "SaveVerbatim", "screen", "exampleblock", "alertblock", "column",
    "only", "structure", "plain",
}
_ENV_DELIMS = {
    "pmatrix": ("(", ")"), "pmatrix*": ("(", ")"),
    "bmatrix": ("[", "]"), "bmatrix*": ("[", "]"),
    "Bmatrix": (r"\{", r"\}"), "Bmatrix*": (r"\{", r"\}"),
    "vmatrix": ("|", "|"), "vmatrix*": ("|", "|"),
    "Vmatrix": (r"\|", r"\|"), "Vmatrix*": (r"\|", r"\|"),
    "cases": (r"\{", None), "dcases": (r"\{", None), "dcases*": (r"\{", None),
    "rcases": (r"\{", None), "numcases": (r"\{", None), "subnumcases": (r"\{", None),
}
_ENV_NARGS = {
    "array": 1, "darray": 1, "subarray": 1, "tabular": 1, "tabular*": 2,
    "longtable": 1, "alignat": 1, "alignedat": 1, "IEEEeqnarray": 1,
    "numcases": 1, "subnumcases": 1, "empheq": 1, "multicols": 1,
    "minipage": 1, "thebibliography": 1, "list": 2, "wrapfigure": 3,
}
_ENV_KNOWN = _MATRIX_ENVS | _CASES_ENVS | _ALIGN_ENVS | _WRAPPER_ENVS

_BEGIN_RE = re.compile(r"\\begin\{([a-zA-Z*]+)\}")


def _skip_env(tex, i):
    """If a \\begin{env} starts at i, return the position after its matching
    \\end{env} (counting same-name nesting); otherwise return i unchanged."""
    m = _BEGIN_RE.match(tex, i)
    if not m:
        return i
    env = m.group(1)
    begin = re.compile(r"\\begin\{" + re.escape(env) + r"\}")
    end = re.compile(r"\\end\{" + re.escape(env) + r"\}")
    depth = 1
    pos = m.end()
    while True:
        m_end = end.search(tex, pos)
        m_begin = begin.search(tex, pos)
        if m_begin and (m_end is None or m_begin.start() < m_end.start()):
            depth += 1
            pos = m_begin.end()
        elif m_end is not None:
            depth -= 1
            if depth == 0:
                return m_end.end()
            pos = m_end.end()
        else:
            return len(tex)  # unbalanced — swallow the rest


def _split_env_segments(tex):
    """Split a formula into plain-text and environment segments.

    Yields (text, env, body): env is None for plain math text. Wrapper
    environments are flattened into the parent (recursively).
    """
    pos = 0
    while True:
        m = _BEGIN_RE.search(tex, pos)
        if not m:
            if tex[pos:].strip():
                yield tex[pos:], None, None
            return
        if tex[pos:m.start()].strip():
            yield tex[pos:m.start()], None, None
        env = m.group(1)
        if env in _UNRENDERABLE_ENVS or env not in _ENV_KNOWN:
            raise MathUnsupported(f"unsupported environment: {env}")
        body, end = _extract_env_body(tex, _parse_env_args(tex, m.end(), env), env)
        if env in _WRAPPER_ENVS:
            yield from _split_env_segments(body)
        else:
            yield "", env, body
        pos = end


def _parse_env_args(tex, pos, env):
    """Consume the argument groups of \\begin{env}; return the new position."""
    consumed = 0
    while consumed < _ENV_NARGS.get(env, 0):
        _, pos_opt = _read_opt_group(tex, pos)
        if pos_opt > pos:
            pos = pos_opt
            continue
        content, pos_req = _read_group(tex, pos)
        if content is not None:
            pos = pos_req
            consumed += 1
        else:
            break
    return pos


def _extract_env_body(tex, pos, env):
    """Return (body, end_pos) of the environment whose content starts at pos."""
    begin = re.compile(r"\\begin\{" + re.escape(env) + r"\}")
    end = re.compile(r"\\end\{" + re.escape(env) + r"\}")
    depth = 1
    i = pos
    while True:
        m_end = end.search(tex, i)
        m_begin = begin.search(tex, i)
        if m_begin and (m_end is None or m_begin.start() < m_end.start()):
            depth += 1
            i = m_begin.end()
        elif m_end is not None:
            depth -= 1
            if depth == 0:
                return tex[pos:m_end.start()], m_end.end()
            i = m_end.end()
        else:
            raise MathUnsupported(f"unbalanced environment: {env}")


def _split_rows(body):
    """Split an environment body into rows on top-level \\\\ (with [..] args).

    Nested \\begin{...}...\\end{...} spans are skipped, so & and \\\\ inside a
    nested environment do not split the outer one.
    """
    rows = []
    depth = 0
    start = 0
    i = 0
    while i < len(body):
        i = _skip_env(body, i)
        if i >= len(body):
            break
        c = body[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        elif c == "\\" and depth == 0 and i + 1 < len(body) and body[i + 1] == "\\":
            rows.append(body[start:i])
            i += 2
            j = i
            while j < len(body) and body[j].isspace():
                j += 1
            if j < len(body) and body[j] == "[":
                k = body.find("]", j)
                if k != -1:
                    i = k + 1
            start = i
            continue
        i += 1
    rows.append(body[start:])
    while len(rows) > 1 and not rows[-1].strip():
        rows.pop()
    return rows


def _split_cells(row):
    """Split a row into cells on top-level & (outside any group or env)."""
    cells = []
    depth = 0
    start = 0
    i = 0
    while i < len(row):
        i = _skip_env(row, i)
        if i >= len(row):
            break
        c = row[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        elif c == "&" and depth == 0:
            cells.append(row[start:i])
            start = i + 1
        i += 1
    cells.append(row[start:])
    return cells

