from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import settings

EVENT_TS_FMT = "%Y-%m-%d %H:%M:%S"


class ComplianceStore:
    def __init__(self, filepath: str | None = None):
        self.filepath = Path(filepath or settings.compliance_store_file)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self.filepath.touch()

    def append_event(self, event_type: str, subject_id: str, payload: dict[str, Any]) -> None:
        row = {
            "timestamp": datetime.now().strftime(EVENT_TS_FMT),
            "event_type": event_type,
            "subject_id": subject_id,
            "payload": payload,
        }
        with self.filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    def export_subject_events(self, subject_id: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        with self.filepath.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if str(row.get("subject_id", "")).strip() == subject_id:
                    out.append(row)
        return out

    def delete_subject_events(self, subject_id: str) -> int:
        kept: list[str] = []
        removed = 0
        with self.filepath.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    kept.append(line)
                    continue
                if str(row.get("subject_id", "")).strip() == subject_id:
                    removed += 1
                else:
                    kept.append(json.dumps(row, ensure_ascii=True) + "\n")
        with self.filepath.open("w", encoding="utf-8") as f:
            f.writelines(kept)
        return removed

    def prune_old_events(self, retention_days: int | None = None) -> int:
        days = int(retention_days if retention_days is not None else settings.compliance_retention_days)
        cutoff = datetime.now() - timedelta(days=max(1, days))
        kept: list[str] = []
        removed = 0
        with self.filepath.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    kept.append(line)
                    continue
                ts_raw = str(row.get("timestamp", ""))
                try:
                    ts = datetime.strptime(ts_raw, EVENT_TS_FMT)
                except Exception:
                    kept.append(json.dumps(row, ensure_ascii=True) + "\n")
                    continue
                if ts < cutoff:
                    removed += 1
                else:
                    kept.append(json.dumps(row, ensure_ascii=True) + "\n")
        with self.filepath.open("w", encoding="utf-8") as f:
            f.writelines(kept)
        return removed
