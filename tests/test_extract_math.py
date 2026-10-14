from book_converter.math.extract import extract_math


def test_extract_display_dollar_dollar():
    text, formulas = extract_math("before $$x^2$$ after")
    assert text == "before MATHFORMULA000000PLACEHOLDER after"
    assert formulas == [("x^2", "display")]


def test_extract_bracket_and_paren_math():
    text, formulas = extract_math(r"\[a+b\] and \(c\)")
    assert formulas == [("a+b", "display"), ("c", "inline")]
    assert "MATHFORMULA000000PLACEHOLDER" in text
    assert "MATHFORMULA000001PLACEHOLDER" in text


def test_extract_inline_dollar_math():
    text, formulas = extract_math("the variable $x$ and $y$")
    assert formulas == [("x", "inline"), ("y", "inline")]


def test_dollar_amounts_are_not_math():
    text, formulas = extract_math("It costs $5 and $10 total")
    assert formulas == []
    assert text == "It costs $5 and $10 total"


def test_escaped_dollar_is_not_math():
    text, formulas = extract_math(r"price \$5 and \$x")
    assert formulas == []
    assert text == r"price \$5 and \$x"


def test_empty_formula_is_dropped():
    text, formulas = extract_math("a $$ $$ b")
    assert formulas == []
    assert text == "a  b"  # the empty $$...$$ is replaced by nothing
