"""EPUB output format (one chapter per page, images embedded)."""

import os
import uuid
import zipfile

from .base import OutputFile, OutputFormat


class EpubFormat(OutputFormat):
    key = "epub"

    def build(self, ctx):
        epub_path = os.path.join(ctx.out_dir, f"{ctx.name}.epub")
        build_epub(epub_path, ctx.name, ctx.page_markdowns, ctx.image_files)
        ctx.epub_path = epub_path
        return [("epub", OutputFile(epub_path, "application/epub+zip",
                                    f"{ctx.name}.epub"))]


def build_epub(epub_path, title, page_markdowns, image_files):
    """Build an EPUB ebook from per-page markdown and extracted images.

    page_markdowns: one markdown string per page; image references must already
    point to images/<file>. image_files: list of (filename, path on disk).
    """
    try:
        import markdown as md_lib
    except ImportError as exc:
        raise RuntimeError(
            "The 'markdown' package is not installed — run: pip install markdown"
        ) from exc
    from xml.sax.saxutils import escape

    uid = uuid.uuid4().hex
    chapters = []
    for i, text in enumerate(page_markdowns, start=1):
        body = md_lib.markdown(text, extensions=["tables", "fenced_code"])
        xhtml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<!DOCTYPE html>\n"
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            f"<head><title>Page {i}</title></head>\n"
            f"<body>\n{body}\n</body>\n"
            "</html>\n"
        )
        chapters.append((f"chapter-{i:04d}.xhtml", xhtml))

    media_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                   "webp": "image/webp", "gif": "image/gif", "svg": "image/svg+xml"}
    manifest, spine, nav_points = [], [], []
    for i, (fname, _) in enumerate(chapters, start=1):
        cid = f"chapter-{i:04d}"
        manifest.append(f'<item id="{cid}" href="{fname}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{cid}"/>')
        nav_points.append(
            f'<navPoint id="navpoint-{i}" playOrder="{i}">'
            f"<navLabel><text>Page {i}</text></navLabel>"
            f'<content src="{fname}"/></navPoint>'
        )
    for n, (fname, _) in enumerate(image_files, start=1):
        ext = fname.rsplit(".", 1)[-1].lower()
        manifest.append(
            f'<item id="img-{n:04d}" href="images/{fname}" '
            f'media-type="{media_types.get(ext, "image/jpeg")}"/>'
        )

    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"    <dc:title>{escape(title)}</dc:title>\n"
        "    <dc:language>en</dc:language>\n"
        f'    <dc:identifier id="bookid">urn:uuid:{uid}</dc:identifier>\n'
        "  </metadata>\n"
        "  <manifest>\n"
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
        + "\n".join(f"    {item}" for item in manifest) + "\n"
        "  </manifest>\n"
        '  <spine toc="ncx">\n'
        + "\n".join(f"    {item}" for item in spine) + "\n"
        "  </spine>\n"
        "</package>\n"
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        f'  <head><meta name="dtb:uid" content="urn:uuid:{uid}"/></head>\n'
        f"  <docTitle><text>{escape(title)}</text></docTitle>\n"
        "  <navMap>\n"
        + "\n".join(f"    {point}" for point in nav_points) + "\n"
        "  </navMap>\n"
        "</ncx>\n"
    )
    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        "  <rootfiles>\n"
        '    <rootfile full-path="OEBPS/content.opf" '
        'media-type="application/vnd.oasis.opendocument+xml"/>\n'
        "  </rootfiles>\n"
        "</container>\n"
    )

    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                    compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)
        for fname, xhtml in chapters:
            zf.writestr(f"OEBPS/{fname}", xhtml, compress_type=zipfile.ZIP_DEFLATED)
        for fname, fullpath in image_files:
            zf.write(fullpath, f"OEBPS/images/{fname}", compress_type=zipfile.ZIP_DEFLATED)

