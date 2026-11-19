from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Iterable


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mediscan.db"


class HistoryStore:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    patient_id INTEGER NOT NULL,
                    patient_name TEXT,
                    report_name TEXT NOT NULL,
                    upload_date TEXT NOT NULL,
                    report_date TEXT,
                    document_type TEXT NOT NULL,
                    extracted_parameters TEXT NOT NULL,
                    document_preview TEXT NOT NULL,
                    processing_status TEXT NOT NULL,
                    FOREIGN KEY(patient_id) REFERENCES patient_profiles(id) ON DELETE CASCADE
                );
            """)

    def add_patient(self, display_name: str) -> str:
        patient_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO patients(patient_id, display_name, created_at) VALUES (?, ?, datetime('now'))",
                (patient_id, display_name),
            )
        return patient_id

    def list_patients(self) -> list[dict]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM patients ORDER BY created_at DESC")]

    def save_report(self, patient_id: str | int, report_name: str, report_date: str | None,
                    document_type: str, extracted_parameters: list[dict], document_preview: dict,
                    processing_status: str = "processed") -> str:
        report_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO reports(report_id, patient_id, patient_name, report_name, upload_date, report_date,
                   document_type, extracted_parameters, document_preview, processing_status)
                   VALUES (?, ?, NULL, ?, datetime('now'), ?, ?, ?, ?, ?)""",
                (report_id, patient_id, report_name, report_date, document_type,
                 json.dumps(extracted_parameters, ensure_ascii=False),
                 json.dumps(document_preview, ensure_ascii=False), processing_status),
            )
        return report_id

    def list_reports(self, patient_id: str | int) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reports WHERE patient_id=? ORDER BY COALESCE(report_date, upload_date) DESC",
                (patient_id,),
            ).fetchall()
        reports = []
        for row in rows:
            item = dict(row)
            item["extracted_parameters"] = json.loads(item["extracted_parameters"])
            item["document_preview"] = json.loads(item["document_preview"])
            reports.append(item)
        return reports

    def delete_report(self, report_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM reports WHERE report_id=?", (report_id,))
