"""
Поиск точного КБЖУ по базе Open Food Facts (world.openfoodfacts.org) —
бесплатно, без ключа, ~3 млн товаров со штрихкодами, много российских брендов.

Логика: сначала ищем товар по названию в OFF (точные данные производителя).
Если не нашли ничего внятного (например, "тарелка борща" — это не товар
с этикеткой) — откатываемся на оценку через ИИ (ai_agent.estimate_food).

Отдельная история — счёт в штуках ("2 яблока", "3 яйца"). Вес штуки берём,
по убыванию доверия: из serving_size товара, если он описывает именно штуку;
из короткой таблицы _PIECE_FOODS; иначе отдаём запрос ИИ. Молча посчитать
"2 яблока" как 100 г нельзя — это и был баг, из-за которого дневник врал.
"""

import logging
import re

import requests

import ai_agent
import nutrition_data
import products

logger = logging.getLogger(__name__)

# world.openfoodfacts.org/cgi/search.pl (старый API) не умеет по-нормальному в
# полнотекстовый поиск и вдобавок периодически лежит; api/v2/search — только
# фильтры по тегам, без свободного текста. search.openfoodfacts.org — их новый
# search-a-licious сервис, реально ищет по названию/бренду.
SEARCH_URL = "https://search.openfoodfacts.org/search"
HEADERS = {"User-Agent": "AIDietBot/1.0 (Telegram diet planner bot)"}
TIMEOUT = 12


_GRAMS_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(килограмм(?:а|ов)?|кг|kg|грамм(?:а|ов)?|гр?|g)\b",
    re.IGNORECASE,
)
_KG_UNITS = {"кг", "kg", "килограмм", "килограмма", "килограммов"}

# служебные слова, не участвующие в проверке релевантности товара (предлоги/
# союзы + единицы веса — последние на случай, если не срослись с числом в _GRAMS_RE)
_STOPWORDS = {
    "и", "с", "со", "на", "из", "для", "без", "или", "по", "не", "от", "к", "за", "под",
    "г", "гр", "грамм", "грамма", "граммов", "кг", "килограмм", "килограмма", "килограммов",
    "шт", "штук", "штука", "штуки", "штуку",
}

# "2 шт", "3 штуки"
_PIECES_RE = re.compile(r"(?<![\d.,])(\d+)\s*шт\w*", re.IGNORECASE)
_PIECE_UNIT_RE = re.compile(r"\b(шт\w*|pcs?|piece|unit)\b", re.IGNORECASE)
# "2 яблока", "1 банан" — число и следом существительное. Слово от 3 букв,
# чтобы не цеплять "3 в 1" и остатки единиц измерения ("500 мл", "1 г").
_COUNT_RE = re.compile(r"(?<![\d.,])(\d+)\s*([а-яёa-z]{3,})", re.IGNORECASE)
_MAX_PIECES = 30
# предлоги, на которых заканчивается счётная группа: в "3 бутерброда с яйцом"
# считали бутерброды, а яйцо — начинка
_PHRASE_BREAK = {"и", "с", "со", "из", "для", "без", "или", "по", "на", "от", "к", "за", "под", "в", "во"}

# Средний вес СЪЕДОБНОЙ части одной штуки (банан без кожуры, яйцо без скорлупы).
# Список намеренно короткий: только то, где "штука" — естественная единица и вес
# почти не гуляет. Котлета, кусок пиццы, тарелка супа сюда не годятся — там вес
# зависит от рецепта, и лучше честная прикидка ИИ, чем выдуманное точное число.
# Ключи — из nutrition_data.NUTRI; для PER_PIECE_KEYS там КБЖУ уже за штуку.
_PIECE_FOODS = (
    (("перепелин",), "eggs_quail", 10),   # идёт до "яйц": перепелиные яйца — не куриные
    (("яйц", "яиц"), "eggs", 50),
    (("яблок",), "apple", 180),
    (("банан",), "banana", 120),
    (("авокадо",), "avocado", 150),
    (("мандарин",), "mandarin", 70),
    (("апельсин",), "orange", 130),
    (("груш",), "pear", 170),
    (("киви",), "kiwi", 75),
)


def _parse_grams(text: str | None) -> float | None:
    """'42g' / '52,7g' / '100 г' / '1 килограмм' -> граммы. None, если в тексте
    не нашлось похожего на граммовку фрагмента."""
    if not text:
        return None
    match = _GRAMS_RE.search(text)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", "."))
    except ValueError:
        return None
    if match.group(2).lower() in _KG_UNITS:
        value *= 1000
    return value if 1 <= value <= 2000 else None


def _piece_food(text: str) -> tuple[str, float] | None:
    """Находит в тексте знакомую штучную еду -> (ключ NUTRI, вес штуки).
    Морфологию не разбираем: хвост до трёх букв покрывает "яблоко/яблока/яблок",
    но отсекает "банановый кекс" — там банан не штука, а прилагательное."""
    words = re.findall(r"[а-яёa-z]+", text.lower())
    for stems, key, grams in _PIECE_FOODS:
        for stem in stems:
            if any(re.fullmatch(stem + r"[а-яё]{0,3}", w) for w in words):
                return key, float(grams)
    return None


def _parse_pieces(text: str | None) -> float | None:
    """Сколько штук съедено: "2 яблока" -> 2, "3 шт" -> 3, голое "яблоко" -> 1.
    None, если про штуки речи нет. Явный вес всегда важнее счёта."""
    if not text or _parse_grams(text) is not None:
        return None

    match = _PIECES_RE.search(text)
    if match is None:
        count_match = _COUNT_RE.search(text)
        # "5 килограмм" — не пять штук: вес не влез в лимит _parse_grams, но
        # единицей веса быть не перестал
        if count_match and count_match.group(2).lower() not in _STOPWORDS:
            match = count_match
    if match:
        count = int(match.group(1))
        return float(count) if 1 <= count <= _MAX_PIECES else None

    # Название без количества — это одна штука, а не 100 г. Только если запрос
    # из одного слова: в "банановый смузи" штук нет.
    if not any(c.isdigit() for c in text) and len(text.split()) == 1 and _piece_food(text):
        return 1.0
    return None


def _counted_food(text: str) -> tuple[str, float] | None:
    """Штучная еда, к которой относится счёт. Смотрим только пару слов сразу
    после числа: иначе "3 бутерброда с яйцом" превратятся в три яйца."""
    match = _PIECES_RE.search(text) or _COUNT_RE.search(text)
    if match is None:
        return _piece_food(text)  # числа нет — голое название
    window = []
    for word in re.findall(r"[а-яёa-z]+", text[match.start():].lower())[:3]:
        if word in _PHRASE_BREAK:
            break
        if not word.startswith("шт"):  # "2 шт яблок" — "шт" не мешает
            window.append(word)
    return _piece_food(" ".join(window))


def _serving_piece_grams(serving_size: str | None) -> float | None:
    """Вес штуки из serving_size товара ("1 шт (180 г)"). None, если порция
    задана просто весом ("30 г") — это порция производителя, а не штука."""
    if not serving_size or not _PIECE_UNIT_RE.search(serving_size):
        return None
    count = _PIECES_RE.search(serving_size)
    if count and int(count.group(1)) != 1:  # "2 шт (60 г)" — вес двух печений
        return None
    grams = _parse_grams(serving_size)
    return grams if grams is not None and 5 <= grams <= 500 else None


def _piece_portion(pieces: float, grams: float) -> str:
    # Пользователь считал штуки — в карточке подтверждения так и пишем,
    # иначе "360 г" выглядит как будто бот что-то взвесил сам
    return f"{round(pieces)} шт (≈{round(grams)} г)"


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[а-яёa-z]+", _GRAMS_RE.sub(" ", text.lower()))
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _is_relevant(query: str, product_name: str | None) -> bool:
    """Без этой проверки полнотекстовый поиск OFF подсовывает случайные
    совпадения по одному слову — например, на "жареная картошка" находился
    товар "Сырок Картошка"."""
    query_words = _significant_words(query)
    if not query_words:
        return True
    name = (product_name or "").lower()
    matched = sum(1 for w in query_words if w in name)
    return matched / len(query_words) > 0.5


def _from_off_hit(hit: dict, user_grams: float | None = None,
                  pieces: float | None = None, piece_grams: float | None = None) -> dict | None:
    n = hit.get("nutriments") or {}
    kcal_100g = n.get("energy-kcal_100g")
    if kcal_100g is None:
        return None

    name = hit.get("product_name") or "Продукт"
    portion = None
    if user_grams is not None:
        grams = user_grams
    elif pieces is not None:
        per_piece = _serving_piece_grams(hit.get("serving_size")) or piece_grams
        if per_piece is None:
            # Вес штуки неоткуда взять. Посчитать штуки как 100 г — тот самый
            # уверенный неверный ответ, от которого уходим: пусть отвечает ИИ.
            return None
        grams = per_piece * pieces
        portion = _piece_portion(pieces, grams)
    else:
        grams = _parse_grams(hit.get("quantity")) or _parse_grams(hit.get("serving_size"))
        if grams is None or grams > 200:
            # Либо нет данных о фасовке, либо "quantity" — это вес всей упаковки
            # (пачка крупы, мешок муки), а не порция за один присест. Берём
            # стандартную порцию 100 г — концентрация КБЖУ из OFF всё равно точная.
            grams = 100.0
    scale = grams / 100.0

    return {
        "name": str(name)[:120],
        "portion": portion or f"{round(grams)} г",
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

    user_grams = _parse_grams(query)
    pieces = _parse_pieces(query)
    food = _counted_food(query) if pieces is not None else None
    piece_grams = food[1] if food else None
    for hit in data.get("hits", []):
        if not _is_relevant(query, hit.get("product_name")):
            continue
        result = _from_off_hit(hit, user_grams, pieces, piece_grams)
        if result:
            return result
    return None


def _from_local_pieces(text: str) -> dict | None:
    """Ответ по своей таблице: OFF на "2 яблока" часто промахивается мимо
    проверки релевантности (падежи), но средний вес яблока мы и так знаем."""
    pieces = _parse_pieces(text)
    food = _counted_food(text) if pieces is not None else None
    if not food:
        return None
    key, per_piece = food
    values = nutrition_data.NUTRI.get(key)
    if not values:
        return None

    kcal, protein, fat, carbs = values[:4]
    # В NUTRI яйца/авокадо лежат за штуку, остальное — за 100 г
    scale = pieces if key in nutrition_data.PER_PIECE_KEYS else pieces * per_piece / 100.0
    name = (products.PRODUCTS.get(key) or {}).get("name") or key
    return {
        "name": str(name)[:120],
        "portion": _piece_portion(pieces, pieces * per_piece),
        "kcal": max(0, round(kcal * scale)),
        "protein": max(0, round(protein * scale)),
        "fat": max(0, round(fat * scale)),
        "carbs": max(0, round(carbs * scale)),
        "note": "оценка по среднему весу штуки",
    }


def estimate(text: str) -> dict | None:
    """Единая точка входа для оценки КБЖУ: сначала точная база, потом своя
    таблица штучных продуктов, потом ИИ-догадка."""
    off_result = search(text)
    if off_result:
        return off_result
    local_pieces = _from_local_pieces(text)
    if local_pieces:
        return local_pieces
    return ai_agent.estimate_food(text)
