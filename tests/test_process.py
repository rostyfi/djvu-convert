import pytest

from book_converter.process import run_checked


def test_run_checked_success():
    proc = run_checked(["echo", "hello"], text=True)
    assert proc.stdout.strip() == "hello"


def test_run_checked_failure_raises_with_last_stderr_line():
    with pytest.raises(RuntimeError) as excinfo:
        run_checked(["sh", "-c", "echo first-line >&2; echo some-error >&2; exit 3"])
    assert "some-error" in str(excinfo.value)
