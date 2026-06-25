#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-~/Projects/mind-lab}"
OUT="${2:-docs/sun.json}"
python3 -m trust_substrate.sun "$REPO" > "$OUT"
echo "Updated $OUT from $REPO"
