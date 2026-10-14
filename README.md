# Book Converter

Turn a DJVU book into an ebook using Mistral OCR. Upload the file in a small
web UI, pick a DPI, and download the result as EPUB, PDF, MOBI or Markdown —
LaTeX formulas are rendered as vector SVGs in the PDF output.

## Features

- Page-by-page OCR with the Mistral API (parallel workers, automatic retries)
- Content-addressed OCR page cache: re-uploading the same book at the same DPI
  never re-bills the API for pages already seen
- Output formats: EPUB (ebook, with images), PDF (print-ready, formulas
  rendered), MOBI (Kindle), Markdown + images (zip)
- Everything bundled in a Docker image (Python, djvulibre, calibre, weasyprint)

## Run with Docker (recommended)

Everything (Python, djvulibre, calibre, the web app) is packaged in the image —
one command:

```bash
./run.sh
```

`run.sh` runs `docker compose up --build` with `MISTRAL_API_KEY` loaded from
`.env` — create it once with `echo 'MISTRAL_API_KEY=sk-...' > .env` (it is
gitignored, so it never gets committed). Add `-d` to run detached. Then open
http://127.0.0.1:5000.

`run.sh` also creates `./cache` (the OCR-cache bind mount) if it is missing.
The Docker daemon would otherwise try to create it as root, which fails on
NFS shares with root squashing. If you run compose directly, create it first:

```bash
mkdir -p cache && chmod 1777 cache
```

Manual equivalents:

```bash
docker compose up --build                          # then paste the key in the form
MISTRAL_API_KEY=sk-... docker compose up --build   # or pass it to the container
```

Without compose:

```bash
docker build -t book-converter .
docker run --rm -p 5000:5000 -e MISTRAL_API_KEY=sk-... book-converter
```

## Run without Docker

Install the system dependencies — djvulibre renders the DJVU pages, calibre
builds the MOBI from the EPUB, weasyprint renders the PDF — then the Python
requirements:

```bash
#   Debian/Ubuntu: sudo apt-get install djvulibre-bin calibre
#   macOS: brew install djvulibre && brew install --cask calibre
#          (weasyprint wheels bundle their own Pango on macOS)
pip install -r requirements.txt
export MISTRAL_API_KEY=sk-...          # or paste the key into the web form
python3 app.py
```

Open http://127.0.0.1:5000. To expose the app on your network, set
`HOST=0.0.0.0` (and `PORT` to change the port).

## How it works

Upload a `.djvu` and the app renders each page with `ddjvu` at the chosen DPI
(150/200/300), sends the pages to Mistral OCR (4 in parallel, with retries),
then builds the outputs: Markdown + images, EPUB, PDF (LaTeX formulas rendered
as vector SVGs) and MOBI (built from the EPUB with calibre). Page renders and
intermediate images are deleted once the outputs are ready.

- The OCR cache is keyed by a hash of the rendered page image
  and the OCR model. Re-uploading the same book at the same DPI skips the
  Mistral API for every page already seen — you only pay for new or changed
  pages. The cache lives in `./cache` (override with the `CACHE_DIR`
  environment variable); under Docker it is a mounted volume, so it survives
  container rebuilds and restarts. Delete the directory to clear it.
- Jobs live in memory for 2 hours; page images are deleted as soon as the
  outputs are ready. Restarting the app clears all jobs (in Docker: container
  restart clears them). The OCR cache is not affected by this.
- An API key pasted into the form is used only for that conversion and is never
  stored. The key in `.env` is stored in plaintext in that file (gitignored,
  and excluded from the docker build context via `.dockerignore`).
- Environment variables: `MISTRAL_API_KEY` (API key), `HOST`/`PORT` (bind
  address, default `0.0.0.0:5000` in Docker, `127.0.0.1:5000` otherwise),
  `OCR_URL` (override the Mistral OCR endpoint, e.g. for testing),
  `CACHE_DIR` (OCR cache location, default `./cache` next to `app.py`).
  `OCR_MODEL`, `OCR_WORKERS`, `OCR_RETRIES` and `JOB_MAX_AGE` are honored too
  (see `book_converter/config.py`).

## Project layout

```
app.py                  # entry point (Docker runs `python app.py`)
book_converter/         # the application package
  cache.py              # content-addressed OCR page cache
  cli.py                # app entry (`python app.py` / `python -m book_converter`)
  config.py             # settings read from the environment
  djvu.py               # renders DJVU pages with ddjvu
  jobs.py               # in-memory job store
  ocr.py                # Mistral OCR client
  pipeline.py           # DJVU -> page images -> OCR -> output formats
  text.py               # book-name sanitizing
  math/                 # LaTeX formula extraction, normalization, SVG rendering
  formats/              # output formats: markdown, epub, pdf, mobi
  web/                  # Flask app (upload, progress, download)
templates/index.html    # the upload form
tests/                  # pytest suite (fakes.py stubs the OCR client)
run.sh                  # docker compose up --build (loads the key from .env)
docker-compose.yml      # the service definition
Dockerfile              # python:3.12-slim + calibre + djvulibre + weasyprint
cache/                  # OCR page cache (created on first run)
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
