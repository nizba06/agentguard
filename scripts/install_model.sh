#!/usr/bin/env bash
# Copy model artifacts into agentguard/models/
# Usage: ./scripts/install_model.sh ./kaggle-model-pull/agentguard/models

set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || $# -lt 1 ]]; then
  cat <<'EOF'
Usage: ./scripts/install_model.sh <source_dir>

Copies risk_scorer.onnx, model.sha256, and tokenizer files into agentguard/models/,
then runs scripts/verify_model.py.
EOF
  [[ $# -lt 1 ]] && exit 1
  exit 0
fi

SOURCE_DIR="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/agentguard/models"
REQUIRED=(risk_scorer.onnx model.sha256 tokenizer.json tokenizer_config.json)

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source directory not found: $SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$DEST"
for name in "${REQUIRED[@]}"; do
  src="$SOURCE_DIR/$name"
  if [[ ! -f "$src" ]]; then
    echo "Missing required artifact: $src" >&2
    exit 1
  fi
  cp -f "$src" "$DEST/$name"
  echo "Installed $name"
done

echo "Verifying installed model..."
cd "$ROOT"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1 PYTHONPATH="$ROOT"
python scripts/verify_model.py
