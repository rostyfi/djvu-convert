import pytest

pytest.importorskip("matplotlib")

from book_converter.math.render import formula_to_html


def test_simple_formula_renders_as_svg_image():
    html = formula_to_html("x^2 + y^2 = z^2", display=False)
    assert '<img class="math"' in html
    assert "data:image/svg+xml;base64," in html


def test_normalized_formula_renders():
    html = formula_to_html(r"\tfrac{1}{2}", display=False)
    assert '<img class="math"' in html


def test_display_formula_is_wrapped_in_a_div():
    html = formula_to_html("x", display=True)
    assert html.startswith('<div class="math-display">')
    assert html.endswith("</div>")


def test_unrenderable_formula_falls_back_to_raw_code():
    html = formula_to_html(r"\begin{tikzpicture} x \end{tikzpicture}",
                           display=False)
    assert '<code class="math-raw">' in html
    assert "tikzpicture" in html


def test_matrix_renders_as_table_with_stretched_delimiters():
    html = formula_to_html(r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}",
                           display=True)
    assert '<table class="mgrid">' in html
    assert html.count('class="mdelim"') == 2  # ( ... )
    assert "<td>" in html
