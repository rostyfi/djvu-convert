import os

from book_converter.cache import PageCache
from fakes import make_png


def test_store_and_lookup_roundtrip(tmp_path):
    cache = PageCache(str(tmp_path / "cache"), "model-a")
    png = make_png(tmp_path / "page.png")
    result = ("# Page\n\n![img-1](img-1)",
              [{"id": "img-1", "safe_id": "img-1", "ext": "png", "data": b"123"}])
    cache.store(png, result)
    assert cache.lookup(png) == result


def test_lookup_miss_for_unknown_image(tmp_path):
    cache = PageCache(str(tmp_path / "cache"), "model-a")
    assert cache.lookup(make_png(tmp_path / "page.png")) is None


def test_model_is_part_of_the_key(tmp_path):
    cache_dir = str(tmp_path / "cache")
    png = make_png(tmp_path / "page.png")
    PageCache(cache_dir, "model-a").store(png, ("md", []))
    assert PageCache(cache_dir, "model-b").lookup(png) is None
    assert PageCache(cache_dir, "model-a").lookup(png) == ("md", [])


def test_corrupt_entry_counts_as_a_miss(tmp_path):
    cache = PageCache(str(tmp_path / "cache"), "model-a")
    png = make_png(tmp_path / "page.png")
    cache.store(png, ("md", []))
    entry_dir = cache._entry_dir(cache._key(png))
    with open(os.path.join(entry_dir, "result.json"), "w") as fh:
        fh.write("not json")
    assert cache.lookup(png) is None


def test_unwritable_cache_never_raises(tmp_path):
    cache = PageCache(str(tmp_path / "cache"), "model-a")
    png = make_png(tmp_path / "page.png")
    # a directory where a file is expected makes every write fail
    os.makedirs(os.path.join(cache._entry_dir(cache._key(png)), "img-0000.jpg"),
                exist_ok=True)
    cache.store(png, ("md", [{"id": "i", "safe_id": "i", "ext": "jpg",
                             "data": b"x"}]))
