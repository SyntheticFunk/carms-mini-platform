from __future__ import annotations

import io
import os
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request

OWNER = "dnokes"
REPO = "Junior-Data-Scientist"

# GitHub "zipball" always points to the default branch head.
ZIP_URL = f"https://github.com/{OWNER}/{REPO}/archive/refs/heads/main.zip"

EXPECTED_EXTS = {".xlsx", ".zip", ".md"}  # keep only the relevant artifacts

def repo_root() -> Path:
    p = Path.cwd().resolve()
    while not (p / "pyproject.toml").exists():
        if p.parent == p:
            raise RuntimeError("Could not locate repo root (pyproject.toml not found). Run from repo root.")
        p = p.parent
    return p

def safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

def download_zip(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "carms-mini-platform-fetch/1.0"})
    with urlopen(req, timeout=60) as resp:
        return resp.read()

def strip_zone_identifier_files(root: Path) -> int:
    removed = 0
    for fp in root.rglob("*Zone.Identifier"):
        try:
            fp.unlink()
            removed += 1
        except OSError:
            pass
    return removed

def main() -> None:
    root = repo_root()
    out_dir = root / "data" / "raw" / "dnokes"
    tmp_dir = root / "data" / "_tmp_dnokes_extract"

    print(f"[fetch] target: {out_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    safe_rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"[fetch] downloading: {ZIP_URL}")
    blob = download_zip(ZIP_URL)

    print("[fetch] extracting zipball...")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(tmp_dir)

    # The zipball contains a single top-level folder like dnokes-Junior-Data-Scientist-<sha>/
    top_levels = [p for p in tmp_dir.iterdir() if p.is_dir()]
    if len(top_levels) != 1:
        raise RuntimeError(f"Unexpected zip structure. Top level dirs: {top_levels}")
    src_root = top_levels[0]

    # Clean destination (so results are deterministic)
    safe_rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for fp in src_root.rglob("*"):
        if fp.is_file() and fp.suffix.lower() in EXPECTED_EXTS:
            rel = fp.relative_to(src_root)
            dest = out_dir / rel.name  # flatten: keep only filenames at top level
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, dest)
            copied += 1

    removed = strip_zone_identifier_files(out_dir)

    safe_rmtree(tmp_dir)

    print(f"[fetch] copied {copied} files into {out_dir}")
    if removed:
        print(f"[fetch] removed {removed} *Zone.Identifier metadata files")
    print("[fetch] done.")

if __name__ == "__main__":
    main()
