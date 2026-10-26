#!/usr/bin/env python3
"""Download only the public, immutable v0.1.0 raw snapshot; never refresh the API."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    from huggingface_hub import snapshot_download
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot_download(repo_id="Bayanat-Labs/arabic-public-data-reasoning", repo_type="dataset",
                      revision="v0.1.0", allow_patterns=["raw/*"], local_dir=str(args.output), token=False)
    root = args.output / "raw"
    expected_manifest = "c51853183363290e56714582b5ac3d2bca382a7400b88e8c9b90369f7150c170"
    assert hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest() == expected_manifest
    manifest = json.loads((root / "manifest.json").read_text())
    for item in manifest["files"]:
        path = root / item["file"]
        assert path.is_file() and path.stat().st_size == item["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    print(json.dumps({"verified_raw_files": len(manifest["files"]), "revision": "v0.1.0",
                      "raw_manifest_sha256": expected_manifest}))


if __name__ == "__main__":
    main()
