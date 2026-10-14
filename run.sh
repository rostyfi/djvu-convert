#!/usr/bin/env bash
# Run the Book Converter (dockerized) — one command.
# Usage: ./run.sh        (foreground; Ctrl+C to stop)
#        ./run.sh -d     (detached)
# The Mistral API key is read from .env (gitignored — never commit it).
set -euo pipefail

cd "$(dirname "$0")"

# The OCR cache is bind-mounted from ./cache (see docker-compose.yml). Create
# it here as the current user: the Docker daemon would otherwise create it as
# root, which fails on NFS shares with root squashing — and a root-owned
# directory would leave the container's appuser (uid 1000) unable to write.
mkdir -p cache
chmod 1777 cache

# Load the API key from .env (gitignored). docker compose reads .env
# automatically too; sourcing it here lets us fail early with a clear message.
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ -z "${MISTRAL_API_KEY:-}" ]; then
  echo "error: MISTRAL_API_KEY is not set — create .env with:" >&2
  echo "  MISTRAL_API_KEY=your-key-here" >&2
  exit 1
fi

exec docker compose up --build "$@"
