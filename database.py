"""
database.py — KwikKhata Ledger Database Module
===============================================
Excel-backed ledger store using openpyxl.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook


class KhataDB:
    """Excel-backed customer ledger database."""

    DB_FILE = "kwik_khata_db.xlsx"
    LEDGER_SHEET = "Khata"
    HISTORY_SHEET = "Transactions"
    HEADERS = ["Customer_Name", "Balance"]
    HISTORY_HEADERS = ["Timestamp", "Customer_Name", "Amount", "New_Balance"]
    BACKUP_DIR = "backups"

    def __init__(self, filepath: str | None = None):
        self.filepath = filepath or self.DB_FILE
        self.backup_dir = os.getenv("KWIKKHATA_BACKUP_DIR", self.BACKUP_DIR)
        self.backup_keep = int(os.getenv("KWIKKHATA_BACKUP_KEEP", "20"))
        self.enable_backups = os.getenv("KWIKKHATA_ENABLE_BACKUP", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._ensure_file_exists()
        self._backup_if_enabled()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.filepath):
            wb = Workbook()
            ws = wb.active
            ws.title = self.LEDGER_SHEET
            ws.append(self.HEADERS)
            history = wb.create_sheet(self.HISTORY_SHEET)
            history.append(self.HISTORY_HEADERS)
            wb.save(self.filepath)
            wb.close()
            return

        # Ensure mandatory sheets exist even if file already present.
        wb = load_workbook(self.filepath)
        try:
            if self.LEDGER_SHEET not in wb.sheetnames:
                ws = wb.create_sheet(self.LEDGER_SHEET, 0)
                ws.append(self.HEADERS)
            if self.HISTORY_SHEET not in wb.sheetnames:
                history = wb.create_sheet(self.HISTORY_SHEET)
                history.append(self.HISTORY_HEADERS)
            wb.save(self.filepath)
        finally:
            wb.close()

    def _normalize_name(self, name: str) -> str:
        return str(name).strip().title()

    def _find_customer_row(self, ws, name: str) -> int | None:
        normalized = self._normalize_name(name)
        for row in range(2, ws.max_row + 1):
            value = ws.cell(row=row, column=1).value
            if value and self._normalize_name(value) == normalized:
                return row
        return None

    def _append_history(self, ws_history, name: str, amount: float, new_balance: float) -> None:
        ws_history.append(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self._normalize_name(name),
                round(float(amount), 2),
                round(float(new_balance), 2),
            ]
        )

    def _backup_if_enabled(self) -> None:
        """Create a timestamped DB backup and prune older backups."""
        if not self.enable_backups:
            return

        db_path = Path(self.filepath)
        if not db_path.exists():
            return

        backup_dir = Path(self.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{db_path.stem}_{timestamp}{db_path.suffix}"
        backup_path = backup_dir / backup_name
        shutil.copy2(db_path, backup_path)

        # Keep only the latest N backups.
        backups = sorted(
            backup_dir.glob(f"{db_path.stem}_*{db_path.suffix}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[self.backup_keep :]:
            old.unlink(missing_ok=True)

    def add_transaction(self, name: str, amount: int | float) -> float:
        """Add positive (udhaar) or negative (jama) amount to customer balance."""
        normalized_name = self._normalize_name(name)
        if not normalized_name:
            raise ValueError("customer name cannot be empty")

        try:
            amount = round(float(amount), 2)
        except (TypeError, ValueError) as exc:
            raise ValueError("amount must be a number") from exc

        wb = load_workbook(self.filepath)
        try:
            ws = wb[self.LEDGER_SHEET]
            ws_history = wb[self.HISTORY_SHEET]
            row = self._find_customer_row(ws, normalized_name)

            if row:
                current_balance = float(ws.cell(row=row, column=2).value or 0)
                new_balance = round(current_balance + amount, 2)
                ws.cell(row=row, column=2, value=new_balance)
            else:
                new_balance = round(amount, 2)
                ws.append([normalized_name, new_balance])

            self._append_history(ws_history, normalized_name, amount, new_balance)
            wb.save(self.filepath)
            return new_balance
        finally:
            wb.close()

    def get_balance(self, name: str) -> float | None:
        normalized_name = self._normalize_name(name)
        if not normalized_name:
            return None

        wb = load_workbook(self.filepath)
        try:
            ws = wb[self.LEDGER_SHEET]
            row = self._find_customer_row(ws, normalized_name)
            if not row:
                return None
            return round(float(ws.cell(row=row, column=2).value or 0), 2)
        finally:
            wb.close()

    def get_all_ledgers(self) -> list[dict]:
        """Return customers with pending positive balances."""
        wb = load_workbook(self.filepath)
        try:
            ws = wb[self.LEDGER_SHEET]
            ledgers: list[dict] = []
            for row in range(2, ws.max_row + 1):
                name = ws.cell(row=row, column=1).value
                balance = float(ws.cell(row=row, column=2).value or 0)
                if name and balance > 0:
                    ledgers.append({"name": str(name), "balance": round(balance, 2)})
            return ledgers
        finally:
            wb.close()

    def get_recent_transactions(self, limit: int = 10) -> list[dict]:
        """Return most recent transaction rows for debugging/operator visibility."""
        limit = max(1, int(limit))
        wb = load_workbook(self.filepath)
        try:
            ws = wb[self.HISTORY_SHEET]
            rows = []
            start_row = max(2, ws.max_row - limit + 1)
            for row in range(ws.max_row, start_row - 1, -1):
                rows.append(
                    {
                        "timestamp": ws.cell(row=row, column=1).value,
                        "name": ws.cell(row=row, column=2).value,
                        "amount": ws.cell(row=row, column=3).value,
                        "new_balance": ws.cell(row=row, column=4).value,
                    }
                )
            return rows
        finally:
            wb.close()
