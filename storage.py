"""
Простое хранилище данных пользователей в JSON-файле.

Зачем нужно: бот должен помнить выбранный план и отметки "куплено" между
сообщениями. Полноценная база данных для такой задачи избыточна.

Файл создаётся автоматически рядом с кодом (data.json).
"""

import json
import os
import tempfile
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data.json"


def _read_all() -> dict:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # файл повреждён — начинаем с чистого листа, чтобы бот не падал
        return {}


def _write_all(data: dict) -> None:
    # пишем через временный файл, чтобы не потерять данные при сбое записи
    directory = DATA_FILE.parent
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, DATA_FILE)
    except OSError:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def get_user(chat_id: int) -> dict:
    return _read_all().get(str(chat_id), {})


def save_user(chat_id: int, patch: dict) -> dict:
    """Обновляет данные пользователя, возвращает результат."""
    data = _read_all()
    user = data.get(str(chat_id), {})
    user.update(patch)
    data[str(chat_id)] = user
    _write_all(data)
    return user


def clear_user(chat_id: int) -> None:
    data = _read_all()
    data.pop(str(chat_id), None)
    _write_all(data)


# --- Пользовательские правки цен (команда /цена) ---

def get_price_overrides() -> dict:
    return _read_all().get("_prices", {})


def set_price_override(product_key: str, price: float) -> None:
    data = _read_all()
    prices = data.get("_prices", {})
    prices[product_key] = price
    data["_prices"] = prices
    _write_all(data)


# --- ИИ-диетолог: анкета, дневник питания, напоминания ---

def update_profile(chat_id: int, patch: dict) -> dict:
    """Точечно обновляет вложенный словарь user['profile'] (не затирая остальные поля)."""
    data = _read_all()
    user = data.get(str(chat_id), {})
    profile = dict(user.get("profile", {}))
    profile.update(patch)
    user["profile"] = profile
    data[str(chat_id)] = user
    _write_all(data)
    return user


def add_diary_entry(chat_id: int, entry: dict) -> dict:
    """Добавляет запись в дневник питания. Хранит не больше последних 500 записей."""
    data = _read_all()
    user = data.get(str(chat_id), {})
    diary = list(user.get("diary", []))
    diary.append(entry)
    if len(diary) > 500:
        diary = diary[-500:]
    user["diary"] = diary
    data[str(chat_id)] = user
    _write_all(data)
    return user


def get_diary(chat_id: int) -> list:
    return _read_all().get(str(chat_id), {}).get("diary", [])


def mark_reminded(chat_id: int, date_str: str, slot: str) -> None:
    """Отмечает, что напоминание на этот слот в эту дату уже отправлено (без дублей)."""
    data = _read_all()
    user = data.get(str(chat_id), {})
    reminded = dict(user.get("reminded", {}))
    day_list = list(reminded.get(date_str, []))
    if slot not in day_list:
        day_list.append(slot)
    reminded[date_str] = day_list
    if len(reminded) > 3:
        for key in sorted(reminded)[:-3]:
            reminded.pop(key, None)
    user["reminded"] = reminded
    data[str(chat_id)] = user
    _write_all(data)


def all_users() -> dict:
    """Все пользователи бота (для рассылки напоминаний по крону), без служебных ключей."""
    data = _read_all()
    return {k: v for k, v in data.items() if k != "_prices" and k.isdigit()}


def update_checkin(chat_id: int, date_str: str, slot: str, patch: dict) -> None:
    """Состояние опроса о приёме пищи: {"sent": "HH:MM", "followup_sent": bool, "responded": bool}.
    Хранит только последние 3 даты, чтобы файл не рос бесконечно."""
    data = _read_all()
    user = data.get(str(chat_id), {})
    checkins = dict(user.get("checkins", {}))
    day = dict(checkins.get(date_str, {}))
    slot_state = dict(day.get(slot, {}))
    slot_state.update(patch)
    day[slot] = slot_state
    checkins[date_str] = day
    if len(checkins) > 3:
        for key in sorted(checkins)[:-3]:
            checkins.pop(key, None)
    user["checkins"] = checkins
    data[str(chat_id)] = user
    _write_all(data)
