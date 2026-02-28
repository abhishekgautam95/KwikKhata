"""
database.py — KwikKhata Ledger Database Module
================================================
Uses openpyxl to store customer balances in an Excel file.
Each customer has a name and a running balance (udhaar/credit ledger).
"""

import os
from openpyxl import Workbook, load_workbook


class KhataDB:
    """Excel-backed customer ledger database."""

    # Default Excel file name
    DB_FILE = "kwik_khata_db.xlsx"
    # Column layout
    HEADERS = ["Customer_Name", "Balance"]

    def __init__(self, filepath: str | None = None):
        """
        Initialize the database.
        Creates the Excel file with headers if it doesn't already exist.

        Args:
            filepath: Optional custom path for the Excel file.
        """
        self.filepath = filepath or self.DB_FILE
        self._ensure_file_exists()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_file_exists(self) -> None:
        """Create the Excel workbook and header row if the file is missing."""
        if not os.path.exists(self.filepath):
            wb = Workbook()
            ws = wb.active
            ws.title = "Khata"
            ws.append(self.HEADERS)
            wb.save(self.filepath)

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a customer name for consistent lookups.
        Strips whitespace and converts to Title Case.
        """
        return name.strip().title()

    def _find_customer_row(self, ws, name: str) -> int | None:
        """
        Return the row number (1-indexed) where the customer exists,
        or None if not found. Skips the header row.
        """
        normalized = self._normalize_name(name)
        for row in range(2, ws.max_row + 1):
            cell_value = ws.cell(row=row, column=1).value
            if cell_value and self._normalize_name(str(cell_value)) == normalized:
                return row
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_transaction(self, name: str, amount: int | float) -> float:
        """
        Add a transaction for a customer.

        - If the customer exists, add `amount` to their current balance.
        - If the customer doesn't exist, create a new row.

        Args:
            name:   Customer name (case-insensitive).
            amount: Amount to add. Positive = credit/udhaar given,
                    Negative = payment received (jama).

        Returns:
            The updated balance after the transaction.
        """
        wb = load_workbook(self.filepath)
        ws = wb.active

        normalized_name = self._normalize_name(name)
        row = self._find_customer_row(ws, name)

        if row:
            # Customer exists — update balance
            current_balance = ws.cell(row=row, column=2).value or 0
            new_balance = current_balance + amount
            ws.cell(row=row, column=2, value=new_balance)
        else:
            # New customer — append a fresh row
            new_balance = amount
            ws.append([normalized_name, new_balance])

        wb.save(self.filepath)
        return new_balance

    def get_balance(self, name: str) -> float | None:
        """
        Get the current balance of a specific customer.

        Args:
            name: Customer name (case-insensitive).

        Returns:
            The balance as a number, or None if the customer is not found.
        """
        wb = load_workbook(self.filepath)
        ws = wb.active

        row = self._find_customer_row(ws, name)
        if row:
            return ws.cell(row=row, column=2).value or 0
        return None

    def get_all_ledgers(self) -> list[dict]:
        """
        Get a summary of all customers who have a balance greater than 0.

        Returns:
            A list of dicts: [{"name": "Customer", "balance": 500}, ...]
        """
        wb = load_workbook(self.filepath)
        ws = wb.active

        ledgers = []
        for row in range(2, ws.max_row + 1):
            name = ws.cell(row=row, column=1).value
            balance = ws.cell(row=row, column=2).value or 0
            if name and balance > 0:
                ledgers.append({"name": str(name), "balance": balance})

        return ledgers
