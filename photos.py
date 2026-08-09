"""
Поиск фото блюда через Unsplash (для карточки рецепта).
Без UNSPLASH_ACCESS_KEY просто ничего не находит — фото молча не показывается,
бот при этом не ломается (см. философию graceful degradation в ai_agent.py).
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.unsplash.com/search/photos"
TIMEOUT = 10


def search_dish_photo(query: str) -> str | None:
    """Возвращает URL картинки (или None, если ключа нет / ничего не нашлось)."""
    key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not key:
        return None
    try:
        resp = requests.get(SEARCH_URL, timeout=TIMEOUT, headers={
            "Authorization": f"Client-ID {key}",
        }, params={"query": f"{query} food", "per_page": 1, "orientation": "landscape"})
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None
        return results[0]["urls"]["regular"]
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning("Unsplash недоступен: %s", e)
        return None
