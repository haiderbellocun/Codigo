# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv

from pda_s3_uploader.config import load_from_env
from pda_s3_uploader.scanner import iter_files
from pda_s3_uploader.uploader import upload_files

load_dotenv()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sube archivos a S3 (PDA) con resume por manifest.")
    parser.add_argument("--local-dir", default=None)
    parser.add_argument("--pattern", default=None, help="Ej: *.pdf | **/*.pdf | *.xlsx")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--max-workers", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-if-exists", action="store_true")
    args = parser.parse_args()

    cfg = load_from_env()

    if args.local_dir:
        cfg.local_dir = Path(args.local_dir)
    if args.pattern:
        cfg.pattern = args.pattern
    if args.bucket:
        cfg.bucket = args.bucket
    if args.prefix is not None:
        cfg.prefix = args.prefix
    if args.max_workers:
        cfg.max_workers = int(args.max_workers)
    if args.dry_run:
        cfg.dry_run = True

    files = iter_files(cfg.local_dir, cfg.pattern)
    print(f"📂 Archivos encontrados: {len(files):,} | pattern='{cfg.pattern}' | dir='{cfg.local_dir}'")

    stats = upload_files(
        bucket=cfg.bucket,
        prefix=cfg.prefix,
        local_dir=cfg.local_dir,
        files=files,
        manifest_path=cfg.manifest_path,
        region=cfg.region,
        max_workers=cfg.max_workers,
        multipart_threshold_mb=cfg.multipart_threshold_mb,
        multipart_chunksize_mb=cfg.multipart_chunksize_mb,
        dry_run=cfg.dry_run,
        skip_if_exists_in_s3=args.skip_if_exists,
    )

    done = stats.uploaded + stats.skipped
    remaining = max(0, stats.total - done - stats.failed)

    print("\n✅ Resumen")
    print(f"   Total:    {stats.total:,}")
    print(f"   Subidos:  {stats.uploaded:,}")
    print(f"   Saltados: {stats.skipped:,}")
    print(f"   Fallidos: {stats.failed:,}")
    print(f"   Faltan:   {remaining:,}")


if __name__ == "__main__":
    main()
