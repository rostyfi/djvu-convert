"""Mistral OCR client: one page image -> (markdown, extracted images)."""

import base64
import re
import time

import requests


def _decode_image(image_base64):
    """Decode Mistral's image_base64 field (data URI or raw base64) to (bytes, ext)."""
    if not image_base64:
        return None, "jpg"
    b64 = image_base64
    ext = "jpg"
    if image_base64.startswith("data:"):
        header, _, b64 = image_base64.partition(",")
        mime = header[5:].split(";", 1)[0].strip().lower()
        ext = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
               "image/webp": "webp", "image/gif": "gif"}.get(mime, "jpg")
    try:
        return base64.b64decode(b64), ext
    except (ValueError, TypeError):
        return None, ext


def _parse_images(raw_images):
    """Turn the images[] array of a Mistral OCR page into a list of dicts.

    Each dict has the original "id" (as used in the markdown placeholders),
    a filesystem-safe "safe_id", the decoded image "data" and its "ext".
    """
    images = []
    for raw in raw_images:
        data, ext = _decode_image(raw.get("image_base64", ""))
        if data is None:
            continue
        original = str(raw.get("id", "") or f"img-{len(images)}")
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", original).strip("._-") or f"img-{len(images)}"
        images.append({"id": original, "safe_id": safe, "data": data, "ext": ext})
    return images



class OcrClient:
    """Client for the Mistral OCR API.

    One call per page image; returns the page as markdown (with ![id](id)
    placeholders for detected images) plus the decoded images.
    """

    def __init__(self, url, model, retries, session=None):
        self.url = url
        self.model = model
        self.retries = retries
        self._session = session

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def ocr_page(self, api_key, image_path):
        """OCR one page image with Mistral OCR.

        Returns (markdown, images): the page as markdown (containing ![id](id)
        placeholders for detected images) and a list of parsed images.
        """
        with open(image_path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("ascii")
        payload = {
            "model": self.model,
            "document": {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{encoded}",
            },
            "include_image_base64": True,
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        last_error = "unknown error"
        for attempt in range(self.retries):
            try:
                resp = self.session.post(self.url, json=payload, headers=headers, timeout=180)
            except requests.RequestException as exc:
                last_error = str(exc)
            else:
                if resp.status_code == 200:
                    try:
                        page = resp.json()["pages"][0]
                        return page["markdown"], _parse_images(page.get("images") or [])
                    except (ValueError, KeyError, IndexError) as exc:
                        raise RuntimeError(f"Unexpected Mistral OCR response: {exc}") from exc
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                if resp.status_code < 500 and resp.status_code != 429:
                    raise RuntimeError(f"Mistral OCR failed: {last_error}")
            time.sleep(min(2 ** attempt, 30))
        raise RuntimeError(f"Mistral OCR failed after {self.retries} attempts: {last_error}")

