import os
import zipfile

import pytest

from book_converter.formats import (
    DEFAULT_FORMATS,
    ConversionContext,
    EpubFormat,
    MarkdownFormat,
    MobiFormat,
    PdfFormat,
)


def make_ctx(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"pngdata")
    return ConversionContext(
        workdir=str(tmp_path),
        out_dir=str(tmp_path),
        name="book",
        page_markdowns=["# P1\n\n![a](images/p0001-a.png)"],
        image_files=[("p0001-a.png", str(img))],
        markdown="# P1\n\n![a](images/p0001-a.png)",
    )


def test_default_registry_order_and_flags():
    assert [f.key for f in DEFAULT_FORMATS] == ["md", "epub", "pdf", "mobi"]
    assert [f.required for f in DEFAULT_FORMATS] == [True, True, False, False]
    assert PdfFormat.status == "pdf"


def test_markdown_format_writes_md_txt_and_zip(tmp_path):
    ctx = make_ctx(tmp_path)
    outputs = dict(MarkdownFormat().build(ctx))

    assert set(outputs) == {"md", "txt"}
    assert outputs["txt"].mimetype == "text/plain"
    assert outputs["txt"].filename == "book.txt"
    assert open(outputs["txt"].path).read() == "# P1\n\n"  # image embed stripped
    with zipfile.ZipFile(outputs["md"].path) as zf:
        assert zf.namelist() == ["book.md", "images/p0001-a.png"]
        assert zf.read("book.md").decode() == ctx.markdown
        assert zf.read("images/p0001-a.png") == b"pngdata"


def test_epub_format_builds_and_records_epub_path(tmp_path):
    ctx = make_ctx(tmp_path)
    outputs = dict(EpubFormat().build(ctx))

    assert set(outputs) == {"epub"}
    assert outputs["epub"].mimetype == "application/epub+zip"
    assert ctx.epub_path == outputs["epub"].path
    assert os.path.exists(outputs["epub"].path)


def test_mobi_format_requires_epub_first(tmp_path):
    ctx = make_ctx(tmp_path)
    with pytest.raises(RuntimeError, match="EPUB"):
        MobiFormat().build(ctx)


def test_mobi_format_reports_missing_ebook_convert(tmp_path, monkeypatch):
    ctx = make_ctx(tmp_path)
    EpubFormat().build(ctx)
    monkeypatch.setattr("book_converter.formats.mobi.shutil.which",
                        lambda name: None)
    with pytest.raises(RuntimeError, match="ebook-convert"):
        MobiFormat().build(ctx)


def test_pdf_format_delegates_to_build_pdf(tmp_path, monkeypatch):
    import book_converter.formats.pdf as pdf_module

    ctx = make_ctx(tmp_path)
    calls = []

    def fake_build_pdf(pdf_path, title, page_markdowns, base_dir):
        calls.append((pdf_path, title, page_markdowns, base_dir))
        with open(pdf_path, "wb") as fh:
            fh.write(b"%PDF-fake")

    monkeypatch.setattr(pdf_module, "build_pdf", fake_build_pdf)
    outputs = dict(PdfFormat().build(ctx))

    assert outputs["pdf"].mimetype == "application/pdf"
    assert open(outputs["pdf"].path, "rb").read() == b"%PDF-fake"
    assert calls == [(outputs["pdf"].path, "book", ctx.page_markdowns,
                      ctx.out_dir)]
