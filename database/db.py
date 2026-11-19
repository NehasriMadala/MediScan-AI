from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "mediscan.db"


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: str | Path = DB_PATH) -> None:
    with get_connection(db_path) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS patient_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL UNIQUE,
                age INTEGER,
                sex TEXT NOT NULL DEFAULT '',
                diabetes INTEGER NOT NULL DEFAULT 0,
                kidney_disease INTEGER NOT NULL DEFAULT 0,
                pregnancy INTEGER NOT NULL DEFAULT 0,
                food_allergies TEXT NOT NULL DEFAULT '',
                dietary_restrictions TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                patient_id INTEGER,
                patient_name TEXT,
                report_name TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                report_date TEXT,
                document_type TEXT NOT NULL,
                extracted_parameters TEXT NOT NULL,
                document_preview TEXT NOT NULL,
                processing_status TEXT NOT NULL,
                FOREIGN KEY(patient_id) REFERENCES patient_profiles(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
