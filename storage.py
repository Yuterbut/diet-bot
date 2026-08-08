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
