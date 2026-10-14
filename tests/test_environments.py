import pytest

from book_converter.math.environments import (
    _skip_env,
    _split_cells,
    _split_env_segments,
    _split_rows,
)
from book_converter.math.exceptions import MathUnsupported


def test_split_rows_ignores_breaks_inside_nested_environments():
    body = r"a & b \\ c & d \\ \begin{matrix} x \\ y \end{matrix} \\ e"
    rows = _split_rows(body)
    assert [r.strip() for r in rows] == [
        "a & b", "c & d", r"\begin{matrix} x \\ y \end{matrix}", "e",
    ]


def test_split_rows_drops_trailing_empty_row():
    assert _split_rows(r"a \\ b \\ ") == ["a ", " b "]


def test_split_cells_ignores_ampersands_inside_groups():
    assert _split_cells(r"a & b & {c & d}") == ["a ", " b ", " {c & d}"]
    assert _split_cells("single") == ["single"]


def test_skip_env_handles_nesting():
    tex = r"\begin{matrix} \begin{matrix} a \end{matrix} b \end{matrix} tail"
    assert tex[_skip_env(tex, 0):] == " tail"
    assert _skip_env("no env here", 0) == 0


def test_split_env_segments_flattens_wrapper_environments():
    tex = r"\begin{equation} x + \begin{pmatrix} a \\ b \end{pmatrix} \end{equation}"
    segments = list(_split_env_segments(tex))
    assert segments == [(" x + ", None, None), ("", "pmatrix", r" a \\ b ")]


def test_split_env_segments_rejects_unrenderable_environments():
    with pytest.raises(MathUnsupported, match="tikzpicture"):
        list(_split_env_segments(r"\begin{tikzpicture} x \end{tikzpicture}"))


def test_split_env_segments_rejects_unbalanced_environments():
    with pytest.raises(MathUnsupported, match="unbalanced"):
        list(_split_env_segments(r"\begin{matrix} a \\ b"))
