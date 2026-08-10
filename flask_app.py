"""
Telegram-бот "Диет-планировщик" — webhook-версия для PythonAnywhere.

Что умеет:
  * составляет план питания на неделю под цель и ограничения;
  * учитывает регион (цены отличаются) и бюджет;
  * собирает список покупок с отметками "куплено";
  * позволяет обновлять цены прямо из чата командой /цена.

Настройка описана в README_pythonanywhere.md
"""

import os
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

import ai_agent
import charts
import food_lookup
import nutrition
import photos
import planner
import storage
from meals_data import BUDGET_PRESETS, GOAL_LABELS, MEAL_TYPE_LABELS, RESTRICTION_LABELS
from products import PRODUCTS, REGIONS

load_dotenv(Path(__file__).parent / ".env")

# Sentry — мониторинг ошибок, полностью опционален: без SENTRY_DSN просто не включается.
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[FlaskIntegration()],
                         traces_sample_rate=0.0, send_default_pii=False)
    except ImportError:
        pass

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN (проверь файл .env рядом с flask_app.py)")

API_URL = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

RESTRICTION_KEYS = list(RESTRICTION_LABELS.keys())
WELCOME = "Привет! 👋 Составлю план питания на неделю с учётом бюджета.\n\nКакая у тебя цель?"

# ---------- ИИ-диетолог: константы ----------

TZ = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Moscow"))
CRON_SECRET = os.getenv("CRON_SECRET", "")

SEX_LABELS = {"m": "Мужской", "f": "Женский"}
MEAL_SLOT_LABELS = {"breakfast": "🌅 Завтрак", "lunch": "🥗 Обед", "dinner": "🍽 Ужин", "snack": "🍎 Перекус"}
DEFAULT_REMINDERS = {"breakfast": "08:30", "lunch": "13:30", "dinner": "19:30"}

# Опрос "поел ли ты?": спрашиваем один раз, если нет ответа — ровно один повтор
# через час, и всё (Telegram не даёт боту статус "прочитано", поэтому ждём по
# времени с момента отправки, а не с момента прочтения).
FOLLOWUP_WINDOW_MINUTES = 60
EVENING_CHECK_SLOT = "evening_check"
EVENING_CHECK_TIME = "20:30"

WEEK_DAYS = 7  # через сколько дней предлагать обновить меню
PROFILE_SEQUENCE = ["sex", "age", "height", "weight", "activity"]


def tg(method: str, **payload):
    try:
        return requests.post(f"{API_URL}/{method}", json=payload, timeout=15).json()
    except requests.RequestException as e:
        app.logger.error("Ошибка запроса к Telegram: %s", e)
        return {}


def tg_photo(chat_id: int, photo_bytes: bytes, caption: str = "") -> int | None:
    """Отправляет сгенерированную картинку. Возвращает message_id (для последующего
    удаления при переходе на другой экран) или None при сбое."""
    try:
        resp = requests.post(f"{API_URL}/sendPhoto", data={"chat_id": chat_id, "caption": caption},
                              files={"photo": ("chart.png", photo_bytes, "image/png")}, timeout=20)
        return resp.json().get("result", {}).get("message_id")
    except requests.RequestException as e:
        app.logger.error("Ошибка отправки фото в Telegram: %s", e)
        return None


def tg_delete(chat_id: int, message_id: int | None) -> None:
    if message_id:
        tg("deleteMessage", chat_id=chat_id, message_id=message_id)


def notify_admin_error(context: str) -> None:
    """Шлёт админу в Telegram уведомление о необработанной ошибке (вместо Sentry,
    который у нас блокируется сетью). Вызывать только изнутри except-блока."""
    admin_id = os.getenv("ADMIN_CHAT_ID")
    if not admin_id:
        return
    tb = traceback.format_exc()
    text = f"⚠️ Ошибка в боте ({context})\n\n{tb[-1500:]}"
    try:
        tg("sendMessage", chat_id=int(admin_id), text=text[:4000])
    except Exception:
        pass  # уведомление об ошибке не должно само порождать ошибку


# ---------- Клавиатуры ----------

def goal_keyboard():
    return {"inline_keyboard": [
        [{"text": "📉 Похудение", "callback_data": "G|loss"}],
        [{"text": "📈 Набор массы", "callback_data": "G|gain"}],
        [{"text": "⚖️ Поддержание веса", "callback_data": "G|maintain"}],
        [{"text": "🎲 Просто разнообразие", "callback_data": "G|variety"}],
        [{"text": "🤖 ИИ-диетолог (тест)", "callback_data": "AI|START"}],
    ]}


def restrictions_keyboard(selected: list):
    rows = []
    for i, key in enumerate(RESTRICTION_KEYS):
        box = "☑️" if key in selected else "⬜️"
        rows.append([{"text": f"{box} {RESTRICTION_LABELS[key]}", "callback_data": f"R|{i}"}])
    rows.append([{"text": "✅ Готово, дальше", "callback_data": "D"}])
    return {"inline_keyboard": rows}


def meals_keyboard():
    return {"inline_keyboard": [
        [{"text": "3 приёма пищи", "callback_data": "M|3"}],
        [{"text": "5 приёмов (с перекусами)", "callback_data": "M|5"}],
    ]}


def region_keyboard():
    rows = [[{"text": data["name"], "callback_data": f"REG|{key}"}]
            for key, data in REGIONS.items()]
    return {"inline_keyboard": rows}


def budget_keyboard():
    rows = [[{"text": f"{p['name']} · {p['hint']}", "callback_data": f"B|{key}"}]
            for key, p in BUDGET_PRESETS.items()]
    return {"inline_keyboard": rows}


def plan_keyboard(day: int = 0, total_days: int = 7):
    prev_day = (day - 1) % total_days
    next_day = (day + 1) % total_days
    return {"inline_keyboard": [
        [
            {"text": "◀️", "callback_data": f"DAY|{prev_day}"},
            {"text": f"День {day + 1}/{total_days}", "callback_data": "NOOP"},
            {"text": "▶️", "callback_data": f"DAY|{next_day}"},
        ],
        [{"text": "🔁 Заменить блюдо", "callback_data": f"SWAP|{day}"}],
        [{"text": "👨‍🍳 Рецепты", "callback_data": f"RECIPES|{day}"}],
        [{"text": "🛒 Список покупок", "callback_data": f"SHOP|{day}"}],
        [{"text": "🔄 Другой вариант", "callback_data": "REGEN"},
         {"text": "⚙️ Заново", "callback_data": "START"}],
        [{"text": "🤖 ИИ-диетолог", "callback_data": "AI|START"}],
    ]}


def swap_slots_keyboard(user: dict, day: int):
    """Выбор блюда для замены внутри дня."""
    order = planner.MEAL_ORDER_5 if user["meals_per_day"] == 5 else planner.MEAL_ORDER_3
    rows = []
    for slot, (meal_type, name) in enumerate(zip(order, user["plan_names"][day])):
        label = MEAL_TYPE_LABELS[meal_type].split()[0]
        rows.append([{"text": f"{label} {name}", "callback_data": f"SWS|{day}|{slot}"}])
    rows.append([{"text": "⬅️ Назад к меню", "callback_data": f"DAY|{day}"}])
    return {"inline_keyboard": rows}


def swap_options_keyboard(day: int, slot: int, options: list):
    rows = [[{"text": name, "callback_data": f"SWD|{day}|{slot}|{i}"}]
            for i, name in enumerate(options)]
    rows.append([{"text": "⬅️ Отмена", "callback_data": f"DAY|{day}"}])
    return {"inline_keyboard": rows}


def recipes_keyboard(names: list, day: int):
    rows = [[{"text": f"👨‍🍳 {name}", "callback_data": f"RC|{day}|{i}"}]
            for i, name in enumerate(names)]
    rows.append([{"text": "⬅️ Назад к меню", "callback_data": f"DAY|{day}"}])
    return {"inline_keyboard": rows}


def recipe_back_keyboard(day: int):
    return {"inline_keyboard": [
        [{"text": "⬅️ К списку рецептов", "callback_data": f"RECIPES|{day}"}],
        [{"text": "📋 К меню", "callback_data": f"DAY|{day}"}],
    ]}


CATEGORY_EMOJI = {
    "крупы": "🌾", "макароны": "🍝", "хлеб": "🍞", "мука": "🌾",
    "птица": "🍗", "мясо": "🥩", "яйца": "🥚", "рыба": "🐟", "морепродукты": "🦐",
    "молочное": "🥛", "раст_молоко": "🥥", "овощи": "🥦", "зелень": "🌿",
    "консервы": "🥫", "грибы": "🍄", "фрукты": "🍎", "ягоды": "🫐",
    "бобовые": "🫘", "раст_белок": "🌱", "орехи": "🥜", "семена": "🌻",
    "сухофрукты": "🍇", "масла": "🫒", "соусы": "🧂", "специи": "🧂",
    "сладости": "🍬", "спортпит": "💪", "напитки": "☕", "прочее": "📦",
}


def _item_category(item: dict) -> str:
    return PRODUCTS.get(item["key"], {}).get("category", "прочее")


def _items_by_category(items: list) -> dict:
    """key -> список исходных индексов (индекс важен: 'bought' и 'T|' ссылаются на него)."""
    cats: dict[str, list[int]] = {}
    for i, item in enumerate(items):
        cats.setdefault(_item_category(item), []).append(i)
    return cats


def shopping_categories_keyboard(items: list, bought: list, day: int) -> dict:
    """Список покупок разгружен по категориям — раньше все продукты шли одним
    длинным списком кнопок, теперь сначала категории, потом состав внутри."""
    cats = _items_by_category(items)
    rows = []
    for cat, idxs in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        done = sum(1 for i in idxs if i in bought)
        emoji = CATEGORY_EMOJI.get(cat, "📦")
        mark = " ✅" if done == len(idxs) else ""
        rows.append([{"text": f"{emoji} {cat.capitalize()} ({done}/{len(idxs)}){mark}",
                      "callback_data": f"SHOPCAT|{day}|{cat}"}])
    rows.append([{"text": "📋 Вернуться к меню", "callback_data": f"DAY|{day}"}])
    return {"inline_keyboard": rows}


def shopping_category_keyboard(items: list, bought: list, day: int, category: str) -> dict:
    rows = []
    for i, item in enumerate(items):
        if _item_category(item) != category:
            continue
        box = "✅" if i in bought else "⬜️"
        rows.append([{
            "text": f"{box} {item['name']} · {item['amount_text']} · {item['cost']} ₽",
            "callback_data": f"T|{day}|{category}|{i}",
        }])
    rows.append([{"text": "⬅️ К категориям", "callback_data": f"SHOP|{day}"}])
    return {"inline_keyboard": rows}


def sex_keyboard():
    return {"inline_keyboard": [
        [{"text": "👨 Мужской", "callback_data": "AIS|m"}, {"text": "👩 Женский", "callback_data": "AIS|f"}],
    ]}


def activity_keyboard():
    rows = [[{"text": label, "callback_data": f"AIA|{key}"}]
            for key, (label, _) in nutrition.ACTIVITY_LEVELS.items()]
    return {"inline_keyboard": rows}


def measurements_prompt_keyboard():
    return {"inline_keyboard": [
        [{"text": "✏️ Указать объёмы", "callback_data": "AIM|YES"}],
        [{"text": "⏭ Пропустить", "callback_data": "AIM|NO"}],
    ]}


def ai_menu_keyboard(user: dict | None = None):
    rows = [
        [{"text": "📝 Записать приём пищи", "callback_data": "AI|LOG"}],
        [{"text": "📊 Сегодня", "callback_data": "AI|TODAY"}, {"text": "📈 Неделя", "callback_data": "AI|WEEK"}],
        [{"text": "⏰ Напоминания", "callback_data": "AI|REMIND"}],
        [{"text": "💬 Спросить диетолога", "callback_data": "AI|ASK"}],
        [{"text": "👤 Анкета", "callback_data": "AI|PROFILE"}],
    ]
    if user and user.get("plan_names"):
        rows.append([{"text": "📋 План питания", "callback_data": "PLAN"}])
    rows.append([{"text": "🏠 Главное меню", "callback_data": "HOME"}])
    return {"inline_keyboard": rows}


def reminder_response_keyboard(slot: str):
    return {"inline_keyboard": [
        [{"text": "✅ Поел по плану", "callback_data": f"AIR|OK|{slot}"}],
        [{"text": "🍽 Ел другое", "callback_data": f"AIR|OTHER|{slot}"}],
        [{"text": "➖ Пропустил", "callback_data": f"AIR|SKIP|{slot}"}],
    ]}


def evening_check_keyboard():
    return {"inline_keyboard": [
        [{"text": "✅ Всё записано", "callback_data": "EVE|OK"}],
        [{"text": "🍽 Было что-то ещё", "callback_data": "EVE|OTHER"}],
    ]}


def weekly_renewal_keyboard():
    return {"inline_keyboard": [
        [{"text": "😊 Нравится, оставляем", "callback_data": "WK|KEEP"}],
        [{"text": "🔄 Новое меню целиком", "callback_data": "WK|REGEN"}],
        [{"text": "🍽 Заменить блюдо", "callback_data": "WK|SWAP"}],
    ]}


def food_confirm_keyboard():
    return {"inline_keyboard": [
        [{"text": "✅ Добавить в дневник", "callback_data": "AIL|ADD"}],
        [{"text": "🔄 Написать заново", "callback_data": "AIL|RETRY"}],
        [{"text": "❌ Отмена", "callback_data": "AIL|CANCEL"}],
    ]}


def back_to_ai_menu_keyboard():
    return {"inline_keyboard": [
        [{"text": "⬅️ В меню диетолога", "callback_data": "AI|MENU"}],
        [{"text": "🏠 Главное меню", "callback_data": "HOME"}],
    ]}


# ---------- Формирование сообщений ----------

def plan_text(user: dict, day: int = 0) -> str:
    header = [f"🎯 *{GOAL_LABELS[user['goal']]}* · 📍 {REGIONS[user['region']]['name']}"]
    if user.get("restrictions"):
        header.append("🚫 " + ", ".join(RESTRICTION_LABELS[r] for r in user["restrictions"]))
    header.append(f"💵 Чек в магазине: *≈ {user['total']} ₽*")
    if user.get("consumed") and user["consumed"] < user["total"] * 0.9:
        header.append(f"_Съедите примерно на {user['consumed']} ₽ — остальное "
                      "(крупы, масло, мёд) останется на следующие недели._")
    if user.get("over_budget"):
        header.append("\n⚠️ В заданный бюджет уложиться не удалось — это самый "
                      "дешёвый возможный вариант.")
    header.append("")
    header.append(planner.format_day(user["plan_names"], day, user["meals_per_day"]))
    header.append("")
    header.append("_👨‍🍳 — есть подробный рецепт_")
    return "\n".join(header)


def shopping_text(user: dict) -> str:
    bought = set(user.get("bought", []))
    remaining = sum(item["cost"] for i, item in enumerate(user["items"]) if i not in bought)
    done = len(bought)
    total_items = len(user["items"])

    lines = ["🛒 *Список покупок на неделю*", ""]
    lines.append(f"Отмечено: {done} из {total_items}")
    lines.append(f"Осталось купить примерно на *{round(remaining)} ₽*")
    lines.append("")
    lines.append("_Выбери категорию, чтобы отметить покупки._")
    return "\n".join(lines)


def shopping_category_text(user: dict, category: str) -> str:
    items = user.get("items", [])
    bought = set(user.get("bought", []))
    cat_indices = [i for i, item in enumerate(items) if _item_category(item) == category]
    remaining = sum(items[i]["cost"] for i in cat_indices if i not in bought)
    done = sum(1 for i in cat_indices if i in bought)
    emoji = CATEGORY_EMOJI.get(category, "📦")

    lines = [f"{emoji} *{category.capitalize()}*", ""]
    lines.append(f"Отмечено: {done} из {len(cat_indices)}")
    lines.append(f"Осталось купить примерно на *{round(remaining)} ₽*")
    lines.append("")
    lines.append("_Нажимай на продукт, чтобы отметить покупку._")
    return "\n".join(lines)


def build_and_save(chat_id: int, user: dict) -> dict:
    result = planner.generate_plan(
        goal=user["goal"],
        restrictions=set(user.get("restrictions", [])),
        meals_per_day=user["meals_per_day"],
        budget=user.get("budget"),
        region=user.get("region", "center"),
    )
    # сохраняем только названия блюд — их достаточно для показа плана
    plan_names = [[m["name"] for m in day] for day in result["plan"]]
    return storage.save_user(chat_id, {
        "plan_names": plan_names,
        "items": result["items"],
        "total": result["total"],
        "consumed": result.get("consumed"),
        "over_budget": result.get("over_budget", False),
        "bought": [],
        "awaiting_budget": False,
        "plan_created": datetime.now(TZ).date().isoformat(),
        "plan_renewal_notified": False,
    })


# ---------- ИИ-диетолог: анкета, дневник, напоминания ----------

def ai_missing_field(profile: dict) -> str | None:
    """Следующий незаполненный шаг анкеты, либо None если анкета готова."""
    for field in PROFILE_SEQUENCE:
        if profile.get(field) is None:
            return field
    if not profile.get("measurements_asked"):
        return "measurements_choice"
    return None


def ai_profile_context(user: dict) -> str:
    """Короткое текстовое summary для промпта ИИ (профиль + КБЖУ за сегодня)."""
    p = user.get("profile", {})
    parts = []
    if p.get("sex"):
        parts.append(f"пол: {SEX_LABELS.get(p['sex'], p['sex'])}")
    if p.get("age"):
        parts.append(f"возраст: {p['age']}")
    if p.get("height"):
        parts.append(f"рост: {p['height']} см")
    if p.get("weight"):
        parts.append(f"вес: {p['weight']} кг")
    goal = user.get("goal")
    if goal:
        parts.append(f"цель: {GOAL_LABELS.get(goal, goal)}")
    if nutrition.profile_complete(p):
        target = nutrition.full_profile_targets(p, goal or "maintain")
        parts.append(f"дневная норма: {target['kcal']} ккал")
        today = datetime.now(TZ).date().isoformat()
        totals, _ = diary_day_totals(user.get("diary", []), today)
        parts.append(f"уже съедено сегодня: {totals['kcal']} ккал")
    return "; ".join(parts)


def ai_profile_text(user: dict) -> str:
    p = user.get("profile", {})
    lines = ["👤 *Анкета*", ""]
    lines.append(f"Пол: {SEX_LABELS.get(p.get('sex'), '—')}")
    lines.append(f"Возраст: {p.get('age', '—')}")
    lines.append(f"Рост: {p.get('height', '—')} см")
    lines.append(f"Вес: {p.get('weight', '—')} кг")
    activity = nutrition.ACTIVITY_LEVELS.get(p.get("activity"))
    lines.append(f"Активность: {activity[0] if activity else '—'}")
    if p.get("waist"):
        lines.append(f"Талия: {p['waist']} см")
    if p.get("hips"):
        lines.append(f"Бёдра: {p['hips']} см")
    if p.get("chest"):
        lines.append(f"Грудь: {p['chest']} см")
    if nutrition.profile_complete(p):
        goal = user.get("goal", "maintain")
        target = nutrition.full_profile_targets(p, goal)
        lines.append("")
        lines.append(f"🎯 Дневная норма (*{GOAL_LABELS.get(goal, 'поддержание')}*): *{target['kcal']} ккал*")
        lines.append(f"Б {target['protein']} г · Ж {target['fat']} г · У {target['carbs']} г")
    return "\n".join(lines)


def ai_advance(chat_id: int, message_id: int | None = None) -> None:
    """Отправляет следующий шаг анкеты либо, если анкета готова, — меню ИИ-диетолога."""
    user = storage.get_user(chat_id)
    profile = user.get("profile", {})
    missing = ai_missing_field(profile)

    def send(text: str, keyboard: dict) -> None:
        if message_id:
            tg("editMessageText", chat_id=chat_id, message_id=message_id,
               text=text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            tg("sendMessage", chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=keyboard)

    if missing == "sex":
        send("Для расчёта дневной нормы калорий пройдём короткую анкету 📋\n\nТвой пол?", sex_keyboard())
    elif missing == "age":
        storage.save_user(chat_id, {"ai_state": "age"})
        tg("sendMessage", chat_id=chat_id, text="Сколько тебе лет?")
    elif missing == "height":
        storage.save_user(chat_id, {"ai_state": "height"})
        tg("sendMessage", chat_id=chat_id, text="Рост в сантиметрах?")
    elif missing == "weight":
        storage.save_user(chat_id, {"ai_state": "weight"})
        tg("sendMessage", chat_id=chat_id, text="Текущий вес в кг?")
    elif missing == "activity":
        send("Какой уровень активности у тебя в среднем за неделю?", activity_keyboard())
    elif missing == "measurements_choice":
        send("Хочешь также указать объёмы (талия/бёдра/грудь)?\nНе обязательно — можно добавить позже.",
             measurements_prompt_keyboard())
    else:
        if not user.get("goal"):
            storage.save_user(chat_id, {"goal": "maintain"})
            user = storage.get_user(chat_id)
        text = "✅ Анкета готова!\n\n" + ai_profile_text(user)
        send(text, ai_menu_keyboard(user))


def diary_day_totals(diary: list, date_str: str) -> tuple[dict, list]:
    entries = [e for e in diary if e.get("date") == date_str]
    totals = {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0}
    for e in entries:
        for k in totals:
            totals[k] += e.get(k, 0) or 0
    return totals, entries


def ai_today_text(user: dict) -> str:
    diary = user.get("diary", [])
    today = datetime.now(TZ).date().isoformat()
    totals, entries = diary_day_totals(diary, today)
    lines = ["📊 *Сегодня*", ""]
    if not entries:
        lines.append("Пока ничего не записано.")
    else:
        marks = {"missed": "➖", "planned": "✅", "logged": "🍽"}
        for e in entries:
            mark = marks.get(e.get("source"), "•")
            lines.append(f"{mark} {e.get('time', '')} — {e.get('name', '?')} ({e.get('kcal', 0)} ккал)")
    lines.append("")
    lines.append(f"Итого: *{totals['kcal']} ккал* · Б {totals['protein']} Ж {totals['fat']} У {totals['carbs']}")

    profile = user.get("profile", {})
    if nutrition.profile_complete(profile):
        target = nutrition.full_profile_targets(profile, user.get("goal", "maintain"))
        remaining = target["kcal"] - totals["kcal"]
        status = f"осталось {remaining}" if remaining >= 0 else f"превышение на {-remaining}"
        lines.append(f"Норма: {target['kcal']} ккал ({status})")
    return "\n".join(lines)


def week_kcal_series(user: dict) -> list[tuple[str, int]]:
    """(дата, ккал) за последние 7 дней по порядку — включая дни без записей (0 ккал), для графика."""
    diary = user.get("diary", [])
    today = datetime.now(TZ).date()
    days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    return [(d, diary_day_totals(diary, d)[0]["kcal"]) for d in days]


def ai_week_text(user: dict) -> str:
    diary = user.get("diary", [])
    today = datetime.now(TZ).date()
    days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    profile = user.get("profile", {})
    target_kcal = None
    if nutrition.profile_complete(profile):
        target_kcal = nutrition.full_profile_targets(profile, user.get("goal", "maintain"))["kcal"]

    day_lines, summary_rows = [], []
    for d in days:
        totals, entries = diary_day_totals(diary, d)
        if not entries:
            continue
        weekday = datetime.fromisoformat(d).strftime("%a")
        mark = ""
        if target_kcal:
            mark = " ✅" if totals["kcal"] <= target_kcal * 1.1 else " ⚠️"
        day_lines.append(f"{d} ({weekday}): {totals['kcal']} ккал{mark}")
        summary_rows.append(f"{d}: {totals['kcal']} ккал, Б{totals['protein']}/Ж{totals['fat']}/У{totals['carbs']}")

    if not day_lines:
        return "📈 *Неделя*\n\nЗа последние 7 дней в дневнике пока пусто."

    header = "📈 *Отчёт за неделю*\n\n" + "\n".join(day_lines)
    prompt_data = (f"Цель: {user.get('goal', 'maintain')}. "
                   f"Дневная норма: {target_kcal or 'неизвестна'} ккал.\n" + "\n".join(summary_rows))
    ai_text = ai_agent.weekly_report(prompt_data)
    if ai_text:
        header += "\n\n" + ai_text
    return header


def send_week_chart(chat_id: int, user: dict) -> None:
    series = week_kcal_series(user)
    if not any(kcal > 0 for _, kcal in series):
        return
    target_kcal = None
    profile = user.get("profile", {})
    if nutrition.profile_complete(profile):
        target_kcal = nutrition.full_profile_targets(profile, user.get("goal", "maintain"))["kcal"]
    try:
        png_bytes = charts.week_kcal_chart(series, target_kcal)
        new_id = tg_photo(chat_id, png_bytes)
        storage.save_user(chat_id, {"last_chart_photo_id": new_id})
    except Exception as e:
        app.logger.error("Ошибка построения графика недели: %s", e)


def ai_remind_text(user: dict) -> str:
    reminders = user.get("reminders") or DEFAULT_REMINDERS
    enabled = user.get("reminders_enabled", False)
    lines = ["⏰ *Напоминания о приёмах пищи*", ""]
    lines.append(f"Статус: {'включены ✅' if enabled else 'выключены'}")
    lines.append(f"Завтрак: {reminders.get('breakfast', '—')}")
    lines.append(f"Обед: {reminders.get('lunch', '—')}")
    lines.append(f"Ужин: {reminders.get('dinner', '—')}")
    lines.append(f"Вечерняя проверка неучтённого: {EVENING_CHECK_TIME}")
    lines.append("")
    lines.append("Напиши три времени через пробел (завтрак обед ужин), например:\n`08:00 13:30 19:30`")
    lines.append("Чтобы выключить — напиши «выкл».")
    lines.append("")
    lines.append("_На каждый опрос жду ответа — кнопкой или просто текстом ('да', 'нет' или что съел). "
                  "Если через час нет ответа — напомню ещё один раз, и всё._")
    return "\n".join(lines)


def tg_download_file(file_id: str) -> bytes | None:
    try:
        info = tg("getFile", file_id=file_id)
        file_path = (info or {}).get("result", {}).get("file_path")
        if not file_path:
            return None
        resp = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_path}", timeout=20)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException as e:
        app.logger.error("Ошибка скачивания файла из Telegram: %s", e)
        return None


def handle_food_photo(chat_id: int, photo_sizes: list) -> None:
    tg("sendChatAction", chat_id=chat_id, action="typing")
    largest = max(photo_sizes, key=lambda p: p.get("file_size") or p.get("width", 0))
    image_bytes = tg_download_file(largest["file_id"])
    if not image_bytes:
        tg("sendMessage", chat_id=chat_id, text="Не получилось скачать фото, попробуй ещё раз 🙏")
        return

    estimate = ai_agent.estimate_food_from_image(image_bytes)
    if not estimate or estimate.get("kcal", 0) == 0:
        note = (estimate or {}).get("note") or ("не получилось распознать еду на фото — попробуй "
                                                  "при хорошем освещении, или опиши текстом")
        tg("sendMessage", chat_id=chat_id, text=f"🤔 {note}", reply_markup=back_to_ai_menu_keyboard())
        return

    storage.save_user(chat_id, {"pending_food": estimate, "ai_state": None})
    lines = [f"🍽 *{estimate['name']}*"]
    if estimate.get("portion"):
        lines.append(f"Порция: {estimate['portion']}")
    lines.append(f"*{estimate['kcal']} ккал* · Б {estimate['protein']} Ж {estimate['fat']} У {estimate['carbs']}")
    if estimate.get("note"):
        lines.append(f"_{estimate['note']}_")
    tg("sendMessage", chat_id=chat_id, text="\n".join(lines), parse_mode="Markdown",
       reply_markup=food_confirm_keyboard())


def handle_food_log(chat_id: int, text: str, slot: str | None = None) -> None:
    tg("sendChatAction", chat_id=chat_id, action="typing")
    if slot is None:
        slot = storage.get_user(chat_id).get("pending_food_slot")
    estimate = food_lookup.estimate(text)
    if not estimate:
        tg("sendMessage", chat_id=chat_id,
           text="Не получилось оценить калорийность — ИИ сейчас недоступен. Попробуй ещё раз чуть позже 🙏",
           reply_markup=back_to_ai_menu_keyboard())
        return
    storage.save_user(chat_id, {"pending_food": estimate, "pending_food_slot": slot, "ai_state": None})
    lines = [f"🍽 *{estimate['name']}*"]
    if estimate.get("portion"):
        lines.append(f"Порция: {estimate['portion']}")
    lines.append(f"*{estimate['kcal']} ккал* · Б {estimate['protein']} Ж {estimate['fat']} У {estimate['carbs']}")
    if estimate.get("note"):
        lines.append(f"_{estimate['note']}_")
    tg("sendMessage", chat_id=chat_id, text="\n".join(lines), parse_mode="Markdown",
       reply_markup=food_confirm_keyboard())


def handle_ai_question(chat_id: int, user: dict, text: str) -> None:
    tg("sendChatAction", chat_id=chat_id, action="typing")
    context = ai_profile_context(user)
    reply = ai_agent.dietitian_chat(context, text)
    storage.save_user(chat_id, {"ai_state": None})
    if not reply:
        tg("sendMessage", chat_id=chat_id, text="ИИ сейчас недоступен, попробуй чуть позже 🙏",
           reply_markup=ai_menu_keyboard(user))
        return
    tg("sendMessage", chat_id=chat_id, text=reply, reply_markup=ai_menu_keyboard(user))


def handle_reminder_times(chat_id: int, text: str) -> None:
    low = text.strip().lower()
    if low in ("выкл", "выключить", "off"):
        storage.save_user(chat_id, {"reminders_enabled": False, "ai_state": None})
        tg("sendMessage", chat_id=chat_id, text="Напоминания выключены.", reply_markup=ai_menu_keyboard())
        return

    times = text.split()
    if len(times) != 3 or not all(re.fullmatch(r"[0-2]\d:[0-5]\d", t) for t in times):
        tg("sendMessage", chat_id=chat_id,
           text="Не понял формат. Напиши три времени через пробел, например: 08:00 13:30 19:30\n"
                "Или «выкл», чтобы отключить напоминания.")
        return

    reminders = {"breakfast": times[0], "lunch": times[1], "dinner": times[2]}
    storage.save_user(chat_id, {"reminders": reminders, "reminders_enabled": True, "ai_state": None})
    tg("sendMessage", chat_id=chat_id, text="✅ Напоминания настроены.", reply_markup=ai_menu_keyboard())


def handle_ai_text(chat_id: int, state: str, text: str) -> None:
    text = text.strip()

    if state == "age":
        if not text.isdigit() or not (10 <= int(text) <= 100):
            tg("sendMessage", chat_id=chat_id, text="Введи возраст числом от 10 до 100.")
            return
        storage.update_profile(chat_id, {"age": int(text)})
        ai_advance(chat_id)
        return

    if state in ("height", "weight"):
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            value = None
        bounds = {"height": (100, 250), "weight": (30, 300)}[state]
        if value is None or not (bounds[0] <= value <= bounds[1]):
            hint = "рост в сантиметрах, например 175" if state == "height" else "вес в кг, например 68"
            tg("sendMessage", chat_id=chat_id, text=f"Введи {hint}.")
            return
        storage.update_profile(chat_id, {state: value})
        ai_advance(chat_id)
        return

    if state in ("waist", "hips", "chest"):
        if text in ("-", "—", "нет", "пропустить"):
            value = None
        else:
            try:
                value = float(text.replace(",", "."))
                if not (30 <= value <= 250):
                    raise ValueError
            except ValueError:
                tg("sendMessage", chat_id=chat_id, text="Напиши число в см или «-», чтобы пропустить.")
                return
        if value is not None:
            storage.update_profile(chat_id, {state: value})
        next_map = {"waist": "hips", "hips": "chest", "chest": None}
        nxt = next_map[state]
        if nxt:
            storage.save_user(chat_id, {"ai_state": nxt})
            labels = {"hips": "бёдер", "chest": "груди"}
            tg("sendMessage", chat_id=chat_id, text=f"Объём {labels[nxt]} в см? (или «-», чтобы пропустить)")
        else:
            storage.update_profile(chat_id, {"measurements_asked": True})
            ai_advance(chat_id)
        return

    if state == "food_log":
        handle_food_log(chat_id, text)
        return

    if state == "ask":
        handle_ai_question(chat_id, storage.get_user(chat_id), text)
        return

    if state == "reminder_times":
        handle_reminder_times(chat_id, text)
        return


def apply_checkin_response(chat_id: int, slot: str, sub_action: str, message_id: int | None = None) -> None:
    """Общая логика ответа на опрос "поел ли ты?" — вызывается и из кнопок (AIR),
    и из свободного текста (см. handle_checkin_text_reply). message_id задан
    только для кнопок (тогда редактируем то же сообщение вместо нового)."""
    user = storage.get_user(chat_id)
    today = datetime.now(TZ).date().isoformat()
    now_t = datetime.now(TZ).strftime("%H:%M")
    label = MEAL_SLOT_LABELS.get(slot, slot)
    storage.update_checkin(chat_id, today, slot, {"responded": True})

    def reply(text: str, keyboard: dict | None = None) -> None:
        if message_id:
            tg("editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=keyboard)
        else:
            tg("sendMessage", chat_id=chat_id, text=text, reply_markup=keyboard)

    if sub_action == "SKIP":
        storage.add_diary_entry(chat_id, {
            "date": today, "time": now_t, "source": "missed", "slot": slot,
            "name": f"Пропущен приём пищи ({label})", "kcal": 0, "protein": 0, "fat": 0, "carbs": 0,
        })
        reply(f"Записал: {label} пропущен. Бывает — наверстаем в следующий раз 🙂", ai_menu_keyboard(user))

    elif sub_action == "OK":
        plan_meal = None
        plan_names = user.get("plan_names")
        if plan_names:
            order = planner.MEAL_ORDER_5 if user.get("meals_per_day") == 5 else planner.MEAL_ORDER_3
            weekday = datetime.now(TZ).weekday()
            if slot in order and weekday < len(plan_names):
                plan_meal = plan_names[weekday][order.index(slot)]
        reply("Отлично! Оцениваю калорийность блюда… 🍽")
        estimate = food_lookup.estimate(plan_meal) if plan_meal else None
        entry = estimate or {"name": plan_meal or label, "portion": "", "kcal": 0, "protein": 0, "fat": 0, "carbs": 0, "note": ""}
        storage.add_diary_entry(chat_id, {"date": today, "time": now_t, "source": "planned", "slot": slot, **entry})
        tg("sendMessage", chat_id=chat_id,
           text=f"✅ Записал: *{entry['name']}* — {entry['kcal']} ккал", parse_mode="Markdown",
           reply_markup=ai_menu_keyboard(user))

    elif sub_action == "OTHER":
        storage.save_user(chat_id, {"ai_state": "food_log", "pending_food_slot": slot})
        reply(f"Что съел вместо запланированного ({label})? Напиши текстом.", back_to_ai_menu_keyboard())


def find_pending_checkin_slot(chat_id: int) -> str | None:
    """Самый старый неотвеченный опрос за сегодня (или None, если таких нет)."""
    user = storage.get_user(chat_id)
    today = datetime.now(TZ).date().isoformat()
    today_checkins = (user.get("checkins") or {}).get(today, {})
    pending = [(slot, state) for slot, state in today_checkins.items()
               if state.get("sent") and not state.get("responded")]
    if not pending:
        return None
    pending.sort(key=lambda item: item[1].get("sent", ""))
    return pending[0][0]


def handle_checkin_text_reply(chat_id: int, slot: str, text: str) -> None:
    """Свободный текстовый ответ на опрос ("да", "нет", или описание того, что съел)."""
    low = text.strip().lower().rstrip("!.,")
    if low in ("да", "ага", "угу", "yes", "+"):
        apply_checkin_response(chat_id, slot, "OK")
        return
    if low in ("нет", "не", "no", "-"):
        apply_checkin_response(chat_id, slot, "SKIP")
        return

    classification = ai_agent.classify_checkin_reply(text)
    if classification in ("OK", "SKIP"):
        apply_checkin_response(chat_id, slot, classification)
        return

    # OTHER: сам текст уже содержит описание еды — не нужно ждать ещё одно сообщение
    today = datetime.now(TZ).date().isoformat()
    storage.update_checkin(chat_id, today, slot, {"responded": True})
    handle_food_log(chat_id, text, slot)


# ---------- Обработка сообщений ----------

def handle_price_command(chat_id: int, text: str) -> None:
    """Формат: /цена курица 420 — обновляет цену упаковки продукта."""
    parts = text.split()
    if len(parts) < 3:
        examples = "\n".join(
            f"• `/цена {PRODUCTS[k]['name'].lower()} {PRODUCTS[k]['pack_price']}`"
            for k in list(PRODUCTS)[:3])
        tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
           text="Укажи продукт и цену упаковки. Например:\n" + examples +
                "\n\nСписок продуктов: /продукты")
        return

    query = " ".join(parts[1:-1]).lower()
    try:
        price = float(parts[-1].replace(",", "."))
    except ValueError:
        tg("sendMessage", chat_id=chat_id, text="Последним числом укажи цену, например: /цена курица 420")
        return

    matches = [k for k, p in PRODUCTS.items() if query in p["name"].lower()]
    if not matches:
        tg("sendMessage", chat_id=chat_id,
           text=f"Не нашёл продукт «{query}». Посмотреть список: /продукты")
        return
    if len(matches) > 1:
        names = ", ".join(PRODUCTS[k]["name"] for k in matches)
        tg("sendMessage", chat_id=chat_id, text=f"Уточни, что именно: {names}")
        return

    key = matches[0]
    storage.set_price_override(key, price)
    p = PRODUCTS[key]
    tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
       text=f"✅ {p['name']}: упаковка {p['pack']} → *{price:.0f} ₽*\n"
            "Новая цена учтётся при следующем составлении плана.")


def handle_products_command(chat_id: int) -> None:
    overrides = storage.get_price_overrides()
    lines = ["📦 *Продукты и цены*", "_Обновить: /цена название сумма_", ""]
    for key, p in PRODUCTS.items():
        price = overrides.get(key, p["pack_price"])
        mark = " ✏️" if key in overrides else ""
        lines.append(f"{p['name']} — {p['pack']} за {price:.0f} ₽{mark}")
    text = "\n".join(lines)
    for i in range(0, len(text), 3500):
        tg("sendMessage", chat_id=chat_id, text=text[i:i + 3500], parse_mode="Markdown")


def handle_message(msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    low = text.lower()

    if low.startswith(("/цена", "/price")):
        handle_price_command(chat_id, text)
        return

    if low.startswith(("/продукты", "/products")):
        handle_products_command(chat_id)
        return

    if low.startswith(("/ai", "/диетолог")):
        ai_advance(chat_id)
        return

    if low.startswith(("/start", "/menu", "/меню")):
        user = storage.save_user(chat_id, {"ai_state": None})
        if user.get("plan_names"):
            tg("sendMessage", chat_id=chat_id, text=plan_text(user, 0),
               parse_mode="Markdown", reply_markup=plan_keyboard(0))
        else:
            tg("sendMessage", chat_id=chat_id, text=WELCOME, reply_markup=goal_keyboard())
        return

    if msg.get("photo"):
        handle_food_photo(chat_id, msg["photo"])
        return

    user = storage.get_user(chat_id)

    # диалог с ИИ-диетологом (анкета / запись еды / вопрос / напоминания)
    if user.get("ai_state"):
        handle_ai_text(chat_id, user["ai_state"], text)
        return

    # ждём от пользователя сумму бюджета
    if user.get("awaiting_budget"):
        digits = re.sub(r"[^\d]", "", text)
        if digits:
            budget = int(digits)
            if budget < 500:
                tg("sendMessage", chat_id=chat_id,
                   text="Такой суммы на неделю продуктов не хватит. Укажи сумму побольше "
                        "или выбери готовый вариант кнопкой.")
                return
            user = storage.save_user(chat_id, {"budget": budget})
            user = build_and_save(chat_id, user)
            tg("sendMessage", chat_id=chat_id, text=plan_text(user, 0),
               parse_mode="Markdown", reply_markup=plan_keyboard(0))
        else:
            tg("sendMessage", chat_id=chat_id,
               text="Напиши бюджет числом, например: 4000")
        return

    # свободный ответ на опрос "поел ли ты?" — если сейчас есть неотвеченный опрос
    if text:
        pending_slot = find_pending_checkin_slot(chat_id)
        if pending_slot:
            handle_checkin_text_reply(chat_id, pending_slot, text)
            return

    tg("sendMessage", chat_id=chat_id,
       text="Я работаю кнопками 🙂\n\n"
            "/start, /menu — вернуться в меню (план или начало)\n"
            "/ai — ИИ-диетолог (анкета, дневник КБЖУ, напоминания)\n"
            "/продукты — список продуктов и цен\n"
            "/цена — обновить цену продукта")


def handle_callback(cb: dict) -> None:
    data = cb.get("data", "")
    message = cb.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    parts = data.split("|")
    action = parts[0]
    user = storage.get_user(chat_id)

    def edit(text: str, keyboard: dict) -> None:
        # рецепт/график шлются отдельными сообщениями (Telegram не даёт вставить
        # картинку в текстовое) — при любом переходе на другой экран подчищаем
        # то, что осталось от предыдущего, иначе фото копятся в чате.
        stray = user.get("last_recipe_photo_id"), user.get("last_chart_photo_id")
        if any(stray):
            for mid in stray:
                tg_delete(chat_id, mid)
            storage.save_user(chat_id, {"last_recipe_photo_id": None, "last_chart_photo_id": None})
        tg("editMessageText", chat_id=chat_id, message_id=message_id,
           text=text, parse_mode="Markdown", reply_markup=keyboard)

    if action == "START":
        storage.clear_user(chat_id)
        edit(WELCOME, goal_keyboard())

    elif action == "G":
        user = storage.save_user(chat_id, {"goal": parts[1], "restrictions": []})
        edit(f"Цель: *{GOAL_LABELS[parts[1]]}* ✅\n\n"
             "Есть ограничения в питании? Отметь нужное и нажми «Готово».",
             restrictions_keyboard([]))

    elif action == "R":
        key = RESTRICTION_KEYS[int(parts[1])]
        selected = list(user.get("restrictions", []))
        selected.remove(key) if key in selected else selected.append(key)
        storage.save_user(chat_id, {"restrictions": selected})
        tg("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
           reply_markup=restrictions_keyboard(selected))

    elif action == "D":
        edit("Сколько приёмов пищи в день тебе удобно?", meals_keyboard())

    elif action == "M":
        storage.save_user(chat_id, {"meals_per_day": int(parts[1])})
        edit("В каком регионе покупаешь продукты?\n"
             "_Это влияет на расчёт стоимости._", region_keyboard())

    elif action == "REG":
        storage.save_user(chat_id, {"region": parts[1], "awaiting_budget": True})
        edit("Какой бюджет на продукты на неделю?\n\n"
             "Выбери вариант или *напиши свою сумму числом* — например, 4500.",
             budget_keyboard())

    elif action == "B":
        preset = BUDGET_PRESETS[parts[1]]
        user = storage.save_user(chat_id, {"budget": preset["limit"], "awaiting_budget": False})
        user = build_and_save(chat_id, user)
        edit(plan_text(user, 0), plan_keyboard(0))

    elif action == "REGEN":
        if user.get("goal"):
            user = build_and_save(chat_id, user)
            edit(plan_text(user, 0), plan_keyboard(0))

    elif action == "PLAN":
        if user.get("plan_names"):
            edit(plan_text(user, 0), plan_keyboard(0))

    elif action == "NOOP":
        pass

    elif action == "DAY":
        if user.get("plan_names"):
            day = int(parts[1]) % planner.DAYS
            edit(plan_text(user, day), plan_keyboard(day))

    elif action == "SWAP":
        if user.get("plan_names"):
            day = int(parts[1])
            edit("Какое блюдо заменить?", swap_slots_keyboard(user, day))

    elif action == "SWS":
        day, slot = int(parts[1]), int(parts[2])
        options = planner.swap_options(
            user["plan_names"], day, slot, user["meals_per_day"],
            user["goal"], set(user.get("restrictions", [])))
        storage.save_user(chat_id, {"swap_options": options})
        if options:
            current = user["plan_names"][day][slot]
            edit(f"Сейчас: *{current}*\n\nНа что заменить?",
                 swap_options_keyboard(day, slot, options))
        else:
            edit("Для этого блюда нет подходящих замен при твоих ограничениях 🤔",
                 plan_keyboard(day))

    elif action == "SWD":
        day, slot, choice = int(parts[1]), int(parts[2]), int(parts[3])
        options = user.get("swap_options", [])
        if choice < len(options):
            plan_names = [list(d) for d in user["plan_names"]]
            plan_names[day][slot] = options[choice]
            items, total, consumed = planner.rebuild_totals(plan_names, user["region"])
            user = storage.save_user(chat_id, {
                "plan_names": plan_names, "items": items, "total": total,
                "consumed": consumed, "bought": [],
            })
            edit(plan_text(user, day), plan_keyboard(day))
            tg("answerCallbackQuery", callback_query_id=cb["id"],
               text="Блюдо заменено, список покупок пересчитан")
            return

    elif action == "RECIPES":
        day = int(parts[1]) if len(parts) > 1 else 0
        plan_names = user.get("plan_names", [])
        names = planner.recipe_meals_for_day(plan_names, day) if plan_names else []
        if names:
            storage.save_user(chat_id, {"recipe_names": names})
            edit(f"👨‍🍳 *Блюда дня {day + 1}, которые нужно готовить*\n\n"
                 "Выбери блюдо — покажу пошаговый рецепт.",
                 recipes_keyboard(names, day))
        else:
            edit("В этот день нет блюд, требующих долгой готовки 🙂",
                 plan_keyboard(day))

    elif action == "RC":
        day = int(parts[1])
        idx = int(parts[2])
        names = user.get("recipe_names", [])
        if idx < len(names):
            edit(planner.format_recipe(names[idx]), recipe_back_keyboard(day))
            photo_url = photos.search_dish_photo(names[idx])
            if photo_url:
                resp = tg("sendPhoto", chat_id=chat_id, photo=photo_url, caption=names[idx])
                new_id = resp.get("result", {}).get("message_id")
                storage.save_user(chat_id, {"last_recipe_photo_id": new_id})

    elif action == "SHOP":
        day = int(parts[1]) if len(parts) > 1 else 0
        if user.get("items"):
            edit(shopping_text(user), shopping_categories_keyboard(user["items"], user.get("bought", []), day))

    elif action == "SHOPCAT":
        day, category = int(parts[1]), parts[2]
        if user.get("items"):
            edit(shopping_category_text(user, category),
                 shopping_category_keyboard(user["items"], user.get("bought", []), day, category))

    elif action == "T":
        day, category, idx = int(parts[1]), parts[2], int(parts[3])
        bought = list(user.get("bought", []))
        bought.remove(idx) if idx in bought else bought.append(idx)
        user = storage.save_user(chat_id, {"bought": bought})
        edit(shopping_category_text(user, category),
             shopping_category_keyboard(user["items"], bought, day, category))

    elif action == "AI":
        sub = parts[1]
        if sub == "START":
            ai_advance(chat_id, message_id)
        elif sub == "MENU":
            storage.save_user(chat_id, {"ai_state": None})
            edit("🤖 *ИИ-диетолог*\n\nЧто делаем?", ai_menu_keyboard(user))
        elif sub == "LOG":
            storage.save_user(chat_id, {"ai_state": "food_log", "pending_food_slot": None})
            edit("Напиши, что съел — например: «сникерс» или «тарелка борща с хлебом».\n"
                 "Я оценю калории и БЖУ 🍽", back_to_ai_menu_keyboard())
        elif sub == "TODAY":
            edit(ai_today_text(user), back_to_ai_menu_keyboard())
        elif sub == "WEEK":
            edit(ai_week_text(user), back_to_ai_menu_keyboard())
            send_week_chart(chat_id, user)
        elif sub == "REMIND":
            storage.save_user(chat_id, {"ai_state": "reminder_times"})
            edit(ai_remind_text(user), back_to_ai_menu_keyboard())
        elif sub == "ASK":
            storage.save_user(chat_id, {"ai_state": "ask"})
            edit("Спроси что-нибудь про питание — отвечу как диетолог 💬", back_to_ai_menu_keyboard())
        elif sub == "PROFILE":
            edit(ai_profile_text(user), back_to_ai_menu_keyboard())

    elif action == "AIS":
        storage.update_profile(chat_id, {"sex": parts[1]})
        ai_advance(chat_id, message_id)

    elif action == "AIA":
        storage.update_profile(chat_id, {"activity": parts[1]})
        ai_advance(chat_id, message_id)

    elif action == "AIM":
        if parts[1] == "YES":
            storage.save_user(chat_id, {"ai_state": "waist"})
            edit("Объём талии в см? (или «-», чтобы пропустить)", back_to_ai_menu_keyboard())
        else:
            storage.update_profile(chat_id, {"measurements_asked": True})
            ai_advance(chat_id, message_id)

    elif action == "AIL":
        sub = parts[1]
        pending = user.get("pending_food")
        if sub == "ADD" and pending:
            today = datetime.now(TZ).date().isoformat()
            now_t = datetime.now(TZ).strftime("%H:%M")
            entry = {"date": today, "time": now_t, "source": "logged", **pending}
            if user.get("pending_food_slot"):
                entry["slot"] = user["pending_food_slot"]
            storage.add_diary_entry(chat_id, entry)
            storage.save_user(chat_id, {"pending_food": None, "pending_food_slot": None, "ai_state": None})
            edit(f"✅ Записал: *{pending['name']}* — {pending['kcal']} ккал "
                 f"(Б {pending['protein']} Ж {pending['fat']} У {pending['carbs']})", ai_menu_keyboard(user))
        elif sub == "RETRY":
            storage.save_user(chat_id, {"pending_food": None, "ai_state": "food_log"})
            edit("Хорошо, напиши ещё раз, что съел 🍽", back_to_ai_menu_keyboard())
        else:
            storage.save_user(chat_id, {"pending_food": None, "pending_food_slot": None, "ai_state": None})
            edit("Отменил.", ai_menu_keyboard(user))

    elif action == "AIR":
        apply_checkin_response(chat_id, parts[2], parts[1], message_id)

    elif action == "EVE":
        today = datetime.now(TZ).date().isoformat()
        storage.update_checkin(chat_id, today, EVENING_CHECK_SLOT, {"responded": True})
        if parts[1] == "OTHER":
            storage.save_user(chat_id, {"ai_state": "food_log", "pending_food_slot": "snack"})
            edit("Что ещё ты сегодня съел? Напиши текстом 🍽", back_to_ai_menu_keyboard())
        else:
            edit("Отлично, все приёмы пищи за сегодня учтены ✅", ai_menu_keyboard(user))

    elif action == "WK":
        sub = parts[1]
        if sub == "KEEP":
            storage.save_user(chat_id, {"plan_created": datetime.now(TZ).date().isoformat(),
                                         "plan_renewal_notified": False})
            edit("Отлично, оставляем текущее меню ещё на неделю 👍", plan_keyboard(0))
        elif sub == "REGEN":
            if user.get("goal"):
                user = build_and_save(chat_id, user)
                edit(plan_text(user, 0), plan_keyboard(0))
        elif sub == "SWAP":
            storage.save_user(chat_id, {"plan_renewal_notified": False})
            if user.get("plan_names"):
                edit(plan_text(user, 0), plan_keyboard(0))

    elif action == "HOME":
        storage.save_user(chat_id, {"ai_state": None})
        if user.get("plan_names"):
            edit(plan_text(user, 0), plan_keyboard(0))
        else:
            edit(WELCOME, goal_keyboard())

    tg("answerCallbackQuery", callback_query_id=cb["id"])


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "Бот работает 🥗"

    update = request.get_json(silent=True) or {}
    try:
        if "message" in update:
            handle_message(update["message"])
        elif "callback_query" in update:
            handle_callback(update["callback_query"])
    except Exception:
        app.logger.exception("Ошибка при обработке обновления")
        notify_admin_error("webhook")

    return jsonify(ok=True)


@app.route("/setwebhook")
def set_webhook():
    url = request.url_root.replace("http://", "https://")
    return jsonify(tg("setWebhook", url=url))


@app.route("/deletewebhook")
def delete_webhook():
    return jsonify(tg("deleteWebhook"))


def _reload_pythonanywhere_webapp() -> None:
    """git pull только обновляет файлы на диске — воркер продолжает работать со старым
    кодом, пока его явно не перезапустить. Без этого шага деплой выглядел законченным
    (вебхук отвечал 200), а бот на самом деле продолжал работать на старой версии."""
    pa_token = os.getenv("PA_API_TOKEN")
    pa_user = os.getenv("PA_USERNAME")
    pa_domain = os.getenv("PA_DOMAIN")
    if not (pa_token and pa_user and pa_domain):
        app.logger.warning("PA_API_TOKEN/PA_USERNAME/PA_DOMAIN не заданы — пропускаю reload")
        return
    try:
        requests.post(
            f"https://www.pythonanywhere.com/api/v0/user/{pa_user}/webapps/{pa_domain}/reload/",
            headers={"Authorization": f"Token {pa_token}"}, timeout=30,
        )
    except requests.RequestException as e:
        app.logger.error("PA reload error: %s", e)


@app.route("/github-webhook", methods=["POST"])
def github_webhook():
    import hashlib
    import hmac
    import subprocess

    secret = (os.getenv("GITHUB_SECRET") or os.getenv("GITHUB_WEBHOOK_SECRET") or "").encode("utf-8")
    signature = request.headers.get("X-Hub-Signature-256", "")

    if secret:
        payload = request.get_data()
        expected = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return "Unauthorized", 401

    repo_dir = os.getenv("DEPLOY_REPO_DIR", "/home/f6iznj3iP7/dietbot")
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir, "pull", "origin", "main"],
            capture_output=True, text=True, timeout=30,
        )
        app.logger.info("Git pull: %s %s", result.stdout, result.stderr)
    except Exception as e:
        app.logger.error("Git pull error: %s", e)
        return "OK (pull failed)", 200

    _reload_pythonanywhere_webapp()
    return "OK", 200


def _time_due(scheduled: str, now_hm: str, window_minutes: int = 10) -> bool:
    """Напоминание пора отправить, если текущее время попало в окно [scheduled, scheduled+window)."""
    try:
        sched_h, sched_m = (int(x) for x in scheduled.split(":"))
        now_h, now_m = (int(x) for x in now_hm.split(":"))
    except ValueError:
        return False
    return 0 <= (now_h * 60 + now_m) - (sched_h * 60 + sched_m) < window_minutes


def _minutes_since(sent_hm: str, now: datetime) -> int:
    try:
        h, m = (int(x) for x in sent_hm.split(":"))
    except ValueError:
        return 0
    sent_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return int((now - sent_dt).total_seconds() // 60)


def _send_checkin_message(chat_id: int, slot: str, followup: bool) -> None:
    if slot == EVENING_CHECK_SLOT:
        prefix = "🌙 Напоминаю: всё ли учтено сегодня?" if followup else "🌙 Всё ли учтено сегодня?"
        text = f"{prefix}\nЕсли был перекус, который не записали — напиши, посчитаю."
        tg("sendMessage", chat_id=chat_id, text=text, reply_markup=evening_check_keyboard())
        return
    label = MEAL_SLOT_LABELS.get(slot, slot)
    prefix = "⏰ Напоминаю:" if followup else "⏰"
    tg("sendMessage", chat_id=chat_id, text=f"{prefix} Время приёма пищи: {label}\nПоел по плану?",
       reply_markup=reminder_response_keyboard(slot))


def _tick_checkin(chat_id: int, user: dict, today: str, now: datetime, slot: str, time_str: str) -> int:
    """Опрос по одному слоту: шлём один раз по расписанию, если через час нет ответа —
    ровно один повтор, дальше молчим (см. FOLLOWUP_WINDOW_MINUTES)."""
    state = (user.get("checkins") or {}).get(today, {}).get(slot)

    if state is None:
        if not _time_due(time_str, now.strftime("%H:%M")):
            return 0
        _send_checkin_message(chat_id, slot, followup=False)
        storage.update_checkin(chat_id, today, slot, {"sent": now.strftime("%H:%M"),
                                                        "followup_sent": False, "responded": False})
        return 1

    if state.get("responded") or state.get("followup_sent"):
        return 0

    sent_hm = state.get("sent")
    if sent_hm and _minutes_since(sent_hm, now) >= FOLLOWUP_WINDOW_MINUTES:
        _send_checkin_message(chat_id, slot, followup=True)
        storage.update_checkin(chat_id, today, slot, {"followup_sent": True})
        return 1
    return 0


def _tick_weekly_renewal(chat_id: int, user: dict) -> int:
    """Раз в неделю после создания плана — предлагаем обновить меню. Спрашиваем один раз
    и не повторяем, пока пользователь не отреагирует (KEEP сбрасывает таймер)."""
    plan_created = user.get("plan_created")
    if not plan_created or not user.get("plan_names") or user.get("plan_renewal_notified"):
        return 0
    try:
        created_date = datetime.fromisoformat(plan_created).date()
    except ValueError:
        return 0
    if (datetime.now(TZ).date() - created_date).days < WEEK_DAYS:
        return 0
    tg("sendMessage", chat_id=chat_id,
       text="📅 Прошла неделя с последнего плана питания!\nКак тебе меню — обновляем?",
       reply_markup=weekly_renewal_keyboard())
    storage.save_user(chat_id, {"plan_renewal_notified": True})
    return 1


@app.route("/cron/tick")
def cron_tick():
    """
    Дёргается внешним планировщиком раз в 5-10 минут (PythonAnywhere Tasks
    не годится — там минимум раз в день; используй бесплатный cron-job.org).
    Рассылает опросы о приёмах пищи, повторяет один раз через час, вечером
    спрашивает про неучтённые перекусы, раз в неделю предлагает обновить меню.
    """
    if CRON_SECRET and request.args.get("secret") != CRON_SECRET:
        return jsonify(ok=False, error="forbidden"), 403

    now = datetime.now(TZ)
    today = now.date().isoformat()
    now_hm = now.strftime("%H:%M")
    sent = 0

    for chat_id_str, user in storage.all_users().items():
        chat_id = int(chat_id_str)
        try:
            if user.get("reminders_enabled"):
                slots = dict(user.get("reminders") or {})
                slots[EVENING_CHECK_SLOT] = EVENING_CHECK_TIME
                for slot, time_str in slots.items():
                    if time_str:
                        sent += _tick_checkin(chat_id, user, today, now, slot, time_str)
            sent += _tick_weekly_renewal(chat_id, user)
        except Exception:
            # один сломанный пользователь не должен останавливать рассылку остальным
            app.logger.exception("Ошибка в cron/tick для chat_id=%s", chat_id_str)
            notify_admin_error(f"cron/tick chat_id={chat_id_str}")

    return jsonify(ok=True, sent=sent, checked_at=now_hm)


if __name__ == "__main__":
    app.run(debug=True)
