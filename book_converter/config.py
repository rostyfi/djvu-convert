"""Application settings, read from the environment with sane defaults."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    ocr_url: str = "https://api.mistral.ai/v1/ocr"
    ocr_model: str = "mistral-ocr-latest"
    ocr_workers: int = 4         # pages OCR'd in parallel
    ocr_retries: int = 5         # retries on 429 / 5xx / network errors
    job_max_age: int = 2 * 3600  # seconds before a job's files are cleaned up
    cache_dir: str = str(PROJECT_ROOT / "cache")
    max_content_length: int = 1024 * 1024 * 1024  # 1 GiB uploads
    mistral_api_key: str = ""
    host: str = "127.0.0.1"
    port: int = 5000

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(
            ocr_url=env.get("OCR_URL", cls.ocr_url),
            ocr_model=env.get("OCR_MODEL", cls.ocr_model),
            ocr_workers=int(env.get("OCR_WORKERS", cls.ocr_workers)),
            ocr_retries=int(env.get("OCR_RETRIES", cls.ocr_retries)),
            job_max_age=int(env.get("JOB_MAX_AGE", cls.job_max_age)),
            cache_dir=env.get("CACHE_DIR", cls.cache_dir),
            mistral_api_key=env.get("MISTRAL_API_KEY", ""),
            host=env.get("HOST", cls.host),
            port=int(env.get("PORT", cls.port)),
        )
