"""
Поиск точного КБЖУ по базе Open Food Facts (world.openfoodfacts.org) —
бесплатно, без ключа, ~3 млн товаров со штрихкодами, много российских брендов.

Логика: сначала ищем товар по названию в OFF (точные данные производителя).
Если не нашли ничего внятного (например, "тарелка борща" — это не товар
с этикеткой) — откатываемся на оценку через ИИ (ai_agent.estimate_food).
"""

import logging

import requests

import ai_agent

logger = logging.getLogger(__name__)

# world.openfoodfacts.org/cgi/search.pl (старый API) не умеет по-нормальному в
# полнотекстовый поиск и вдобавок периодически лежит; api/v2/search — только
# фильтры по тегам, без свободного текста. search.openfoodfacts.org — их новый
# search-a-licious сервис, реально ищет по названию/бренду.
SEARCH_URL = "https://search.openfoodfacts.org/search"
HEADERS = {"User-Agent": "AIDietBot/1.0 (Telegram diet planner bot)"}
TIMEOUT = 12


def _parse_grams(text: str | None) -> float | None:
    """'42g' / '52,7g' / '100 г' -> граммы. None, если не похоже на граммовку."""
    if not text or ("g" not in text.lower() and "г" not in text.lower()):
        return None
    digits = "".join(c for c in text if c.isdigit() or c in ".,").replace(",", ".")
    try:
        value = float(digits)
    except ValueError:
        return None
    return value if 1 <= value <= 2000 else None


def _from_off_hit(hit: dict) -> dict | None:
    n = hit.get("nutriments") or {}
    kcal_100g = n.get("energy-kcal_100g")
    if kcal_100g is None:
        return None

    name = hit.get("product_name") or "Продукт"
    grams = _parse_grams(hit.get("quantity")) or _parse_grams(hit.get("serving_size"))
    if grams is None or grams > 200:
        # Либо нет данных о фасовке, либо "quantity" — это вес всей упаковки
        # (пачка крупы, мешок муки), а не порция за один присест. Берём
        # стандартную порцию 100 г — концентрация КБЖУ из OFF всё равно точная.
        grams = 100.0
    scale = grams / 100.0

    return {
        "name": str(name)[:120],
        "portion": f"{round(grams)} г",
        "kcal": max(0, round(kcal_100g * scale)),
        "protein": max(0, round((n.get("proteins_100g") or 0) * scale)),
        "fat": max(0, round((n.get("fat_100g") or 0) * scale)),
        "carbs": max(0, round((n.get("carbohydrates_100g") or 0) * scale)),
        "note": "источник: Open Food Facts",
    }


def search(query: str) -> dict | None:
    """Ищет товар в Open Food Facts. None, если ничего подходящего не нашлось."""
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=TIMEOUT, params={
            "q": query,
            "page_size": 5,
            "fields": "product_name,nutriments,quantity,serving_size",
        })
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning("Open Food Facts недоступен: %s", e)
        return None

    for hit in data.get("hits", []):
        result = _from_off_hit(hit)
        if result:
            return result
    return None


def estimate(text: str) -> dict | None:
    """Единая точка входа для оценки КБЖУ: сначала точная база, потом ИИ-догадка."""
    off_result = search(text)
    if off_result:
        return off_result
    return ai_agent.estimate_food(text)
