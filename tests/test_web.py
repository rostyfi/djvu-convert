import io
import os

import pytest

from book_converter.config import Settings
from book_converter.formats.base import OutputFile
from book_converter.jobs import JobStore
from book_converter.web import create_app


class StubPipeline:
    """Stands in for ConversionPipeline: finishes the job synchronously."""

    def __init__(self, store):
        self.store = store
        self.calls = []

    def run(self, job_id, workdir, dpi, api_key):
        self.calls.append({"job_id": job_id, "workdir": workdir,
                           "dpi": dpi, "api_key": api_key})
        out_dir = os.path.join(workdir, "out")
        os.makedirs(out_dir, exist_ok=True)
        txt_path = os.path.join(out_dir, "book.txt")
        with open(txt_path, "w") as fh:
            fh.write("converted text")
        self.store.update(job_id, status="done", total=1, done=1,
                          files={"txt": OutputFile(txt_path, "text/plain",
                                                   "book.txt")},
                          preview="converted text")


def make_web(tmp_path, mistral_api_key="env-key"):
    settings = Settings(cache_dir=str(tmp_path / "cache"),
                        mistral_api_key=mistral_api_key)
    store = JobStore()
    pipeline = StubPipeline(store)
    app = create_app(settings=settings, job_store=store, pipeline=pipeline,
                     start_job=lambda *args: pipeline.run(*args))
    app.config["TESTING"] = True
    return app.test_client(), store, pipeline


@pytest.fixture
def web(tmp_path):
    return make_web(tmp_path)


def upload(client, filename="book.djvu", api_key="form-key", dpi="200",
           with_file=True):
    data = {}
    if with_file:
        data["file"] = (io.BytesIO(b"djvu-bytes"), filename)
    if api_key is not None:
        data["api_key"] = api_key
    if dpi is not None:
        data["dpi"] = dpi
    return client.post("/upload", data=data,
                       content_type="multipart/form-data")


def test_index(web):
    client, _, _ = web
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Book Converter" in resp.data


def test_upload_requires_a_file(web):
    client, _, _ = web
    resp = upload(client, with_file=False)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "No file uploaded"


def test_upload_rejects_non_djvu(web):
    client, _, _ = web
    resp = upload(client, filename="book.pdf")
    assert resp.status_code == 400
    assert "djvu" in resp.get_json()["error"]


def test_upload_requires_an_api_key(tmp_path):
    client, _, _ = make_web(tmp_path, mistral_api_key="")
    resp = upload(client, api_key=None)
    assert resp.status_code == 400
    assert "API key" in resp.get_json()["error"]


def test_upload_and_download_flow(web):
    client, store, pipeline = web
    resp = upload(client, filename="My Book.djvu", api_key="form-key",
                  dpi="300")
    assert resp.status_code == 200
    job_id = resp.get_json()["job_id"]

    # the pipeline ran synchronously with the form values
    call = pipeline.calls[0]
    assert call["api_key"] == "form-key"
    assert call["dpi"] == 300

    snap = client.get(f"/progress/{job_id}").get_json()
    assert snap["status"] == "done"
    assert snap["name"] == "My_Book"
    assert snap["formats"] == ["txt"]

    dl = client.get(f"/download/{job_id}/txt")
    assert dl.status_code == 200
    assert dl.data == b"converted text"
    assert dl.mimetype == "text/plain"
    assert "book.txt" in dl.headers["Content-Disposition"]

    assert client.get(f"/download/{job_id}/epub").status_code == 404


def test_env_api_key_is_used(tmp_path):
    client, _, pipeline = make_web(tmp_path, mistral_api_key="env-key")
    resp = upload(client, api_key=None)
    assert resp.status_code == 200
    assert pipeline.calls[0]["api_key"] == "env-key"


def test_invalid_dpi_falls_back_to_200(web):
    client, _, pipeline = web
    resp = upload(client, dpi="999")
    assert resp.status_code == 200
    assert pipeline.calls[0]["dpi"] == 200


def test_progress_unknown_job(web):
    client, _, _ = web
    assert client.get("/progress/nope").status_code == 404


def test_download_unknown_job(web):
    client, _, _ = web
    assert client.get("/download/nope/txt").status_code == 404
