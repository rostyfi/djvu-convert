from book_converter.config import Settings


def test_defaults():
    s = Settings()
    assert s.ocr_url == "https://api.mistral.ai/v1/ocr"
    assert s.ocr_model == "mistral-ocr-latest"
    assert s.ocr_workers == 4
    assert s.ocr_retries == 5
    assert s.job_max_age == 2 * 3600
    assert s.max_content_length == 1024 * 1024 * 1024
    assert s.mistral_api_key == ""
    assert s.host == "127.0.0.1"
    assert s.port == 5000
    assert s.cache_dir.endswith("cache")


def test_from_env():
    env = {
        "OCR_URL": "http://ocr.example/v1/ocr",
        "OCR_MODEL": "custom-model",
        "OCR_WORKERS": "8",
        "OCR_RETRIES": "2",
        "JOB_MAX_AGE": "60",
        "CACHE_DIR": "/tmp/xyz",
        "MISTRAL_API_KEY": "k",
        "HOST": "0.0.0.0",
        "PORT": "8080",
    }
    s = Settings.from_env(env)
    assert s.ocr_url == "http://ocr.example/v1/ocr"
    assert s.ocr_model == "custom-model"
    assert s.ocr_workers == 8
    assert s.ocr_retries == 2
    assert s.job_max_age == 60
    assert s.cache_dir == "/tmp/xyz"
    assert s.mistral_api_key == "k"
    assert s.host == "0.0.0.0"
    assert s.port == 8080


def test_from_env_ignores_unrelated_env(monkeypatch):
    monkeypatch.setenv("UNRELATED", "1")
    assert Settings.from_env().ocr_model == "mistral-ocr-latest"
