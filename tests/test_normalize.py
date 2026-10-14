from book_converter.math.normalize import (
    _balance_braces,
    _find_command,
    _has_row_break,
    _read_group,
    normalize_tex,
)


def test_normalize_tex_renames_commands():
    assert normalize_tex(r"\tfrac{1}{2}") == r"\frac{1}{2}"
    assert normalize_tex(r"\textbf{hi}") == r"\text{hi}"
    assert normalize_tex(r"\gets") == r"\leftarrow"
    assert normalize_tex(r"\euro") == "€"


def test_normalize_tex_strips_and_replaces():
    assert normalize_tex(r"x \label{eq:1} + \ref{eq:1}") == "x + ?"
    assert normalize_tex(r"a \pmod{n} b") == r"a (\mathrm{mod}\ n) b"
    assert normalize_tex(r"\xrightarrow{f}") == r"\overset{f}{\longrightarrow}"


def test_normalize_tex_balances_braces():
    assert normalize_tex(r"\frac{1}{2") == r"\frac{1}{2}"
    assert normalize_tex("x}") == "{x}"


def test_normalize_tex_collapses_whitespace():
    assert normalize_tex("x   +\n  y") == "x + y"


def test_balance_braces():
    assert _balance_braces("{a{b}c") == "{a{b}c}"
    assert _balance_braces("a}b") == "{a}b"
    assert _balance_braces(r"\{") == r"\{"  # escaped brace is not a group
    assert _balance_braces("ok") == "ok"


def test_has_row_break():
    assert _has_row_break(r"a \\ b")
    assert not _has_row_break(r"{\frac{a}{b} \\ c}")  # inside a group
    assert not _has_row_break("no breaks")


def test_read_group():
    assert _read_group("{ab} cd", 0) == ("ab", 4)
    assert _read_group("  {x}", 0) == ("x", 5)
    assert _read_group("no group", 0) == (None, 0)


def test_find_command_matches_whole_words_only():
    assert _find_command(r"\alpha\beta", r"\alpha") == 0
    assert _find_command(r"\alphabet", r"\alpha") == -1
    assert _find_command("none", r"\alpha") == -1
