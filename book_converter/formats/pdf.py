r"""PDF output format: print-ready A5, formulas rendered as vector graphics.

Mistral OCR emits formulas as LaTeX inside the markdown (\(...\), \[...\],
$$...$$, sometimes $...$). Each formula is rendered to a vector SVG with
matplotlib's mathtext engine and embedded in a print-styled HTML document
that WeasyPrint turns into an A5 PDF. See book_converter/math/.
"""

import os
import threading

from ..math.extract import page_to_html
from .base import OutputFile, OutputFormat

# matplotlib's mathtext engine and WeasyPrint are not thread-safe; the app can
# run several conversion jobs concurrently, so the whole PDF phase is serialized.
_PDF_LOCK = threading.Lock()


PDF_CSS = """
@page {
  size: A5;
  margin: 20mm 18mm 18mm 18mm;
  @bottom-center {
    content: counter(page);
    font-family: "DejaVu Serif", serif;
    font-size: 8pt;
    color: #777;
  }
}
@page :first { @bottom-center { content: none; } }
body {
  font-family: "DejaVu Serif", serif;
  font-size: 10.5pt;
  line-height: 1.45;
  text-align: justify;
  hyphens: auto;
  color: #111;
}
section.titlepage { page-break-after: always; text-align: center; margin-top: 45mm; }
section.titlepage h1 { font-size: 26pt; margin: 0 0 0.4em; }
section.titlepage p { color: #555; font-size: 11pt; }
section.page { page-break-before: always; }
h1, h2, h3, h4 { text-align: left; line-height: 1.25; page-break-after: avoid; }
h1 { font-size: 17pt; }
h2 { font-size: 14pt; }
h3 { font-size: 12pt; }
h4 { font-size: 11pt; }
p { margin: 0 0 0.55em; orphans: 2; widows: 2; }
img { max-width: 100%; page-break-inside: avoid; }
ul, ol { margin: 0 0 0.55em; padding-left: 1.4em; }
li { margin: 0 0 0.2em; }
blockquote { margin: 0.6em 1.5em; }
hr { border: 0; border-top: 1px solid #999; margin: 1em 0; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; }
pre {
  font-family: "DejaVu Sans Mono", monospace; font-size: 8.5pt;
  background: #f6f6f6; padding: 0.6em; white-space: pre-wrap;
}
pre code { font-size: inherit; background: none; padding: 0; }
code.math-raw { background: #f6f6f6; padding: 0 3px; font-size: 8.5pt; }
table { border-collapse: collapse; margin: 0.8em auto; max-width: 100%; page-break-inside: avoid; }
th, td { border: 1px solid #999; padding: 3px 8px; text-align: left; }
div.math-display { text-align: center; margin: 0.9em 0; page-break-inside: avoid; }
span.mwrap { white-space: nowrap; }
table.mgrid { display: inline-table; border-collapse: collapse; vertical-align: middle; margin: 0 0.12em; }
table.mgrid td { border: 0; padding: 0.05em 0.35em; text-align: center; line-height: 1; }
table.mgrid td.al-r { text-align: right; }
table.mgrid td.al-l { text-align: left; }
img.mdelim { vertical-align: middle; margin: 0 0.04em; }
"""



class PdfFormat(OutputFormat):
    key = "pdf"
    required = False  # best-effort — never fail the whole job
    status = "pdf"    # progress status shown while rendering

    def build(self, ctx):
        pdf_path = os.path.join(ctx.out_dir, f"{ctx.name}.pdf")
        build_pdf(pdf_path, ctx.name, ctx.page_markdowns, ctx.out_dir)
        return [("pdf", OutputFile(pdf_path, "application/pdf",
                                   f"{ctx.name}.pdf"))]


def build_pdf(pdf_path, title, page_markdowns, base_dir):
    """Build a print-ready A5 PDF from per-page markdown.

    Formulas are rendered as vector graphics; images are referenced relative
    to base_dir (the markdown already points at images/<file>).
    """
    try:
        from weasyprint import HTML as WeasyHTML
    except ImportError as exc:
        raise RuntimeError(
            "The 'weasyprint' package is not installed — run: pip install weasyprint "
            "(needed for the PDF output)"
        ) from exc
    try:
        import markdown as md_lib
    except ImportError as exc:
        raise RuntimeError(
            "The 'markdown' package is not installed — run: pip install markdown"
        ) from exc
    from xml.sax.saxutils import escape

    with _PDF_LOCK:
        sections = [
            '<section class="titlepage">'
            f"<h1>{escape(title)}</h1>"
            "<p>Converted from DJVU with Mistral OCR</p>"
            "</section>"
        ]
        for text in page_markdowns:
            sections.append(f'<section class="page">\n{page_to_html(text, md_lib)}\n</section>')
        html = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f"<title>{escape(title)}</title>\n"
            f"<style>{PDF_CSS}</style>\n"
            "</head>\n<body>\n" + "\n".join(sections) + "\n</body>\n</html>\n"
        )
        WeasyHTML(string=html, base_url=base_dir).write_pdf(pdf_path)
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise RuntimeError("weasyprint finished but produced no output file")

