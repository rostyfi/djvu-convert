import time

from book_converter.jobs import JobStore


def test_create_and_get(job_store, tmp_path):
    job = job_store.create("abc", "My Book", str(tmp_path))
    assert job.status == "queued"
    assert job.total == 0
    assert job_store.get("abc") is job
    assert job_store.get("nope") is None


def test_update_known_fields_and_extra(job_store, tmp_path):
    job_store.create("abc", "book", str(tmp_path))
    job_store.update("abc", status="ocr", total=10, done=3)
    job_store.update("abc", mobi_error="boom")
    job = job_store.get("abc")
    assert (job.status, job.total, job.done) == ("ocr", 10, 3)
    assert job.extra == {"mobi_error": "boom"}


def test_snapshot_shape(job_store, tmp_path):
    job_store.create("abc", "book", str(tmp_path))
    job_store.update("abc", status="done", total=2, done=2, cached=1, images=3,
                     preview="prev", files={"epub": object(), "txt": object()},
                     pdf_error="no weasyprint")
    snap = job_store.snapshot("abc")
    assert snap == {
        "status": "done",
        "total": 2,
        "done": 2,
        "cached": 1,
        "error": None,
        "name": "book",
        "formats": ["epub", "txt"],
        "images": 3,
        "preview": "prev",
        "mobi_error": None,
        "pdf_error": "no weasyprint",
    }
    assert job_store.snapshot("nope") is None


def test_cleanup_removes_stale_jobs_and_their_workdirs(job_store, tmp_path):
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()
    (old_dir / "f").write_text("x")
    job_store.create("old", "old", str(old_dir))
    job_store.create("new", "new", str(new_dir))
    job_store.update("old", created_at=time.time() - 10000)

    removed = job_store.cleanup(max_age=3600)

    assert [j.id for j in removed] == ["old"]
    assert not old_dir.exists()
    assert new_dir.exists()
    assert job_store.get("old") is None
    assert job_store.get("new") is not None
