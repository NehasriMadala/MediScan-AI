from pathlib import Path

from database.patient_repository import PatientRepository


def test_profile_persists_across_repository_restart(tmp_path: Path):
    db_path = tmp_path / "mediscan.db"
    repository = PatientRepository(db_path)

    saved = repository.save_profile(
        None, "V", 19, "Female", True, False, False, "Milk", "Vegetarian",
    )
    assert saved["profile_name"] == "V"
    assert saved["age"] == 19
    assert saved["diabetes"] is True
    assert saved["food_allergies"] == "Milk"

    restarted = PatientRepository(db_path)
    loaded = restarted.get_profile(saved["id"])
    assert loaded["profile_name"] == "V"
    assert loaded["food_allergies"] == "Milk"


def test_profile_update_and_independent_second_profile(tmp_path: Path):
    db_path = tmp_path / "mediscan.db"
    repository = PatientRepository(db_path)

    first = repository.save_profile(None, "V", 19, "Female", True, False, False, "Milk", "")
    second = repository.save_profile(None, "Asha", 32, "Female", False, False, False, "Peanuts", "")

    updated = repository.save_profile(
        first["id"], "V", 20, "Female", True, False, False, "Soy milk", "Vegetarian",
    )

    restarted = PatientRepository(db_path)
    assert restarted.get_profile(first["id"])["food_allergies"] == "Soy milk"
    assert restarted.get_profile(first["id"])["age"] == 20
    assert restarted.get_profile(second["id"])["profile_name"] == "Asha"
    assert restarted.get_profile(second["id"])["food_allergies"] == "Peanuts"


def test_profile_delete(tmp_path: Path):
    db_path = tmp_path / "mediscan.db"
    repository = PatientRepository(db_path)
    saved = repository.save_profile(None, "Delete Me", 25, "Male", False, False, False, "", "")
    repository.delete_profile(saved["id"])

    restarted = PatientRepository(db_path)
    assert restarted.get_profile(saved["id"]) is None
