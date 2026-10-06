"""Build the release pack of the frozen D10-ext retrieval buffer + its 547 init_pre
images (PI ruling 2026-10-06; publish on the arXiv upload day, PI account).

Source (never modified): workspace/recaps_d10_frozen_c_retrieval (tree hash
7d4f3f9e…, unpacked from d10ext_final_buffer.tar.gz a762386b…).

Pack layout (all paths RELATIVE to the pack root; run tools from the pack root):
  buffer/<run_id>/<ep_id>.json   record, byte-identical except image_anchors:
                                 init_pre  → "images/<run_id>/<ep_id>/init_pre.png"
                                 final_post, key_round_pre → null (not released;
                                 used only when the recap was WRITTEN, never at
                                 retrieval — retriever.py loads init_pre only)
  images/<run_id>/<ep_id>/init_pre.png   byte copy of the original round_01_pre.png
  MANIFEST.sha256                sha256 of every file in the pack (sorted)
  README.md
Outputs a tar.gz beside the pack and prints: pack tree hash, tar sha256, and the
per-image source→copy hash check.

Usage: python3 scripts/release/build_buffer_release.py [--out workspace/release]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

SRC = Path("workspace/recaps_d10_frozen_c_retrieval")
SRC_TREE_EXPECTED = "7d4f3f9e93d99b7199a9f2dc4bebe2de2a3fd62cac4dc69d78a294f10e432ec7"
NAME = "aiongenos_d10ext_frozen_buffer_v1"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_hash(root: Path) -> str:
    out = subprocess.run(f"cd {root} && find . -type f | sort | xargs sha256sum | sha256sum",
                         shell=True, capture_output=True, text=True, check=True).stdout
    return out.split()[0]


README = """# AionGenos D10-ext frozen retrieval buffer (v1)

The frozen retrieval buffer used by the D11 `C_retrieval` protocol and the
A15 (a)/(b) protocols: 547 recap records from 7 D10 teacher runs, plus the
`init_pre` image of every record.

- **Images are part of the protocol.** At inference, `C_retrieval` attaches the
  `init_pre` image of each retrieved record (top_k = 3) to the prompt. Without
  the images, the protocol is text-only and is NOT the evaluated one.
- **Paths are relative to this directory.** Run the loader from here, e.g.
  `RecapBuffer(root="buffer")`.
- **`final_post` / `key_round_pre` are null.** Those images were used only when
  each recap was written, never at retrieval, so they are not released.
- **Known literal.** The stored `instruction` field contains an unformatted
  `{target_color}` placeholder (547/547). It is a faithful copy of the live
  pipeline; lessons are unaffected (0/547).
- **Integrity.**
  - Every file is listed in `MANIFEST.sha256`.
  - Source buffer tree hash: `7d4f3f9e93d99b7199a9f2dc4bebe2de2a3fd62cac4dc69d78a294f10e432ec7`.
  - Source tarball sha256: `a762386b79e18ce50440d1ff3e7045f6f82f32bd7b05092ac332b9217fb0eb9c`.
  - Records are byte-identical to the source except for the `image_anchors` rewrite.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("workspace/release"))
    a = ap.parse_args()
    assert tree_hash(SRC) == SRC_TREE_EXPECTED, "source buffer tree hash mismatch — refusing"
    pack = a.out / NAME
    if pack.exists():
        shutil.rmtree(pack)
    (pack / "buffer").mkdir(parents=True)
    n, mism = 0, 0
    for f in sorted(SRC.rglob("*.json")):
        rel = f.relative_to(SRC)
        run_id, ep_id = rel.parts[0], rel.stem
        d = json.loads(f.read_text())
        src_img = Path(d["image_anchors"]["init_pre"])
        dst_img = pack / "images" / run_id / ep_id / "init_pre.png"
        dst_img.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_img, dst_img)
        mism += sha(src_img) != sha(dst_img)
        d["image_anchors"] = {"init_pre": f"images/{run_id}/{ep_id}/init_pre.png",
                              "final_post": None, "key_round_pre": None}
        out = pack / "buffer" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(d, indent=2))
        n += 1
    (pack / "README.md").write_text(README)
    files = sorted(p for p in pack.rglob("*") if p.is_file())
    (pack / "MANIFEST.sha256").write_text(
        "".join(f"{sha(p)}  {p.relative_to(pack)}\n" for p in files))
    tar = a.out / f"{NAME}.tar.gz"
    # deterministic archive: fixed order/owner/mtime + gzip -n (no header timestamp)
    subprocess.run(f"tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-06 00:00Z' "
                   f"-cf - -C {a.out} {NAME} | gzip -n > {tar}", shell=True, check=True)
    print(f"records {n}  images {n}  image copy hash mismatches {mism}")
    print(f"pack tree hash  {tree_hash(pack)}")
    print(f"tar sha256      {sha(tar)}  ({tar})")
    return 0 if mism == 0 and n == 547 else 3


if __name__ == "__main__":
    raise SystemExit(main())
