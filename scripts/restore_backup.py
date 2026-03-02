"""
Restore KwikKhata Excel DB from backup snapshots.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def find_latest_backup(backup_dir: str, db_path: str) -> Path | None:
    db = Path(db_path)
    folder = Path(backup_dir)
    if not folder.exists():
        return None
    candidates = sorted(
        folder.glob(f"{db.stem}_*{db.suffix}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def restore_backup(backup_file: str, db_path: str, create_pre_restore_backup: bool = True) -> Path:
    source = Path(backup_file)
    if not source.exists():
        raise FileNotFoundError(f"Backup not found: {backup_file}")

    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if create_pre_restore_backup and target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety = target.parent / f"{target.stem}_pre_restore_{stamp}{target.suffix}"
        shutil.copy2(target, safety)
    shutil.copy2(source, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore KwikKhata DB from backups.")
    parser.add_argument("--db", default="kwik_khata_db.xlsx", help="Primary DB file path")
    parser.add_argument("--backup-dir", default="backups", help="Backup directory path")
    parser.add_argument("--file", default="", help="Specific backup file to restore")
    parser.add_argument(
        "--no-safety-backup",
        action="store_true",
        help="Skip creating pre-restore safety backup of current DB file",
    )
    args = parser.parse_args()

    try:
        backup_file = args.file or str(find_latest_backup(args.backup_dir, args.db) or "")
        if not backup_file:
            raise RuntimeError("No backup files found to restore.")
        restored_to = restore_backup(
            backup_file=backup_file,
            db_path=args.db,
            create_pre_restore_backup=not args.no_safety_backup,
        )
        print(f"Restore complete: source={backup_file} -> target={restored_to}")
    except Exception as exc:
        print(f"Restore failed: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
