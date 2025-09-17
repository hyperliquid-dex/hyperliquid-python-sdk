#!/bin/bash
set -e

# Python deps
pip install -r requirements.txt || true

# Node deps
if [ -f package.json ]; then
  npm install
fi

# Go deps (if needed)
if [ -f go.mod ]; then
  go mod tidy
fi
