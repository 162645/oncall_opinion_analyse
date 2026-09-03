#!/usr/bin/env bash
set -euo pipefail

# Build an amd64 image on a builder/CI host and push it to a registry.
# Usage: REGISTRY=registry.example.com/oncall TAG=2026-08-27 ./deploy/build-push-oncall.sh [base|full]
PROFILE="${1:-base}"
REGISTRY="${REGISTRY:?Set REGISTRY, e.g. registry.example.com/oncall}"
TAG="${TAG:-$(date +%Y%m%d-%H%M)}"
docker buildx build --platform linux/amd64 \
  --build-arg INSTALL_AI_DOCS=$([[ "$PROFILE" == "full" ]] && echo 1 || echo 0) \
  -f docker/Dockerfile.python \
  -t "${REGISTRY}/python:${TAG}" --push .
echo "Pushed ${REGISTRY}/python:${TAG}"
