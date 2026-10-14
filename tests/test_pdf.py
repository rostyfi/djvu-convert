import pytest

pytest.importorskip("weasyprint")

from book_converter.formats.pdf import build_pdf


def test_build_pdf_end_to_end(tmp_path):
    pdf = tmp_path / "book.pdf"
    build_pdf(str(pdf), "Test Book", [
        "# Chapter 1\n\nText with a formula $$E = mc^2$$ inline.",
        "A matrix:\n\n$$\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$$",
    ], str(tmp_path))
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert pdf.stat().st_size > 1000
