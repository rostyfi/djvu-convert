"""Subprocess helpers."""

import subprocess


def run_checked(cmd, text=False):
    """Run a command; on failure raise RuntimeError with its last stderr line."""
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=text)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        lines = stderr.strip().splitlines()
        detail = lines[-1] if lines else f"exit status {exc.returncode}"
        raise RuntimeError(f"'{cmd[0]}' failed: {detail}") from exc

