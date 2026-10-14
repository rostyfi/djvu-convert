"""The conversion pipeline: DJVU -> page images -> OCR -> output formats."""

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

from .djvu import djvu_page_images
from .formats import DEFAULT_FORMATS, ConversionContext


class ConversionPipeline:
    """Runs one conversion job end to end.

    All dependencies are injected, so tests can substitute fakes (OCR
    client, page renderer, cache, output formats).
    """

    def __init__(self, settings, job_store, ocr_client, page_cache,
                 formats=None, page_renderer=djvu_page_images):
        self.settings = settings
        self.job_store = job_store
        self.ocr_client = ocr_client
        self.page_cache = page_cache
        self.formats = DEFAULT_FORMATS if formats is None else formats
        self.page_renderer = page_renderer

    def run(self, job_id, workdir, dpi, api_key):
        """Convert the DJVU at workdir/book.djvu and update the job record."""
        pages_dir = os.path.join(workdir, "pages")
        os.makedirs(pages_dir, exist_ok=True)
        try:
            self.job_store.update(job_id, status="converting")
            pages = self.page_renderer(os.path.join(workdir, "book.djvu"),
                                       pages_dir, dpi)
            total = len(pages)
            self.job_store.update(job_id, status="ocr", total=total, done=0,
                                  cached=0)

            page_results = [None] * total  # (markdown, images) per page
            cancel = threading.Event()
            counters = {"done": 0, "cached": 0}
            count_lock = threading.Lock()

            def ocr_one(index):
                if cancel.is_set():
                    raise RuntimeError("Cancelled: an earlier page failed")
                cached = self.page_cache.lookup(pages[index])
                if cached is not None:
                    page_results[index] = cached
                    with count_lock:
                        counters["cached"] += 1
                        self.job_store.update(job_id,
                                              cached=counters["cached"])
                else:
                    page_results[index] = self.ocr_client.ocr_page(
                        api_key, pages[index])
                    self.page_cache.store(pages[index], page_results[index])
                with count_lock:
                    counters["done"] += 1
                    self.job_store.update(job_id, done=counters["done"])

            pool = ThreadPoolExecutor(max_workers=self.settings.ocr_workers)
            try:
                futures = [pool.submit(ocr_one, i) for i in range(total)]
                for future in futures:
                    future.result()
            except Exception:
                cancel.set()
                raise
            finally:
                pool.shutdown(wait=True, cancel_futures=True)

            name = self.job_store.get(job_id).name
            out_dir = os.path.join(workdir, "out")
            images_dir = os.path.join(out_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            page_markdowns = []
            image_files = []  # (filename, path on disk)
            for page_no, (text, images) in enumerate(page_results, start=1):
                for img in images:
                    stem = os.path.splitext(img["safe_id"])[0] \
                        or f"img-{len(image_files)}"
                    fname = f"p{page_no:04d}-{stem}.{img['ext']}"
                    fullpath = os.path.join(images_dir, fname)
                    with open(fullpath, "wb") as fh:
                        fh.write(img["data"])
                    image_files.append((fname, fullpath))
                    text = text.replace(
                        f"![{img['id']}]({img['id']})",
                        f"![{img['id']}](images/{fname})",
                    )
                page_markdowns.append(text)

            markdown = "\n\n---\n\n".join(
                f"<!-- Page {i} -->\n\n{page_markdowns[i - 1].strip()}"
                for i in range(1, total + 1)
            )

            ctx = ConversionContext(
                workdir=workdir, out_dir=out_dir, name=name,
                page_markdowns=page_markdowns, image_files=image_files,
                markdown=markdown,
            )
            files = {}
            errors = {}
            for output_format in self.formats:
                if output_format.status:
                    self.job_store.update(job_id, status=output_format.status)
                try:
                    for key, output in output_format.build(ctx):
                        files[key] = output
                except Exception as exc:
                    if output_format.required:
                        raise
                    errors[f"{output_format.key}_error"] = str(exc)

            shutil.rmtree(pages_dir, ignore_errors=True)   # page renders are the big part
            shutil.rmtree(images_dir, ignore_errors=True)  # images live inside the outputs
            self.job_store.update(job_id, status="done", images=len(image_files),
                                  preview=markdown[:2000], files=files,
                                  cached=counters["cached"], **errors)
        except Exception as exc:
            self.job_store.update(job_id, status="error", error=str(exc))
