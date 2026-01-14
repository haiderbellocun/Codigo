from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from tqdm import tqdm

from .manifest import Manifest
from .scanner import make_s3_key


@dataclass
class UploadStats:
    total: int
    uploaded: int
    skipped: int
    failed: int


def _s3_client(region: Optional[str] = None):
    session = boto3.session.Session(region_name=region)
    return session.client("s3")


def head_exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def upload_files(
    *,
    bucket: str,
    prefix: str,
    local_dir: Path,
    files: list[Path],
    manifest_path: Path,
    region: Optional[str] = None,
    max_workers: int = 8,
    multipart_threshold_mb: int = 64,
    multipart_chunksize_mb: int = 16,
    dry_run: bool = False,
    skip_if_exists_in_s3: bool = False,
) -> UploadStats:
    if not bucket:
        raise ValueError("S3_BUCKET está vacío. Configura tu bucket en .env o variables de entorno.")

    s3 = _s3_client(region)

    cfg = TransferConfig(
        multipart_threshold=multipart_threshold_mb * 1024 * 1024,
        multipart_chunksize=multipart_chunksize_mb * 1024 * 1024,
        max_concurrency=max_workers,
        use_threads=True,
    )

    manifest = Manifest.load(manifest_path)

    total = len(files)
    uploaded = skipped = failed = 0

    def _one(file_path: Path) -> Tuple[str, bool, str]:
        key = make_s3_key(prefix, local_dir, file_path)
        size = file_path.stat().st_size

        if manifest.is_uploaded(file_path):
            return (file_path.as_posix(), True, "SKIP(manifest)")

        if skip_if_exists_in_s3 and head_exists(s3, bucket, key):
            manifest.mark_uploaded(file_path, bucket=bucket, key=key, size=size)
            return (file_path.as_posix(), True, "SKIP(s3 exists)")

        if dry_run:
            return (file_path.as_posix(), True, f"DRY_RUN -> s3://{bucket}/{key}")

        s3.upload_file(
            Filename=str(file_path),
            Bucket=bucket,
            Key=key,
            Config=cfg,
        )
        manifest.mark_uploaded(file_path, bucket=bucket, key=key, size=size)
        return (file_path.as_posix(), True, f"UPLOADED -> s3://{bucket}/{key}")

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_one, fp) for fp in files]
        for fut in tqdm(as_completed(futures), total=total, desc="Subiendo a S3"):
            try:
                _, ok, msg = fut.result()
                if msg.startswith("SKIP"):
                    skipped += 1
                elif msg.startswith("UPLOADED") or msg.startswith("DRY_RUN"):
                    uploaded += 1
                else:
                    uploaded += 1
            except Exception:
                failed += 1

            if (uploaded + skipped + failed) % 25 == 0:
                manifest.save(manifest_path)

    manifest.save(manifest_path)
    return UploadStats(total=total, uploaded=uploaded, skipped=skipped, failed=failed)
