"""Shared test doubles."""

from PIL import Image


def make_png(path, color=(200, 30, 30)):
    """Write a small real PNG and return its path."""
    Image.new("RGB", (8, 8), color).save(str(path), format="PNG")
    return str(path)


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    """Scripted stand-in for requests.Session."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers,
                           "timeout": timeout})
        return self.responses.pop(0)


class FakeOcrClient:
    """Stand-in for OcrClient: returns a canned (markdown, images) per page."""

    def __init__(self, result=None, error=None):
        self.result = result if result is not None else ("# Page\n\nSome text.", [])
        self.error = error
        self.calls = []

    def ocr_page(self, api_key, image_path):
        self.calls.append((api_key, image_path))
        if self.error is not None:
            raise self.error
        return self.result
