import base64

import pytest

from book_converter.ocr import OcrClient, _decode_image, _parse_images
from fakes import FakeResponse, FakeSession


def make_client(responses, retries=3):
    session = FakeSession(responses)
    client = OcrClient("http://ocr.test/v1/ocr", "test-model", retries,
                       session=session)
    return client, session


def test_decode_image_data_uri():
    raw = b"\x89PNG-fake"
    data, ext = _decode_image("data:image/png;base64,"
                              + base64.b64encode(raw).decode())
    assert (data, ext) == (raw, "png")


def test_decode_image_raw_base64_and_invalid():
    raw = b"jpeg-bytes"
    assert _decode_image(base64.b64encode(raw).decode()) == (raw, "jpg")
    assert _decode_image("") == (None, "jpg")
    assert _decode_image("!!!not-base64!!!") == (None, "jpg")


def test_parse_images_sanitizes_ids_and_skips_empty():
    raw = base64.b64encode(b"img").decode()
    images = _parse_images([
        {"id": "fig 1/a.png", "image_base64": f"data:image/png;base64,{raw}"},
        {"id": "", "image_base64": ""},
    ])
    assert len(images) == 1
    assert images[0] == {"id": "fig 1/a.png", "safe_id": "fig_1_a.png",
                         "data": b"img", "ext": "png"}


def test_ocr_page_success(tmp_path, monkeypatch):
    monkeypatch.setattr("book_converter.ocr.time.sleep", lambda s: None)
    page_png = tmp_path / "p.png"
    page_png.write_bytes(b"png-bytes")
    payload = {"pages": [{"markdown": "# Hi\n\n![img-1](img-1)",
                          "images": [{"id": "img-1",
                                      "image_base64": base64.b64encode(b"x").decode()}]}]}
    client, session = make_client([FakeResponse(200, payload)])

    markdown, images = client.ocr_page("key", str(page_png))

    assert markdown == "# Hi\n\n![img-1](img-1)"
    assert images[0]["id"] == "img-1"
    call = session.calls[0]
    assert call["url"] == "http://ocr.test/v1/ocr"
    assert call["headers"]["Authorization"] == "Bearer key"
    assert call["json"]["model"] == "test-model"
    assert call["json"]["document"]["image_url"].startswith("data:image/png;base64,")


def test_ocr_page_retries_on_500_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr("book_converter.ocr.time.sleep", lambda s: None)
    page_png = tmp_path / "p.png"
    page_png.write_bytes(b"png")
    payload = {"pages": [{"markdown": "ok", "images": []}]}
    client, session = make_client([FakeResponse(500, text="boom"),
                                   FakeResponse(200, payload)])
    assert client.ocr_page("key", str(page_png))[0] == "ok"
    assert len(session.calls) == 2


def test_ocr_page_does_not_retry_on_400(tmp_path, monkeypatch):
    monkeypatch.setattr("book_converter.ocr.time.sleep", lambda s: None)
    page_png = tmp_path / "p.png"
    page_png.write_bytes(b"png")
    client, session = make_client([FakeResponse(400, text="bad request")])
    with pytest.raises(RuntimeError, match="HTTP 400"):
        client.ocr_page("key", str(page_png))
    assert len(session.calls) == 1


def test_ocr_page_gives_up_after_retries(tmp_path, monkeypatch):
    monkeypatch.setattr("book_converter.ocr.time.sleep", lambda s: None)
    page_png = tmp_path / "p.png"
    page_png.write_bytes(b"png")
    client, session = make_client([FakeResponse(503, text="down")] * 2, retries=2)
    with pytest.raises(RuntimeError, match="after 2 attempts"):
        client.ocr_page("key", str(page_png))
    assert len(session.calls) == 2
