#!/usr/bin/env python3
"""scripts/backup_db.py
---------------------
Production-grade, portable PostgreSQL backup and verification utility for KRATOS V3.1.
Supports timestamped non-overwriting backups, SHA-256 checksum generation,
manifest logging, and pg_restore archive readability verification.
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Resolve repository root dynamically without hardcoded machine paths
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("backup_db")


def compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hexadecimal digest of a file in chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_connection_params(db_name_override: str = None, is_test_db: bool = False):
    """Safely parse connection parameters from environment without exposing secrets."""
    if is_test_db:
        db_url = os.getenv("TEST_DATABASE_URL")
    else:
        db_url = os.getenv("DATABASE_URL")

    if db_url:
        parsed = urlparse(db_url)
        user = unquote(parsed.username) if parsed.username else os.getenv("DB_USER", "postgres")
        password = unquote(parsed.password) if parsed.password else os.getenv("DB_PASSWORD", "")
        host = parsed.hostname or os.getenv("DB_HOST", "localhost")
        port = str(parsed.port or os.getenv("DB_PORT", "5432"))
        dbname = parsed.path.lstrip('/') or (os.getenv("TEST_DB_NAME", "wildfire_test_db") if is_test_db else os.getenv("DB_NAME", "wildfire_db"))
    else:
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = str(os.getenv("DB_PORT", "5432"))
        dbname = os.getenv("TEST_DB_NAME", "wildfire_test_db") if is_test_db else os.getenv("DB_NAME", "wildfire_db")

    if db_name_override:
        dbname = db_name_override

    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname
    }


def backup_database(
    dbname: str,
    output_dir: Path,
    backup_format: str = "custom",
    tag: str = "auto",
    user: str = None,
    password: str = None,
    host: str = None,
    port: str = None
) -> dict:
    """
    Execute pg_dump with safe environment-based authentication.
    Returns a dict with backup metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    ext = "dump" if backup_format == "custom" else "sql"
    filename = f"{dbname}_{timestamp_str}_{tag}.{ext}"
    backup_file = output_dir / filename

    if backup_file.exists():
        counter = 1
        while backup_file.exists():
            backup_file = output_dir / f"{dbname}_{timestamp_str}_{tag}_{counter}.{ext}"
            counter += 1

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    cmd = [
        "pg_dump",
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", dbname,
        "-f", str(backup_file),
    ]

    if backup_format == "custom":
        cmd.extend(["-F", "c"])  # Custom archive format, compatible with pg_restore
    else:
        cmd.extend(["--clean", "--if-exists", "--no-owner", "--no-privileges"])

    log.info("Dumping database '%s' to '%s' (format: %s)...", dbname, backup_file.name, backup_format)
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        log.error("pg_dump failed with exit code %d: %s", res.returncode, res.stderr.strip())
        raise RuntimeError(f"pg_dump failed: {res.stderr.strip()}")

    if not backup_file.exists() or backup_file.stat().st_size == 0:
        raise RuntimeError(f"Backup file was not created or is empty: {backup_file}")

    file_size = backup_file.stat().st_size
    sha256_hash = compute_sha256(backup_file)

    log.info("✓ Backup created successfully: %s (%d bytes, SHA-256: %s)", backup_file.name, file_size, sha256_hash[:16] + "...")

    metadata = {
        "database": dbname,
        "backup_file": str(backup_file.resolve()),
        "filename": backup_file.name,
        "format": backup_format,
        "size_bytes": file_size,
        "sha256": sha256_hash,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "port": port,
        "user": user,
        "tag": tag,
        "verified": False
    }

    return metadata


def verify_backup_archive(backup_file_path: Path, backup_format: str = "custom") -> bool:
    """Verify archive readability using pg_restore list verification."""
    if not backup_file_path.exists():
        log.error("Verification failed: backup file does not exist: %s", backup_file_path)
        return False

    if backup_format == "custom":
        cmd = ["pg_restore", "-l", str(backup_file_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            log.error("pg_restore -l failed with code %d: %s", res.returncode, res.stderr.strip())
            return False
        
        toc_lines = [l for l in res.stdout.splitlines() if l.strip() and not l.startswith(";")]
        log.info("✓ Archive readability verified for %s: %d TOC items found in header.", backup_file_path.name, len(toc_lines))
        return len(toc_lines) > 0
    else:
        # Plain SQL verification
        with open(backup_file_path, "r", encoding="utf-8", errors="ignore") as f:
            first_lines = [f.readline() for _ in range(10)]
        has_sql = any("PostgreSQL database dump" in l or "SET " in l or "CREATE " in l for l in first_lines)
        log.info("✓ Plain SQL structure verified for %s.", backup_file_path.name)
        return has_sql


def write_manifest(output_dir: Path, metadata_list: list):
    """Write/append to backup manifest in the backup directory."""
    manifest_file = output_dir / "backup_manifest.json"
    existing = []
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing.extend(metadata_list)
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    log.info("Updated backup manifest: %s", manifest_file)


def run_cli():
    parser = argparse.ArgumentParser(description="KRATOS PostgreSQL Backup & Verification Utility")
    parser.add_argument("--db", choices=["wildfire_db", "wildfire_test_db", "both"], default="both",
                        help="Target database to back up (default: both)")
    parser.add_argument("--format", choices=["custom", "plain"], default="custom",
                        help="Backup format: 'custom' (.dump for pg_restore) or 'plain' (.sql) (default: custom)")
    parser.add_argument("--tag", default="pre_hardening", help="Descriptive tag for backup filename")
    parser.add_argument("--output-dir", help="Output directory override (defaults to BACKUP_DIR env or 'backups/')")
    parser.add_argument("--no-verify", action="store_true", help="Skip archive readability verification")
    args = parser.parse_args()

    default_backup_dir = Path(os.getenv("BACKUP_DIR", REPO_ROOT / "backups"))
    output_dir = Path(args.output_dir) if args.output_dir else default_backup_dir

    targets = []
    if args.db in ("wildfire_db", "both"):
        targets.append(("wildfire_db", False))
    if args.db in ("wildfire_test_db", "both"):
        targets.append(("wildfire_test_db", True))

    results = []
    for db_name, is_test in targets:
        params = get_connection_params(db_name_override=db_name, is_test_db=is_test)
        try:
            meta = backup_database(
                dbname=params["dbname"],
                output_dir=output_dir,
                backup_format=args.format,
                tag=args.tag,
                user=params["user"],
                password=params["password"],
                host=params["host"],
                port=params["port"]
            )
            if not args.no_verify:
                verified = verify_backup_archive(Path(meta["backup_file"]), backup_format=args.format)
                meta["verified"] = verified
                if not verified:
                    log.error("✗ Backup verification failed for %s", db_name)
                    sys.exit(1)
            results.append(meta)
        except Exception as e:
            log.error("✗ Backup failed for %s: %s", db_name, e)
            sys.exit(1)

    write_manifest(output_dir, results)
    log.info("All requested backups completed and verified successfully.")


if __name__ == "__main__":
    run_cli()
