"""Pack a training-bundle tarball for shipping to the remote GPU host.

Given one or more JSONL training sets, collects every unique ``image_path``
referenced across all rows, plus the JSONLs themselves, into a tar.gz.

Rewrites ``image_path`` inside each row to be relative to the tarball root
so the extraction on the server preserves the file layout the trainer expects.

Usage:
    python3 pack_training_bundle.py \\
        --jsonls data/training_sets/v4_sft_A.jsonl data/training_sets/v4_kto_B.jsonl \\
        --out /tmp/d11_bundle.tar.gz
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import tarfile
from pathlib import Path

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonls", nargs="+", required=True,
                        help="One or more JSONL training sets to include.")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output tarball path.")
    parser.add_argument("--repo_root", type=Path, default=Path("."),
                        help="Repo root to compute relative paths from.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    repo_root = args.repo_root.resolve()
    images: set[Path] = set()
    rewritten_jsonls: list[tuple[Path, str]] = []

    for jsonl_path_str in args.jsonls:
        jsonl_path = Path(jsonl_path_str)
        if not jsonl_path.exists():
            raise FileNotFoundError(str(jsonl_path))
        rewritten_rows: list[str] = []
        with jsonl_path.open() as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                img = Path(rec["image_path"])
                if not img.is_absolute():
                    img = (repo_root / img).resolve()
                try:
                    rel = img.relative_to(repo_root)
                except ValueError:
                    # image outside repo root — keep absolute (server side must match)
                    rel = img
                if img.exists():
                    images.add(img)
                    rec["image_path"] = str(rel)
                else:
                    logger.warning(f"  missing image, dropping row: {img}")
                    continue
                rewritten_rows.append(json.dumps(rec))
        # Rewritten JSONL will live at the same relative path inside the tarball
        rel_jsonl = jsonl_path.resolve().relative_to(repo_root) if jsonl_path.is_absolute() else jsonl_path
        rewritten_jsonls.append((Path(str(rel_jsonl)), "\n".join(rewritten_rows) + "\n"))

    logger.info(f"Packing {len(rewritten_jsonls)} JSONL files + {len(images)} unique images")
    logger.info(f"Output: {args.out}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.out, "w:gz") as tar:
        # Add rewritten JSONLs as text blobs
        for rel_path, content in rewritten_jsonls:
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=str(rel_path))
            info.size = len(data)
            info.mode = 0o644
            import io
            tar.addfile(info, io.BytesIO(data))

        # Add image files
        for img in sorted(images):
            arc_name = str(img.relative_to(repo_root)) if img.is_absolute() and str(img).startswith(str(repo_root)) else str(img)
            tar.add(img, arcname=arc_name)

    size_mb = args.out.stat().st_size / 1024 / 1024
    logger.info(f"Done. Bundle size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
