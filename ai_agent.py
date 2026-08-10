"""
Обёртка над бесплатным ИИ (GitHub Models) с фоллбеком на OpenAI.

GitHub Models: https://github.com/marketplace/models — бесплатно по обычному
GitHub PAT (GITHUB_MODELS_TOKEN), лимиты по запросам в минуту/день.
Если GitHub Models недоступен (лимит, сбой) и задан OPENAI_API_KEY — пробуем
через OpenAI тем же форматом сообщений.

Все функции никогда не бросают исключение наружу: при сбое возвращают
None / понятную заглушку, чтобы бот не падал, если ИИ недоступен.
"""

import base64
import json
import logging
import math
import os
import re

import requests

from nutrition_data import (
    DEFAULT_KCAL_THRESHOLDS,
    MEAL_KCAL_THRESHOLDS,
    NUTRI,
    PER_PIECE_KEYS,
    compute_goals,
    compute_macros,
    compute_tags,
)
from products import PRODUCTS

logger = logging.getLogger(__name__)

GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_URL_LEGACY = "https://models.inference.ai.azure.com/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

TIMEOUT = 25


def _post(url: str, headers: dict, payload: dict) -> dict | None:
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        logger.warning("AI request error (%s): %s", url, e)
        return None
    if resp.status_code >= 400:
        logger.warning("AI request failed (%s): %s %s", url, resp.status_code, resp.text[:300])
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def _extract_text(data: dict | None) -> str | None:
    if not data:
        return None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def _github_models_chat(messages: list, temperature: float, max_tokens: int) -> str | None:
    token = os.getenv("GITHUB_MODELS_TOKEN")
    if not token:
        return None
    model = os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4o-mini")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

    text = _extract_text(_post(GITHUB_MODELS_URL, headers, payload))
    if text is not None:
        return text

    # старый эндпоинт GitHub Models — модель там без префикса издателя
    legacy_model = model.split("/", 1)[-1]
    legacy_payload = {**payload, "model": legacy_model}
    return _extract_text(_post(GITHUB_MODELS_URL_LEGACY, headers, legacy_payload))


def _groq_chat(messages: list, temperature: float, max_tokens: int) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    return _extract_text(_post(GROQ_URL, headers, payload))


def _openai_chat(messages: list, temperature: float, max_tokens: int) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    return _extract_text(_post(OPENAI_URL, headers, payload))


def chat(messages: list, temperature: float = 0.4, max_tokens: int = 700) -> str | None:
    """Единая точка входа: GitHub Models -> Groq -> OpenAI -> None.

    GitHub Models по состоянию на сейчас периодически недоступен (retirement
    brownout / 410), поэтому Groq — фактически основной бесплатный провайдер,
    если задан GROQ_API_KEY."""
    for provider in (_github_models_chat, _groq_chat, _openai_chat):
        text = provider(messages, temperature, max_tokens)
        if text is not None:
            return text.strip()
    logger.error("AI недоступен: GitHub Models, Groq и OpenAI не ответили")
    return None


# ---------- Оценка КБЖУ по свободному тексту ----------

FOOD_ESTIMATE_SYSTEM = """Ты — нутрициолог-эксперт. Пользователь пишет, что съел (по-русски, часто без граммовки).
Твоя задача — оценить порцию и вернуть КБЖУ.

Правила:
- Если граммовка не указана — прикинь стандартную порцию (например, "сникерс" ≈ 50 г батончик).
- Если описано несколько продуктов — просуммируй в одну запись.
- Отвечай СТРОГО валидным JSON без markdown, без пояснений вокруг, вот такой формы:
{"name": "короткое название на русском", "portion": "например, 50 г", "kcal": 250, "protein": 3, "fat": 12, "carbs": 33, "note": "короткий комментарий если оценка очень грубая, иначе пустая строка"}
Числа — целые, в разумных пределах (kcal 0-3000 на одну запись). Если совсем не можешь понять, что за еда — верни name как есть и note "не удалось точно оценить, значения приблизительные"."""


def _parse_food_json(text: str, fallback_name: str) -> dict | None:
    """Общий разбор ответа ИИ вида {"name":..,"kcal":..,...} — используется и для
    текстовой, и для фото-оценки еды."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        logger.warning("Не удалось найти JSON в ответе ИИ: %s", text[:200])
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Невалидный JSON от ИИ: %s", text[:200])
        return None

    try:
        return {
            "name": str(data.get("name") or fallback_name)[:120],
            "portion": str(data.get("portion") or "")[:60],
            "kcal": max(0, min(3000, round(float(data.get("kcal", 0))))),
            "protein": max(0, min(300, round(float(data.get("protein", 0))))),
            "fat": max(0, min(300, round(float(data.get("fat", 0))))),
            "carbs": max(0, min(500, round(float(data.get("carbs", 0))))),
            "note": str(data.get("note") or "")[:200],
        }
    except (TypeError, ValueError):
        return None


def estimate_food(description: str) -> dict | None:
    """Оценивает КБЖУ по свободному описанию еды. Возвращает dict или None при сбое ИИ."""
    messages = [
        {"role": "system", "content": FOOD_ESTIMATE_SYSTEM},
        {"role": "user", "content": description.strip()},
    ]
    text = chat(messages, temperature=0.2, max_tokens=300)
    if text is None:
        return None
    return _parse_food_json(text, fallback_name=description.strip())


# ---------- Оценка КБЖУ по фото еды (Groq vision, фоллбек OpenAI) ----------

FOOD_IMAGE_PROMPT = """Посмотри на фото еды и оцени её КБЖУ (калории, белки, жиры, углеводы).
Определи блюдо/продукты на фото и прикинь размер порции по виду тарелки/упаковки.

Отвечай СТРОГО валидным JSON без markdown, вот такой формы:
{"name": "короткое название на русском", "portion": "например, 250 г", "kcal": 450, "protein": 20, "fat": 15, "carbs": 55, "note": "короткий комментарий, если оценка грубая"}
Числа целые, kcal в пределах 0-3000. Если на фото не еда или не видно — верни kcal: 0 и в note напиши "не удалось распознать еду на фото"."""


def _groq_vision_chat(content: list, temperature: float, max_tokens: int) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    model = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": content}],
               "temperature": temperature, "max_tokens": max_tokens}
    return _extract_text(_post(GROQ_URL, headers, payload))


def _openai_vision_chat(content: list, temperature: float, max_tokens: int) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": content}],
               "temperature": temperature, "max_tokens": max_tokens}
    return _extract_text(_post(OPENAI_URL, headers, payload))


def estimate_food_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict | None:
    """Оценивает КБЖУ по фото еды. Возвращает dict или None, если vision-модели недоступны."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    content = [
        {"type": "text", "text": FOOD_IMAGE_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
    ]

    text = _groq_vision_chat(content, temperature=0.2, max_tokens=300)
    if text is None:
        text = _openai_vision_chat(content, temperature=0.2, max_tokens=300)
    if text is None:
        logger.error("Vision AI недоступен: ни Groq, ни OpenAI не ответили")
        return None
    return _parse_food_json(text, fallback_name="Фото еды")


# ---------- Свободное общение с диетологом ----------

DIETITIAN_SYSTEM = """Ты — персональный ИИ-диетолог в Telegram-боте. Помогаешь пользователю с питанием:
отвечаешь на вопросы про еду, калорийность, помогаешь скорректировать план.

Тон: дружелюбный, короткий, без осуждения — это Telegram, а не лонгрид. Эмодзи умеренно.

Границы (важно):
- Ты не врач. Не ставь диагнозы, не давай медицинских рекомендаций (дозировки, лечение болезней питанием).
  При медицинских вопросах советуй обратиться к врачу/диетологу.
- Не советуй экстремальный дефицит калорий (менее ~1200 ккал/день) и не поощряй пропуск приёмов пищи как способ похудеть.
- Если видишь признаки расстройства пищевого поведения — мягко предложи поддержку специалиста, без точных цифр по ограничениям.
- Не критикуй выбор еды пользователя и не используй стыдящие формулировки.
- Отвечай коротко (2-6 предложений), без длинных списков, если не просят подробностей."""


def dietitian_chat(profile_context: str, user_message: str, history: list | None = None) -> str | None:
    """profile_context — краткое текстовое summary профиля/дневника пользователя за сегодня."""
    messages = [{"role": "system", "content": DIETITIAN_SYSTEM}]
    if profile_context:
        messages.append({"role": "system", "content": f"Контекст пользователя:\n{profile_context}"})
    for turn in (history or [])[-6:]:
        messages.append(turn)
    messages.append({"role": "user", "content": user_message.strip()})
    return chat(messages, temperature=0.5, max_tokens=500)


# ---------- Классификация ответа на опрос "поел ли ты?" ----------

CHECKIN_CLASSIFY_SYSTEM = """Пользователь отвечает на вопрос о приёме пищи ("Позавтракал?" и т.п.).
Определи по его ответу одно из трёх:
- OK — да, поел точно по плану, без изменений (например: "да", "да, позавтракал", "все съел как обычно")
- SKIP — не ел / пропустил приём пищи (например: "нет", "не успел", "пропустил", "забыл")
- OTHER — ел, но по-другому / другое блюдо / с изменениями — в ответе есть описание еды

Ответь ОДНИМ словом без пояснений: OK, SKIP или OTHER."""


def classify_checkin_reply(text: str) -> str:
    """Классифицирует свободный текстовый ответ на опрос о приёме пищи. Безопасный дефолт — OTHER
    (трактуем как описание еды), если ИИ недоступен или ответил что-то непонятное."""
    messages = [
        {"role": "system", "content": CHECKIN_CLASSIFY_SYSTEM},
        {"role": "user", "content": text.strip()},
    ]
    result = chat(messages, temperature=0.0, max_tokens=5)
    if result:
        word = result.strip().upper()
        if word in ("OK", "SKIP", "OTHER"):
            return word
    return "OTHER"


# ---------- Еженедельный отчёт ----------

REPORT_SYSTEM = """Ты — ИИ-диетолог. На основе данных дневника питания пользователя за неделю
напиши короткий дружелюбный отчёт для Telegram (не более 8-10 строк):
- в какие дни укладывался в норму калорий, в какие нет;
- перекос по белкам/жирам/углеводам, если он есть;
- 1-2 практичных совета на следующую неделю.
Без морализаторства и медицинских советов. Используй *жирный* для акцентов (Telegram Markdown)."""


def weekly_report(summary_text: str) -> str | None:
    messages = [
        {"role": "system", "content": REPORT_SYSTEM},
        {"role": "user", "content": summary_text},
    ]
    return chat(messages, temperature=0.4, max_tokens=500)


# ---------- Генерация нового блюда (когда статической базы не хватает) ----------
#
# Главная защита от выдуманных калорий: модель НЕ сообщает КБЖУ вообще.
# Она называет только ключи продуктов из products.PRODUCTS и граммовку, а
# калории/БЖУ/теги/цели считает nutrition_data — тем же кодом, которым
# посчитана вся статическая база блюд. Поэтому ошибиться в цифрах ИИ
# физически не может: любые его числа игнорируются.
#
# Побочный выигрыш: раз состав блюда — реальные ключи продуктов, список
# покупок и расчёт стоимости в planner.py работают с таким блюдом без
# единой правки.
#
# Всё, что не прошло проверку, выбрасывается ЦЕЛИКОМ: лучше вернуть None и
# оставить блюдо из статической базы, чем подсунуть пользователю блюдо с
# неизвестным продуктом (упадёт список покупок) или нереальной порцией.

MEAL_TYPE_NAMES_RU = {
    "breakfast": "завтрак",
    "lunch": "обед",
    "dinner": "ужин",
    "snack": "перекус",
}

COOKING_LEVEL_HINTS = {
    "simple": 'Готовить пользователь почти не умеет: блюдо максимально простое, '
              'difficulty строго "easy", time не больше 20 минут, минимум операций '
              '(сварить, смешать, обжарить на одной сковороде).',
    "medium": "Пользователь готовит на среднем уровне: можно обжарку, тушение, духовку, до 40 минут.",
    "advanced": "Пользователь готовит уверенно: можно многоступенчатые блюда, соусы, запекание, до 60 минут.",
}

# Границы разумного в ответе модели. Для сравнения — в статической базе
# максимум 5 ингредиентов, 300 г одного продукта, 540 г порции целиком,
# 2 шт штучного продукта и 3 шага рецепта, так что запас многократный.
MAX_INGREDIENTS = 12
MAX_GRAMS_PER_INGREDIENT = 1000
MAX_PIECES_PER_INGREDIENT = 6
MAX_TOTAL_GRAMS = 1500
MAX_STEPS = 10
MAX_TIME_MINUTES = 240
MAX_STEP_CHARS = 300
ALLOWED_DIFFICULTY = ("easy", "medium", "hard")
SIMPLE_LEVEL_MAX_TIME = 20
# Сколько продуктов вообще имеет смысл перечислять в промпте и при скольких
# разрешённых продуктах просить блюдо уже бессмысленно.
MAX_PROMPT_KEYS = 250
MIN_ALLOWED_KEYS = 3

MEAL_GENERATE_SYSTEM = """Ты — шеф-повар, который придумывает блюда из строго заданного набора продуктов.
Придумай ОДНО блюдо на одну порцию для указанного приёма пищи.

Правила (нарушение любого — ответ будет отброшен целиком):
- Состав блюда — ТОЛЬКО из списка разрешённых продуктов. Ключи писать ровно так, как в списке
  (латиницей, без изменений). Нет ключа в списке — значит, продукта нет: ни соли, ни масла, ни специй.
- Количество: обычные продукты — в ГРАММАХ или МЛ на одну порцию, целым числом.
  Продукты, помеченные "штуками" — в штуках (можно дробно: 0.5).
- От 2 до 6 ингредиентов, порция человеческого размера (не килограмм одного продукта).
- НЕ пиши калории, белки, жиры, углеводы, теги, цели — их посчитают по составу без тебя,
  любые твои числа по КБЖУ будут проигнорированы.
- name — короткое название блюда по-русски (до 60 знаков), без слова "рецепт" и без кавычек.
- difficulty — "easy" или "medium". time — минуты приготовления, целое число.
- cuisine — одним словом латиницей: russian, italian, asian, mediterranean, mexican, american,
  middle_eastern, french, international.
- steps — 1-4 очень коротких шага по-русски в повелительном наклонении, как в кулинарной книге:
  "Гречку отварить 15 мин.", "Курицу обжарить 5 мин, добавить овощи."

Отвечай СТРОГО валидным JSON без markdown и без пояснений вокруг, вот такой формы:
{"name": "Гречка с курицей и брокколи", "cuisine": "russian", "difficulty": "easy", "time": 25, "ingredients": {"chicken": 150, "buckwheat": 70, "broccoli": 100, "olive_oil": 10}, "steps": ["Гречку отварить 15 мин.", "Курицу обжарить 5 мин, добавить брокколи и готовую гречку."]}"""


def _kcal_bounds(meal_type: str) -> tuple[int, int]:
    """Правдоподобный диапазон калорийности блюда для этого приёма пищи.

    Числа не придуманы заново — это те же пороги, по которым compute_goals
    решает, какой цели подходит блюдо: low - 50 — граница, ниже которой блюдо
    не годится даже под набор массы, а верхнюю берём с двойным запасом от high
    (в статической базе порций крупнее нет)."""
    low, high = MEAL_KCAL_THRESHOLDS.get(meal_type, DEFAULT_KCAL_THRESHOLDS)
    return low - 50, high * 2


def _known_allowed_keys(allowed_product_keys) -> list:
    """Разрешённые ключи, которые реально есть и в справочнике покупок, и в
    таблице питательности — иначе блюдо нельзя ни посчитать, ни купить."""
    keys, seen = [], set()
    for key in allowed_product_keys or ():
        if not isinstance(key, str) or key in seen:
            continue
        if key in PRODUCTS and key in NUTRI:
            seen.add(key)
            keys.append(key)
    return keys


def _meal_request_text(meal_type: str, keys: list, cooking_level: str | None, goal: str | None) -> str:
    low, high = MEAL_KCAL_THRESHOLDS.get(meal_type, DEFAULT_KCAL_THRESHOLDS)
    kcal_hint = {
        "loss": f"не больше {high} ккал",
        "gain": f"не меньше {low} ккал, сытное",
        "maintain": f"примерно {low}-{high} ккал",
    }.get(goal or "", f"примерно {low}-{high} ккал")

    lines = [f"Приём пищи: {MEAL_TYPE_NAMES_RU.get(meal_type, meal_type)}.",
             f"Размер порции: {kcal_hint}."]
    hint = COOKING_LEVEL_HINTS.get(cooking_level or "")
    if hint:
        lines.append(hint)
    lines.append("")
    lines.append("Разрешённые продукты (ключ — что это):")
    for key in keys[:MAX_PROMPT_KEYS]:
        product = PRODUCTS[key]
        suffix = " [штуками]" if key in PER_PIECE_KEYS else ""
        lines.append(f"{key} — {product['name']}{suffix}")
    return "\n".join(lines)


def _validate_ai_ingredients(raw, allowed: set) -> dict | None:
    """Состав от ИИ -> {ключ продукта: количество} или None, если что-то не так."""
    if not isinstance(raw, dict) or not 1 <= len(raw) <= MAX_INGREDIENTS:
        return None

    ingredients: dict[str, float] = {}
    total_grams = 0.0
    for key, amount in raw.items():
        if not isinstance(key, str) or key not in allowed:
            logger.warning("ИИ предложил неразрешённый продукт '%s'", key)
            return None
        if key not in PRODUCTS or key not in NUTRI:
            logger.warning("ИИ предложил несуществующий продукт '%s'", key)
            return None
        # bool — подкласс int, но "ингредиент: true" не количество
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            return None
        amount = float(amount)
        if not math.isfinite(amount) or amount <= 0:
            return None

        if key in PER_PIECE_KEYS:  # яйца/авокадо считаются штуками, а не граммами
            if amount > MAX_PIECES_PER_INGREDIENT:
                return None
            ingredients[key] = round(amount, 2)
        else:
            if amount > MAX_GRAMS_PER_INGREDIENT:
                return None
            grams = int(round(amount))
            if grams <= 0:  # 0.3 г округлились в ноль — такой ингредиент не нужен
                return None
            total_grams += grams
            ingredients[key] = grams

    if total_grams > MAX_TOTAL_GRAMS:
        logger.warning("ИИ предложил порцию в %s г — отбрасываем", round(total_grams))
        return None
    return ingredients


def _validate_ai_steps(raw) -> list | None:
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_STEPS:
        return None
    steps = []
    for step in raw:
        if not isinstance(step, str) or not step.strip():
            return None
        steps.append(step.strip()[:MAX_STEP_CHARS])
    return steps


def _build_meal_from_ai(data, meal_type: str, allowed: set, cooking_level: str | None) -> dict | None:
    """Проверяет ответ ИИ и достраивает его до записи вида meals_data.MEALS[...][i].
    КБЖУ, теги и цели считаются здесь, а не берутся у модели."""
    if not isinstance(data, dict):
        return None

    name = str(data.get("name") or "").strip()[:120]
    if not name:
        return None

    difficulty = data.get("difficulty")
    if difficulty not in ALLOWED_DIFFICULTY:
        return None

    minutes = data.get("time")
    if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not math.isfinite(float(minutes)):
        return None
    minutes = int(round(float(minutes)))
    if not 1 <= minutes <= MAX_TIME_MINUTES:
        return None

    if cooking_level == "simple" and (difficulty != "easy" or minutes > SIMPLE_LEVEL_MAX_TIME):
        logger.warning("Блюдо не подходит новичку (%s, %s мин) — отбрасываем", difficulty, minutes)
        return None

    ingredients = _validate_ai_ingredients(data.get("ingredients"), allowed)
    if ingredients is None:
        return None

    raw_steps = data.get("steps")
    if raw_steps is None and isinstance(data.get("recipe"), dict):
        raw_steps = data["recipe"].get("steps")  # модель иногда вкладывает шаги в recipe
    steps = _validate_ai_steps(raw_steps)
    if steps is None:
        return None

    macros = compute_macros(ingredients)
    low, high = _kcal_bounds(meal_type)
    if not low <= macros["kcal"] <= high:
        logger.warning("КБЖУ блюда от ИИ вне диапазона для '%s': %s ккал (ждём %s-%s)",
                       meal_type, macros["kcal"], low, high)
        return None

    cuisine = str(data.get("cuisine") or "").strip().lower()
    if not re.fullmatch(r"[a-z_]{3,24}", cuisine):
        cuisine = "international"

    return {
        "name": name,
        "goals": compute_goals(macros["kcal"], meal_type),
        "tags": compute_tags(ingredients),
        "cuisine": cuisine,
        "difficulty": difficulty,
        "time": minutes,
        "ingredients": ingredients,
        **macros,
        "recipe": {"time": minutes, "steps": steps},
    }


def generate_meal(meal_type: str, allowed_product_keys: list[str],
                  cooking_level: str | None = None,
                  goal: str | None = None) -> dict | None:
    """Придумывает НОВОЕ блюдо из разрешённых пользователю продуктов.

    Нужно, когда после фильтрации по навыку готовки и списку продуктов в
    статической базе почти ничего не осталось. Возвращает запись ровно того же
    вида, что элементы meals_data.MEALS[meal_type] (её можно класть прямо в
    план), либо None — если ИИ недоступен или ответ не прошёл проверку.
    Исключений не бросает никогда."""
    if meal_type not in MEAL_TYPE_NAMES_RU:
        return None

    keys = _known_allowed_keys(allowed_product_keys)
    if len(keys) < MIN_ALLOWED_KEYS:
        logger.warning("Слишком мало разрешённых продуктов (%s) — блюдо не генерируем", len(keys))
        return None

    messages = [
        {"role": "system", "content": MEAL_GENERATE_SYSTEM},
        {"role": "user", "content": _meal_request_text(meal_type, keys, cooking_level, goal)},
    ]
    text = chat(messages, temperature=0.7, max_tokens=600)
    if text is None:
        return None

    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.warning("Не удалось найти JSON в ответе ИИ (блюдо): %s", text[:200])
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("Невалидный JSON от ИИ (блюдо): %s", text[:200])
            return None
        meal = _build_meal_from_ai(data, meal_type, set(keys), cooking_level)
    except Exception:  # noqa: BLE001 — бот не должен падать из-за ответа ИИ
        logger.exception("Сбой разбора блюда от ИИ")
        return None

    if meal is None:
        logger.warning("Блюдо от ИИ не прошло проверку и отброшено: %s", text[:300])
    return meal
