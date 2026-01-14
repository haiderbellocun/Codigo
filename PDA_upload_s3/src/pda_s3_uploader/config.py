from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class S3UploadConfig:
    bucket: str
    prefix: str
    local_dir: Path
    pattern: str = "*"
    region: str | None = None
    manifest_path: Path = Path("outputs/manifest.json")
    max_workers: int = 8
    multipart_threshold_mb: int = 64
    multipart_chunksize_mb: int = 16
    dry_run: bool = False


def load_from_env() -> S3UploadConfig:
    bucket = os.environ.get("S3_BUCKET", "").strip()
    prefix = os.environ.get("S3_PREFIX", "").strip()
    local_dir = Path(os.environ.get("LOCAL_DIR", "data")).expanduser()

    return S3UploadConfig(
        bucket=bucket,
        prefix=prefix,
        local_dir=local_dir,
        pattern=os.environ.get("FILE_PATTERN", "*").strip() or "*",
        region=os.environ.get("AWS_REGION") or None,
        manifest_path=Path(os.environ.get("MANIFEST_PATH", "outputs/manifest.json")),
        max_workers=int(os.environ.get("MAX_WORKERS", "8")),
        multipart_threshold_mb=int(os.environ.get("MULTIPART_THRESHOLD_MB", "64")),
        multipart_chunksize_mb=int(os.environ.get("MULTIPART_CHUNKSIZE_MB", "16")),
        dry_run=os.environ.get("DRY_RUN", "no").lower() in {"1","true","yes","y"},
    )
