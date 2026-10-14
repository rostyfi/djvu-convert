"""Book converter: turn a DJVU book into an ebook using Mistral OCR.

The application lives in the book_converter package; this file is the entry
point (Docker runs `python app.py`) and exposes the Flask `app` object for
WSGI servers.
"""

from book_converter.config import Settings
from book_converter.web import create_app

app = create_app(Settings.from_env())

if __name__ == "__main__":
    from book_converter.cli import main

    main()
