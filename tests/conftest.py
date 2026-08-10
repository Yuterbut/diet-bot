"""
Общая настройка тестов.

1. Корень репозитория добавляется в sys.path, чтобы `import planner` и т.п.
   работали независимо от того, откуда запущен pytest.
2. Автофикстура глушит реальные HTTP-запросы: тесты не должны ходить в сеть
   ни при каких обстоятельствах (ни в Open Food Facts, ни в ИИ-провайдеров).
   Если тест забыл замокать requests — он упадёт с понятной ошибкой,
   а не будет молча зависеть от интернета и внешнего сервиса.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    import requests.adapters

    def _blocked(self, request, *args, **kwargs):
        raise AssertionError(
            f"Тест попытался сходить в сеть ({request.method} {request.url}). "
            "Замокайте requests."
        )

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", _blocked)
