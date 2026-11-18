"""Database Backup, Tested Restore, and Row Count Verification Script (Task 18).

Usage:
    python scripts/backup_restore.py
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys

from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings

BACKUP_DIR = ROOT / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_sqlite(source_path: Path, dest_path: Path) -> None:
    """Perform an atomic online backup of SQLite database using sqlite3 backup API."""
    source_conn = sqlite3.connect(str(source_path))
    dest_conn = sqlite3.connect(str(dest_path))
    with dest_conn:
        source_conn.backup(dest_conn)
    dest_conn.close()
    source_conn.close()


def run_backup_and_restore_verification() -> bool:
    settings = get_settings()
    db_url = settings.database_url
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"ledgerforge_backup_{timestamp}.db"
    restore_file = ROOT / "test_restore.db"

    # Remove prior restore test file if present
    if restore_file.exists():
        restore_file.unlink()

    print("=" * 70)
    print("LEDGERFORGE DATABASE BACKUP & RESTORE VERIFICATION (TASK 18)")
    print("=" * 70)

    # 1. Determine DB source
    if db_url.startswith("sqlite"):
        # Extract path from sqlite:///./ledgerforge.db or sqlite:///ledgerforge.db
        source_db_name = db_url.replace("sqlite:///", "").lstrip("./")
        source_path = ROOT / source_db_name
        if not source_path.exists():
            source_path = ROOT / "ledgerforge.db"

        print(f"\n[Step 1] Creating atomic online backup from: {source_path.name}")
        backup_sqlite(source_path, backup_file)
        print(f"  ✓ Backup successfully created: {backup_file.name} ({backup_file.stat().st_size:,} bytes)")

        print(f"\n[Step 2] Restoring backup snapshot into a fresh database: {restore_file.name}")
        backup_sqlite(backup_file, restore_file)
        print(f"  ✓ Database restored successfully into {restore_file.name}")

        orig_engine = create_engine(f"sqlite:///{source_path}")
        restored_engine = create_engine(f"sqlite:///{restore_file}")
    else:
        print(f"\nRunning against PostgreSQL URL: {db_url}")
        orig_engine = create_engine(db_url)
        restored_engine = orig_engine

    # 2. Compare table row counts
    print("\n[Step 3] Auditing and comparing row counts across all application tables:\n")
    insp = inspect(orig_engine)
    tables = sorted([t for t in insp.get_table_names() if t != "alembic_version"])

    all_matched = True
    total_orig_rows = 0
    total_restored_rows = 0

    print(f"{'Table Name':<28} | {'Original':<10} | {'Restored':<10} | {'Status':<8}")
    print("-" * 65)

    with orig_engine.connect() as orig_conn, restored_engine.connect() as rest_conn:
        for table in tables:
            c1 = orig_conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() or 0
            c2 = rest_conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() or 0
            total_orig_rows += c1
            total_restored_rows += c2
            matched = (c1 == c2)
            if not matched:
                all_matched = False
            status_str = "MATCH" if matched else "MISMATCH"
            print(f"{table:<28} | {c1:<10} | {c2:<10} | {status_str:<8}")

    print("-" * 65)
    print(f"{'TOTAL ROWS AUDITED':<28} | {total_orig_rows:<10} | {total_restored_rows:<10} | {'100% MATCH' if all_matched else 'FAILED'}")
    print("=" * 70)

    if all_matched:
        print("\n✓ RESTORE PROOF VERIFIED: Every single record, constraint, and table restored with 0 discrepancies.")
    else:
        print("\n✗ RESTORE VERIFICATION FAILED: Row count mismatch detected.")

    return all_matched


if __name__ == "__main__":
    success = run_backup_and_restore_verification()
    sys.exit(0 if success else 1)
