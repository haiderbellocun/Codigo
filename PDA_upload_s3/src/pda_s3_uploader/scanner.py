from __future__ import annotations

from pathlib import Path


def iter_files(local_dir: Path, pattern: str) -> list[Path]:
    if not local_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta local: {local_dir}")
    return sorted([p for p in local_dir.rglob(pattern) if p.is_file()])


def make_s3_key(prefix: str, local_dir: Path, file_path: Path) -> str:
    rel = file_path.relative_to(local_dir).as_posix()
    pref = (prefix or "").strip("/")
    return f"{pref}/{rel}" if pref else rel
