import xml.etree.ElementTree as ET
import zipfile

from book_converter.formats.epub import build_epub


def test_build_epub_structure(tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n-fake")
    epub = tmp_path / "book.epub"

    build_epub(str(epub), "My Book",
               ["# Page 1\n\nHello ![a](images/pic.png)", "Page two text"],
               [("pic.png", str(img))])

    with zipfile.ZipFile(epub) as zf:
        names = zf.namelist()
        # mimetype must be the first entry, stored uncompressed
        assert names[0] == "mimetype"
        assert zf.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"
        assert "META-INF/container.xml" in names

        opf = zf.read("OEBPS/content.opf").decode()
        assert "<dc:title>My Book</dc:title>" in opf
        assert 'href="chapter-0001.xhtml"' in opf
        assert 'href="chapter-0002.xhtml"' in opf
        assert 'href="images/pic.png"' in opf
        assert opf.count("<itemref ") == 2

        chapter = zf.read("OEBPS/chapter-0001.xhtml").decode()
        assert "<h1>Page 1</h1>" in chapter
        assert 'src="images/pic.png"' in chapter
        assert zf.read("OEBPS/images/pic.png") == b"\x89PNG\r\n\x1a\n-fake"

        # all XML payloads are well-formed
        ET.fromstring(opf)
        ET.fromstring(zf.read("OEBPS/toc.ncx").decode())
        ET.fromstring(chapter)
        ET.fromstring(zf.read("META-INF/container.xml").decode())


def test_build_epub_escapes_title(tmp_path):
    epub = tmp_path / "book.epub"
    build_epub(str(epub), "A <B> & \"C\"", ["text"], [])
    with zipfile.ZipFile(epub) as zf:
        opf = zf.read("OEBPS/content.opf").decode()
    assert "A &lt;B&gt; &amp; \"C\"" in opf
