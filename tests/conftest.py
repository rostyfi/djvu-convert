import pytest

from book_converter.cache import PageCache
from book_converter.config import Settings
from book_converter.jobs import JobStore


@pytest.fixture
def settings(tmp_path):
    return Settings(cache_dir=str(tmp_path / "cache"), mistral_api_key="test-key")


@pytest.fixture
def job_store():
    return JobStore()


@pytest.fixture
def page_cache(settings):
    return PageCache(settings.cache_dir, settings.ocr_model)
