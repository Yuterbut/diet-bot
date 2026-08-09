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
import os
import re

import requests

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
