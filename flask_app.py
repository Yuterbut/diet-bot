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
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

import planner
import storage
from meals_data import BUDGET_PRESETS, GOAL_LABELS, MEAL_TYPE_LABELS, RESTRICTION_LABELS
from products import PRODUCTS, REGIONS

load_dotenv(Path(__file__).parent / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN (проверь файл .env рядом с flask_app.py)")

API_URL = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

RESTRICTION_KEYS = list(RESTRICTION_LABELS.keys())
WELCOME = "Привет! 👋 Составлю план питания на неделю с учётом бюджета.\n\nКакая у тебя цель?"


def tg(method: str, **payload):
    try:
        return requests.post(f"{API_URL}/{method}", json=payload, timeout=15).json()
    except requests.RequestException as e:
        app.logger.error("Ошибка запроса к Telegram: %s", e)
        return {}


# ---------- Клавиатуры ----------

def goal_keyboard():
    return {"inline_keyboard": [
        [{"text": "📉 Похудение", "callback_data": "G|loss"}],
        [{"text": "📈 Набор массы", "callback_data": "G|gain"}],
        [{"text": "⚖️ Поддержание веса", "callback_data": "G|maintain"}],
        [{"text": "🎲 Просто разнообразие", "callback_data": "G|variety"}],
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
        [{"text": "👨‍🍳 Рецепты", "callback_data": "RECIPES"}],
        [{"text": "🛒 Список покупок", "callback_data": "SHOP"}],
        [{"text": "🔄 Другой вариант", "callback_data": "REGEN"},
         {"text": "⚙️ Заново", "callback_data": "START"}],
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


def recipes_keyboard(names: list, day: int = 0):
    rows = [[{"text": f"👨‍🍳 {name}", "callback_data": f"RC|{i}"}]
            for i, name in enumerate(names)]
    rows.append([{"text": "⬅️ Назад к меню", "callback_data": f"DAY|{day}"}])
    return {"inline_keyboard": rows}


def recipe_back_keyboard():
    return {"inline_keyboard": [
        [{"text": "⬅️ К списку рецептов", "callback_data": "RECIPES"}],
        [{"text": "📋 К меню", "callback_data": "DAY|0"}],
    ]}


def shopping_keyboard(items: list, bought: list):
    rows = []
    for i, item in enumerate(items):
        box = "✅" if i in bought else "⬜️"
        rows.append([{
            "text": f"{box} {item['name']} · {item['amount_text']} · {item['cost']} ₽",
            "callback_data": f"T|{i}",
        }])
    rows.append([{"text": "📋 Вернуться к меню", "callback_data": "DAY|0"}])
    return {"inline_keyboard": rows}


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
    })


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

    if low.startswith("/start"):
        storage.clear_user(chat_id)
        tg("sendMessage", chat_id=chat_id, text=WELCOME, reply_markup=goal_keyboard())
        return

    if low.startswith(("/цена", "/price")):
        handle_price_command(chat_id, text)
        return

    if low.startswith(("/продукты", "/products")):
        handle_products_command(chat_id)
        return

    user = storage.get_user(chat_id)

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

    tg("sendMessage", chat_id=chat_id,
       text="Я работаю кнопками 🙂\n\n"
            "/start — составить план питания\n"
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
        names = planner.recipe_meals(user.get("plan_names", []))
        if names:
            storage.save_user(chat_id, {"recipe_names": names})
            edit("👨‍🍳 *Блюда недели, которые нужно готовить*\n\n"
                 "Выбери блюдо — покажу пошаговый рецепт.",
                 recipes_keyboard(names))
        else:
            edit("В этом меню нет блюд, требующих долгой готовки 🙂",
                 plan_keyboard(0))

    elif action == "RC":
        names = user.get("recipe_names", [])
        idx = int(parts[1])
        if idx < len(names):
            edit(planner.format_recipe(names[idx]), recipe_back_keyboard())

    elif action == "SHOP":
        if user.get("items"):
            edit(shopping_text(user), shopping_keyboard(user["items"], user.get("bought", [])))

    elif action == "T":
        idx = int(parts[1])
        bought = list(user.get("bought", []))
        bought.remove(idx) if idx in bought else bought.append(idx)
        user = storage.save_user(chat_id, {"bought": bought})
        edit(shopping_text(user), shopping_keyboard(user["items"], bought))

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

    return jsonify(ok=True)


@app.route("/setwebhook")
def set_webhook():
    url = request.url_root.replace("http://", "https://")
    return jsonify(tg("setWebhook", url=url))


@app.route("/deletewebhook")
def delete_webhook():
    return jsonify(tg("deleteWebhook"))


if __name__ == "__main__":
    app.run(debug=True)

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    import hmac
    import hashlib
    import subprocess
    import os

    secret = os.environ.get('GITHUB_SECRET', '').encode('utf-8')
    signature = request.headers.get('X-Hub-Signature-256', '')

    if secret:
        payload = request.get_data()
        expected = 'sha256=' + hmac.new(secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return 'Unauthorized', 401

    try:
        result = subprocess.run(
            ['git', '-C', '/home/f6iznj3iP7/dietbot', 'pull', 'origin', 'main'],
            capture_output=True, text=True, timeout=30
        )
        print(f"Git pull: {result.stdout}")
    except Exception as e:
        print(f"Git pull error: {e}")

    return 'OK', 200
