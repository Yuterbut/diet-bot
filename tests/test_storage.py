"""
Тесты хранилища. Главный из них — про параллельную запись: до появления
блокировки пять одновременных писателей теряли двух пользователей целиком.
"""

import multiprocessing

import pytest

import storage


@pytest.fixture(autouse=True)
def tmp_data_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_FILE", tmp_path / "data.json")


# --- базовые операции ---

def test_get_user_returns_empty_dict_for_unknown_chat():
    assert storage.get_user(12345) == {}


def test_save_user_merges_patch_without_dropping_old_keys():
    storage.save_user(1, {"goal": "loss"})
    storage.save_user(1, {"region": "center"})
    user = storage.get_user(1)
    assert user == {"goal": "loss", "region": "center"}


def test_clear_user_removes_only_that_user():
    storage.save_user(1, {"goal": "loss"})
    storage.save_user(2, {"goal": "gain"})
    storage.clear_user(1)
    assert storage.get_user(1) == {}
    assert storage.get_user(2) == {"goal": "gain"}


def test_update_profile_keeps_other_top_level_fields():
    storage.save_user(1, {"goal": "loss"})
    storage.update_profile(1, {"age": 30})
    storage.update_profile(1, {"height": 180})
    user = storage.get_user(1)
    assert user["goal"] == "loss"
    assert user["profile"] == {"age": 30, "height": 180}


def test_diary_keeps_only_last_500_entries():
    for i in range(520):
        storage.add_diary_entry(1, {"n": i})
    diary = storage.get_diary(1)
    assert len(diary) == 500
    assert diary[0]["n"] == 20
    assert diary[-1]["n"] == 519


def test_mark_reminded_is_idempotent_and_keeps_three_dates():
    storage.mark_reminded(1, "2026-08-10", "breakfast")
    storage.mark_reminded(1, "2026-08-10", "breakfast")
    assert storage.get_user(1)["reminded"]["2026-08-10"] == ["breakfast"]

    for day in ("2026-08-11", "2026-08-12", "2026-08-13"):
        storage.mark_reminded(1, day, "lunch")
    reminded = storage.get_user(1)["reminded"]
    assert len(reminded) == 3
    assert "2026-08-10" not in reminded


def test_update_checkin_merges_slot_state():
    storage.update_checkin(1, "2026-08-10", "breakfast", {"sent": "08:00"})
    storage.update_checkin(1, "2026-08-10", "breakfast", {"responded": True})
    state = storage.get_user(1)["checkins"]["2026-08-10"]["breakfast"]
    assert state == {"sent": "08:00", "responded": True}


def test_all_users_skips_service_keys():
    storage.save_user(1, {"goal": "loss"})
    storage.set_price_override("oats", 70)
    assert list(storage.all_users()) == ["1"]


def test_price_overrides_survive_user_writes():
    storage.set_price_override("oats", 70)
    storage.save_user(1, {"goal": "loss"})
    assert storage.get_price_overrides() == {"oats": 70}


def test_corrupted_file_does_not_raise():
    storage.DATA_FILE.write_text("{это не json", encoding="utf-8")
    assert storage.get_user(1) == {}
    storage.save_user(1, {"goal": "loss"})
    assert storage.get_user(1) == {"goal": "loss"}


# --- параллельная запись ---

def _hammer(chat_id):
    for i in range(25):
        storage.save_user(chat_id, {f"key{i}": i})


def test_concurrent_writers_do_not_lose_data():
    """Регрессия: без блокировки «прочитать — изменить — записать» параллельные
    процессы затирали работу друг друга. На PythonAnywhere воркеров несколько,
    и запись из вебхука легко совпадает с записью из крона напоминаний."""
    procs = [multiprocessing.Process(target=_hammer, args=(uid,)) for uid in range(1, 5)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)

    for uid in range(1, 5):
        user = storage.get_user(uid)
        assert len(user) == 25, f"пользователь {uid}: осталось {len(user)} ключей из 25"
