from __future__ import annotations

from sqlite3 import IntegrityError

from pathlib import Path

from .db import get_connection, initialize_database


class ProfileValidationError(ValueError):
    pass


class PatientRepository:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path
        initialize_database(db_path) if db_path else initialize_database()

    def _connect(self):
        return get_connection(self.db_path) if self.db_path else get_connection()

    def list_profiles(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM patient_profiles ORDER BY updated_at DESC, profile_name ASC"
            ).fetchall()
        return [self._row(row) for row in rows]

    def get_profile(self, profile_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM patient_profiles WHERE id=?", (profile_id,)
            ).fetchone()
        return self._row(row) if row else None

    def find_by_name(self, profile_name: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM patient_profiles WHERE lower(profile_name)=lower(?)", (profile_name.strip(),)
            ).fetchone()
        return self._row(row) if row else None

    def save_profile(self, profile_id: int | None, profile_name: str, age: int | None,
                     sex: str, diabetes: bool, kidney_disease: bool, pregnancy: bool,
                     food_allergies: str, dietary_restrictions: str) -> dict:
        profile_name = profile_name.strip()
        if not profile_name:
            raise ProfileValidationError("Profile name is required.")
        if age is not None and not 0 <= age <= 120:
            raise ProfileValidationError("Age must be between 0 and 120.")

        with self._connect() as connection:
            try:
                if profile_id:
                    connection.execute(
                        """UPDATE patient_profiles SET
                           profile_name=?, age=?, sex=?, diabetes=?, kidney_disease=?, pregnancy=?,
                           food_allergies=?, dietary_restrictions=?, updated_at=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (profile_name, age, sex, int(diabetes), int(kidney_disease), int(pregnancy),
                         food_allergies.strip(), dietary_restrictions.strip(), profile_id),
                    )
                    saved_id = profile_id
                else:
                    cursor = connection.execute(
                        """INSERT INTO patient_profiles
                           (profile_name, age, sex, diabetes, kidney_disease, pregnancy,
                            food_allergies, dietary_restrictions)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (profile_name, age, sex, int(diabetes), int(kidney_disease), int(pregnancy),
                         food_allergies.strip(), dietary_restrictions.strip()),
                    )
                    saved_id = int(cursor.lastrowid)
                connection.commit()

                row = connection.execute(
                    "SELECT * FROM patient_profiles WHERE id=?", (saved_id,)
                ).fetchone()
                if row is None:
                    raise RuntimeError("Database did not return the saved profile.")
                return self._row(row)
            except IntegrityError as exc:
                connection.rollback()
                raise ProfileValidationError("A profile with this name already exists.") from exc
            except Exception:
                connection.rollback()
                raise

    def delete_profile(self, profile_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM patient_profiles WHERE id=?", (profile_id,))
            connection.commit()

    @staticmethod
    def _row(row) -> dict:
        item = dict(row)
        for field in ("diabetes", "kidney_disease", "pregnancy"):
            item[field] = bool(item[field])
        return item
