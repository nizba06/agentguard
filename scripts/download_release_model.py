#!/usr/bin/env python3
"""Download risk_scorer.onnx from the public GitHub release into agentguard/models/.

The PyPI wheel does not bundle ONNX weights (~540 MB). After
``pip install inter-agent-guard``, run:

    python scripts/download_release_model.py

Or from a clone with an editable install, the same script writes into the
package ``models/`` directory (site-packages or the repo tree).
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

REPO = "nizba06/agentguard"
TAG = "v0.1.0"
RELEASE = f"https://github.com/{REPO}/releases/download/{TAG}"
FILES = ("risk_scorer.onnx", "model.sha256")
UA = "inter-agent-guard/0.1.0"


def _models_dir() -> Path:
    import agentguard

    return Path(agentguard.__file__).resolve().parent / "models"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    print(f"  -> {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as resp, dest.open("wb") as out:  # noqa: S310
        shutil.copyfileobj(resp, out)


def _verify(onnx: Path, sha: Path) -> str:
    expected = sha.read_text(encoding="utf-8").strip().lower()
    actual = hashlib.sha256(onnx.read_bytes()).hexdigest().lower()
    if actual != expected:
        raise SystemExit(f"ONNX hash mismatch.\n  expected={expected}\n  actual=  {actual}")
    return actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Destination models directory (default: installed agentguard/models)",
    )
    args = parser.parse_args()
    models = args.dest or _models_dir()
    onnx = models / "risk_scorer.onnx"
    sha = models / "model.sha256"

    if onnx.is_file() and sha.is_file() and not args.force:
        digest = _verify(onnx, sha)
        print(f"Model already installed: {onnx}")
        print(f"Hash OK: {digest}")
        return 0

    for name in FILES:
        _download(f"{RELEASE}/{name}", models / name)

    digest = _verify(onnx, sha)
    print(f"Hash OK: {digest}")
    print(f"Ready: {onnx}")
    print("Next: agentguard status && set require_ml_model=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
