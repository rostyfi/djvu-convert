import os
import zipfile

from book_converter.formats import EpubFormat, MarkdownFormat
from book_converter.formats.base import OutputFormat
from book_converter.pipeline import ConversionPipeline
from fakes import FakeOcrClient, make_png

IMAGE = {"id": "img-1", "safe_id": "img-1", "ext": "png", "data": b"imagedata"}


def make_pipeline(tmp_path, settings, job_store, ocr_client, page_cache,
                  formats, num_pages=3):
    def page_renderer(djvu_path, out_dir, dpi):
        os.makedirs(out_dir, exist_ok=True)
        return [make_png(os.path.join(out_dir, f"page-{i:04d}.png"))
                for i in range(1, num_pages + 1)]

    return ConversionPipeline(settings, job_store, ocr_client, page_cache,
                              formats=formats, page_renderer=page_renderer)


def run_pipeline(tmp_path, settings, job_store, ocr_client, page_cache,
                 formats=None, num_pages=3, job_id="job1"):
    if formats is None:
        formats = [MarkdownFormat(), EpubFormat()]
    pipeline = make_pipeline(tmp_path, settings, job_store, ocr_client,
                             page_cache, formats, num_pages)
    workdir = tmp_path / f"work-{job_id}"
    workdir.mkdir()
    (workdir / "book.djvu").write_bytes(b"djvu")
    job_store.create(job_id, "book", str(workdir))
    pipeline.run(job_id, str(workdir), 200, "api-key")
    return job_store.get(job_id), workdir


def test_pipeline_end_to_end(tmp_path, settings, job_store, page_cache):
    ocr = FakeOcrClient(result=("# Page\n\nSome text.\n\n![img-1](img-1)",
                                [IMAGE]))
    job, workdir = run_pipeline(tmp_path, settings, job_store, ocr, page_cache)

    assert job.status == "done"
    assert job.total == 3
    assert job.done == 3
    assert job.cached == 0
    assert job.images == 3
    assert set(job.files) == {"md", "txt", "epub"}
    # image references rewritten to the extracted files
    assert "![img-1](images/p0001-img-1.png)" in job.preview
    # outputs are real files with the right content
    with zipfile.ZipFile(job.files["epub"].path) as zf:
        assert "OEBPS/images/p0001-img-1.png" in zf.namelist()
    with zipfile.ZipFile(job.files["md"].path) as zf:
        assert "images/p0001-img-1.png" in zf.namelist()
    txt = open(job.files["txt"].path).read()
    assert "Some text." in txt
    assert "![" not in txt
    # intermediate dirs are cleaned up
    assert not (workdir / "pages").exists()
    assert not (workdir / "out" / "images").exists()
    # every page was OCR'd with the api key
    assert [c[0] for c in ocr.calls] == ["api-key"] * 3


def test_pipeline_uses_cache_on_second_run(tmp_path, settings, job_store,
                                           page_cache):
    formats = [MarkdownFormat(), EpubFormat()]
    ocr = FakeOcrClient()
    run_pipeline(tmp_path, settings, job_store, ocr, page_cache,
                 formats=formats, job_id="job1")
    assert job_store.get("job1").cached == 0
    assert len(ocr.calls) == 3

    ocr2 = FakeOcrClient()
    job2, _ = run_pipeline(tmp_path, settings, job_store, ocr2, page_cache,
                           formats=formats, job_id="job2")

    assert job2.status == "done"
    assert job2.cached == 3
    assert ocr2.calls == []


def test_pipeline_ocr_failure_marks_job_error(tmp_path, settings, job_store,
                                              page_cache):
    ocr = FakeOcrClient(error=RuntimeError("OCR down"))
    job, _ = run_pipeline(tmp_path, settings, job_store, ocr, page_cache)
    assert job.status == "error"
    assert "OCR down" in job.error


def test_pipeline_optional_format_failure_is_captured(tmp_path, settings,
                                                      job_store, page_cache):
    class BrokenFormat(OutputFormat):
        key = "pdf"
        required = False
        status = "pdf"

        def __init__(self):
            self.status_seen = None

        def build(self, ctx):
            self.status_seen = job_store.get("job1").status
            raise RuntimeError("no weasyprint")

    broken = BrokenFormat()
    job, _ = run_pipeline(tmp_path, settings, job_store, FakeOcrClient(),
                          page_cache,
                          formats=[MarkdownFormat(), EpubFormat(), broken])

    assert job.status == "done"
    assert "pdf" not in job.files
    assert job.extra["pdf_error"] == "no weasyprint"
    assert broken.status_seen == "pdf"  # the status was set before building
    snap = job_store.snapshot("job1")
    assert snap["formats"] == ["epub", "md", "txt"]
    assert snap["pdf_error"] == "no weasyprint"


def test_pipeline_required_format_failure_fails_the_job(tmp_path, settings,
                                                        job_store, page_cache):
    class BrokenFormat(OutputFormat):
        key = "epub"
        required = True

        def build(self, ctx):
            raise RuntimeError("epub broken")

    job, _ = run_pipeline(tmp_path, settings, job_store, FakeOcrClient(),
                          page_cache,
                          formats=[MarkdownFormat(), BrokenFormat()])

    assert job.status == "error"
    assert "epub broken" in job.error
