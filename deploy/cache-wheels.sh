#!/usr/bin/env bash
set -euo pipefail

# Populate a reusable wheel cache. Run from the repository root.
CACHE_DIR="${1:-wheelhouse}"
PROFILE="${2:-base}"
mkdir -p "$CACHE_DIR"
REQ="requirements-base.txt"
if [[ "$PROFILE" == "full" ]]; then REQ="requirements.txt"; fi
if [[ "${USE_DOCKER_PYTHON:-1}" == "1" ]] && command -v docker >/dev/null 2>&1; then
  # Match the image's CPython 3.11 ABI; the host may be Python 3.12+.
  docker run --rm -v "$(pwd):/work" -w /work python:3.11-slim \
    python -m pip download --prefer-binary --timeout 120 \
    --index-url "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple}" \
    --dest "/work/$CACHE_DIR" -r "/work/$REQ"
else
  python3 -m pip download --prefer-binary --timeout 120 \
    --index-url "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple}" \
    --dest "$CACHE_DIR" -r "$REQ"
fi
echo "Wheel cache ready: $CACHE_DIR ($(find "$CACHE_DIR" -type f | wc -l) files)"
