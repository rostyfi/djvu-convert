"""OCR page cache: content-addressed per-page results.

The key is a hash of the rendered page image plus the OCR model, so
re-processing the same book at the same DPI reuses the stored
markdown/images instead of calling Mistral.
"""

import hashlib
import json
import os


class PageCache:
    """Filesystem cache for per-page OCR results. Best-effort: any read or
    write problem counts as a miss / is ignored."""

    def __init__(self, cache_dir, model):
        self.cache_dir = cache_dir
        self.model = model

    def _key(self, image_path):
        """SHA-256 over the OCR model name and the page image bytes."""
        h = hashlib.sha256()
        h.update(self.model.encode("utf-8"))
        with open(image_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()


    def _entry_dir(self, key):
        return os.path.join(self.cache_dir, key[:2], key)


    def lookup(self, image_path):
        """Return the cached (markdown, images) for a page image, or None on a miss.

        Any read/parse problem counts as a miss — the page is simply re-OCR'd.
        """
        try:
            entry_dir = self._entry_dir(self._key(image_path))
            with open(os.path.join(entry_dir, "result.json"), encoding="utf-8") as fh:
                data = json.load(fh)
            images = []
            for raw in data["images"]:
                with open(os.path.join(entry_dir, raw["file"]), "rb") as fh:
                    images.append({"id": raw["id"], "safe_id": raw["safe_id"],
                                   "ext": raw["ext"], "data": fh.read()})
            return data["markdown"], images
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def store(self, image_path, result):
        """Persist a page's (markdown, images) in the cache. Best-effort.

        Image files are written first and result.json is swapped in atomically,
        so a concurrent reader never sees a half-written entry.
        """
        markdown, images = result
        try:
            entry_dir = self._entry_dir(self._key(image_path))
            os.makedirs(entry_dir, exist_ok=True)
            serial = {"markdown": markdown, "images": []}
            for i, img in enumerate(images):
                fname = f"img-{i:04d}.{img['ext']}"
                with open(os.path.join(entry_dir, fname), "wb") as fh:
                    fh.write(img["data"])
                serial["images"].append({"id": img["id"], "safe_id": img["safe_id"],
                                         "ext": img["ext"], "file": fname})
            tmp_path = os.path.join(entry_dir, "result.json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(serial, fh)
            os.replace(tmp_path, os.path.join(entry_dir, "result.json"))
        except OSError:
            pass  # an unwritable cache must never fail a conversion

