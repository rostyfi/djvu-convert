import pytest

from book_converter.djvu import djvu_page_images


def test_djvu_page_images_requires_ddjvu(tmp_path, monkeypatch):
    monkeypatch.setattr("book_converter.djvu.shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="ddjvu"):
        djvu_page_images(str(tmp_path / "book.djvu"), str(tmp_path), 200)
