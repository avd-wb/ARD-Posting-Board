#!/usr/bin/env python3
"""
backup_manager.py
Automated snapshotting, versioning, and rollback management for ard_master_truth.db.
"""

import os
import shutil
import sqlite3
import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
BACKUP_DIR = "/tmp/backups" if is_vercel else os.path.join(BASE_DIR, "backups")
DB_PATH = "/tmp/ard_master_truth.db" if is_vercel else os.path.join(BASE_DIR, "ard_master_truth.db")

os.makedirs(BACKUP_DIR, exist_ok=True)

class BackupManager:
    def __init__(self, db_path: str = None, backup_dir: str = None):
        self.db_path = db_path or DB_PATH
        self.backup_dir = backup_dir or BACKUP_DIR
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self, tag: str = "manual") -> Dict[str, Any]:
        """
        Creates a clean timestamped SQLite backup snapshot.
        """
        if not os.path.exists(self.db_path):
            return {"success": False, "error": "Source database not found"}

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_tag = "".join(c for c in tag if c.isalnum() or c in ("-", "_")).strip() or "auto"
        filename = f"ard_backup_{timestamp}_{safe_tag}.db"
        dest_path = os.path.join(self.backup_dir, filename)

        try:
            # Use SQLite backup API for atomic snapshot
            src_conn = sqlite3.connect(self.db_path)
            dest_conn = sqlite3.connect(dest_path)
            with dest_conn:
                src_conn.backup(dest_conn)
            src_conn.close()
            dest_conn.close()

            size_bytes = os.path.getsize(dest_path)
            self._prune_old_backups(keep=25)

            return {
                "success": True,
                "filename": filename,
                "path": dest_path,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "timestamp": now.isoformat(),
                "tag": safe_tag
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Lists available database backups ordered newest first.
        """
        if not os.path.exists(self.backup_dir):
            return []

        backups = []
        for f in os.listdir(self.backup_dir):
            if f.endswith(".db") and f.startswith("ard_backup_"):
                p = os.path.join(self.backup_dir, f)
                stat = os.stat(p)
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                backups.append({
                    "filename": f,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": mtime
                })

        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups

    def restore_backup(self, filename: str) -> Dict[str, Any]:
        """
        Safely restores a backup file over the active database.
        Takes a safety snapshot of the active DB before overwriting.
        """
        backup_path = os.path.join(self.backup_dir, filename)
        if not os.path.exists(backup_path):
            return {"success": False, "error": f"Backup file {filename} not found"}

        try:
            # 1. Take safety snapshot of current DB
            safety_copy = os.path.join(self.backup_dir, f"pre_restore_safety_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, safety_copy)

            # 2. Overwrite DB
            shutil.copy2(backup_path, self.db_path)

            return {
                "success": True,
                "restored_from": filename,
                "safety_backup": os.path.basename(safety_copy),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _prune_old_backups(self, keep: int = 25):
        """Keeps the most recent N backups to manage disk space."""
        backups = self.list_backups()
        if len(backups) > keep:
            for b in backups[keep:]:
                try:
                    os.remove(os.path.join(self.backup_dir, b["filename"]))
                except Exception:
                    pass

if __name__ == "__main__":
    bm = BackupManager()
    res = bm.create_backup("initial_verification")
    print("Backup created:", res)
    print("Backup list count:", len(bm.list_backups()))
