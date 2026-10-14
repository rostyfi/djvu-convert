"""Flask web app: upload a DJVU, poll progress, download the results."""

import os
import shutil
import tempfile
import threading
import uuid

from flask import Flask, Response, jsonify, render_template, request

from ..cache import PageCache
from ..config import PROJECT_ROOT, Settings
from ..jobs import JobStore
from ..ocr import OcrClient
from ..pipeline import ConversionPipeline
from ..text import sanitize_book_name


def create_app(settings=None, job_store=None, pipeline=None, start_job=None):
    """Application factory.

    settings / job_store / pipeline can be injected (tests do this);
    start_job defaults to running the pipeline in a daemon thread.
    """
    settings = settings or Settings.from_env()
    job_store = job_store or JobStore()
    pipeline = pipeline or ConversionPipeline(
        settings, job_store,
        ocr_client=OcrClient(settings.ocr_url, settings.ocr_model,
                             settings.ocr_retries),
        page_cache=PageCache(settings.cache_dir, settings.ocr_model),
    )

    app = Flask(__name__, template_folder=str(PROJECT_ROOT / "templates"))
    app.config["MAX_CONTENT_LENGTH"] = settings.max_content_length

    if start_job is None:
        def start_job(job_id, workdir, dpi, api_key):
            threading.Thread(target=pipeline.run,
                             args=(job_id, workdir, dpi, api_key),
                             daemon=True).start()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/upload")
    def upload():
        job_store.cleanup(settings.job_max_age)
        file = request.files.get("file")
        if file is None or not file.filename:
            return jsonify({"error": "No file uploaded"}), 400
        if not file.filename.lower().endswith(".djvu"):
            return jsonify({"error": "Only .djvu files are supported"}), 400
        api_key = (request.form.get("api_key") or "").strip() \
            or settings.mistral_api_key
        if not api_key:
            return jsonify({"error": "No Mistral API key — paste it above or set MISTRAL_API_KEY"}), 400
        try:
            dpi = int(request.form.get("dpi", "200"))
        except ValueError:
            dpi = 200
        if dpi not in (150, 200, 300):
            dpi = 200

        name = sanitize_book_name(file.filename)
        job_id = uuid.uuid4().hex[:12]
        workdir = tempfile.mkdtemp(prefix=f"bookconv-{job_id}-")
        try:
            file.save(os.path.join(workdir, "book.djvu"))
        except Exception:
            shutil.rmtree(workdir, ignore_errors=True)
            raise

        job_store.create(job_id, name, workdir)
        start_job(job_id, workdir, dpi, api_key)
        return jsonify({"job_id": job_id})

    @app.get("/progress/<job_id>")
    def progress(job_id):
        snap = job_store.snapshot(job_id)
        if snap is None:
            return jsonify({"error": "Unknown job"}), 404
        return jsonify(snap)

    @app.get("/download/<job_id>/<fmt>")
    def download(job_id, fmt):
        job = job_store.get(job_id)
        entry = job.files.get(fmt) if job else None
        if not entry or not os.path.exists(entry.path):
            return jsonify({"error": "Result not ready"}), 404
        with open(entry.path, "rb") as fh:
            data = fh.read()
        return Response(
            data,
            mimetype=entry.mimetype,
            headers={"Content-Disposition": f'attachment; filename="{entry.filename}"'},
        )

    return app
