"""In-memory job registry (thread-safe)."""

import shutil
import threading
import time
from dataclasses import dataclass, field, fields


@dataclass
class Job:
    """One conversion job: its progress and its finished outputs."""

    id: str
    name: str
    workdir: str
    created_at: float
    status: str = "queued"  # queued -> converting -> ocr -> pdf -> done | error
    total: int = 0
    done: int = 0
    cached: int = 0
    error: str | None = None
    files: dict = field(default_factory=dict)  # format key -> OutputFile
    images: int = 0
    preview: str = ""
    extra: dict = field(default_factory=dict)  # e.g. mobi_error / pdf_error


_JOB_FIELDS = {f.name for f in fields(Job)}


class JobStore:
    """Thread-safe registry of conversion jobs."""

    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()

    def create(self, job_id, name, workdir):
        job = Job(id=job_id, name=name, workdir=workdir, created_at=time.time())
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id, **fields):
        """Update fields of a job; unknown fields go to job.extra."""
        with self._lock:
            job = self._jobs[job_id]
            for key, value in fields.items():
                if key in _JOB_FIELDS:
                    setattr(job, key, value)
                else:
                    job.extra[key] = value

    def snapshot(self, job_id):
        """The /progress payload for a job, or None if the job is unknown."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "status": job.status,
                "total": job.total,
                "done": job.done,
                "cached": job.cached,
                "error": job.error,
                "name": job.name,
                "formats": sorted(job.files),
                "images": job.images,
                "preview": job.preview,
                "mobi_error": job.extra.get("mobi_error"),
                "pdf_error": job.extra.get("pdf_error"),
            }

    def cleanup(self, max_age):
        """Drop jobs older than max_age seconds and delete their workdirs."""
        cutoff = time.time() - max_age
        with self._lock:
            stale = [jid for jid, job in self._jobs.items()
                     if job.created_at < cutoff]
            removed = [self._jobs.pop(jid) for jid in stale]
        for job in removed:
            shutil.rmtree(job.workdir, ignore_errors=True)
        return removed
