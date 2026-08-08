"""
Справочник продуктов: цены и фасовки.

ВАЖНО: цены здесь — ОРИЕНТИРОВОЧНЫЕ, их нужно обновлять руками.
Автоматически тянуть цены с сайта магазина нельзя (нет публичного API,
бесплатный хостинг не пускает запросы на такие сайты).

Как обновить: зайди в приложение или на сайт магазина, посмотри цену
и поправь поле "pack_price". Остальное менять не нужно.
Рекомендуется освежать цены раз в 2-3 месяца.

Формат записи:
    "ключ": {
        "name": "Как показывать в списке покупок",
        "unit": "g" | "ml" | "pcs",   # в чём измеряем в рецептах
        "pack": 400,                   # сколько в одной упаковке
        "pack_price": 49,              # сколько стоит упаковка, руб
    }
"""

PRODUCTS = {
    # --- Крупы, макароны, хлеб ---
    "oats":         {"name": "Овсяные хлопья",      "unit": "g", "pack": 400,  "pack_price": 65},
    "buckwheat":    {"name": "Гречка",              "unit": "g", "pack": 800,  "pack_price": 95},
    "rice":         {"name": "Рис",                 "unit": "g", "pack": 800,  "pack_price": 105},
    "brown_rice":   {"name": "Рис бурый",           "unit": "g", "pack": 500,  "pack_price": 125},
    "quinoa":       {"name": "Киноа",               "unit": "g", "pack": 300,  "pack_price": 240},
    "pasta":        {"name": "Макароны",            "unit": "g", "pack": 450,  "pack_price": 75},
    "bread":        {"name": "Хлеб",                "unit": "g", "pack": 400,  "pack_price": 55},

    # --- Мясо, рыба, яйца ---
    "chicken":      {"name": "Куриное филе",        "unit": "g", "pack": 1000, "pack_price": 380},
    "turkey":       {"name": "Филе индейки",        "unit": "g", "pack": 800,  "pack_price": 450},
    "beef":         {"name": "Говядина",            "unit": "g", "pack": 800,  "pack_price": 640},
    "fish":         {"name": "Рыба (минтай/треска)","unit": "g", "pack": 700,  "pack_price": 320},
    "eggs":         {"name": "Яйца",                "unit": "pcs","pack": 10,  "pack_price": 110},

    # --- Молочное ---
    "cottage_cheese":{"name": "Творог",             "unit": "g", "pack": 350,  "pack_price": 130},
    "greek_yogurt": {"name": "Греческий йогурт",    "unit": "g", "pack": 500,  "pack_price": 180},
    "feta":         {"name": "Брынза",              "unit": "g", "pack": 250,  "pack_price": 190},
    "plant_milk":   {"name": "Растительное молоко", "unit": "ml","pack": 1000, "pack_price": 140},

    # --- Овощи, зелень ---
    "tomato":       {"name": "Помидоры",            "unit": "g", "pack": 1000, "pack_price": 190},
    "cucumber":     {"name": "Огурцы",              "unit": "g", "pack": 1000, "pack_price": 180},
    "spinach":      {"name": "Шпинат",              "unit": "g", "pack": 200,  "pack_price": 130},
    "lettuce":      {"name": "Салат листовой",      "unit": "g", "pack": 150,  "pack_price": 110},
    "broccoli":     {"name": "Брокколи",            "unit": "g", "pack": 400,  "pack_price": 175},
    "vegetables_mix":{"name": "Овощная смесь",      "unit": "g", "pack": 400,  "pack_price": 130},
    "potato":       {"name": "Картофель",           "unit": "g", "pack": 1000, "pack_price": 60},
    "cabbage":      {"name": "Капуста белокочанная","unit": "g", "pack": 1000, "pack_price": 55},
    "mushrooms":    {"name": "Шампиньоны",          "unit": "g", "pack": 400,  "pack_price": 150},
    "carrot":       {"name": "Морковь",             "unit": "g", "pack": 1000, "pack_price": 55},
    "onion":        {"name": "Лук репчатый",        "unit": "g", "pack": 1000, "pack_price": 50},
    "avocado":      {"name": "Авокадо",             "unit": "pcs","pack": 1,   "pack_price": 140},

    # --- Бобовые, растительный белок ---
    "lentils":      {"name": "Чечевица",            "unit": "g", "pack": 450,  "pack_price": 115},
    "chickpeas":    {"name": "Нут",                 "unit": "g", "pack": 450,  "pack_price": 125},
    "tofu":         {"name": "Тофу",                "unit": "g", "pack": 300,  "pack_price": 210},

    # --- Фрукты, орехи, сладкое ---
    "banana":       {"name": "Бананы",              "unit": "g", "pack": 1000, "pack_price": 130},
    "apple":        {"name": "Яблоки",              "unit": "g", "pack": 1000, "pack_price": 140},
    "berries":      {"name": "Ягоды замороженные",  "unit": "g", "pack": 300,  "pack_price": 210},
    "walnuts":      {"name": "Грецкие орехи",       "unit": "g", "pack": 150,  "pack_price": 250},
    "nuts_mix":     {"name": "Орехи и сухофрукты",  "unit": "g", "pack": 200,  "pack_price": 260},
    "peanut_butter":{"name": "Арахисовая паста",    "unit": "g", "pack": 300,  "pack_price": 240},
    "honey":        {"name": "Мёд",                 "unit": "g", "pack": 250,  "pack_price": 260},

    # --- Прочее ---
    "tomato_sauce": {"name": "Томатный соус",       "unit": "g", "pack": 350,  "pack_price": 95},
    "olive_oil":    {"name": "Масло растительное",  "unit": "ml","pack": 800,  "pack_price": 180},
}


# --- Региональные коэффициенты ---
# Цены выше заданы для средней полосы России (коэффициент 1.0).
# Для других регионов бот умножает их на коэффициент ниже.
# Значения ориентировочные — можно поправить под свои наблюдения.

REGIONS = {
    "center":   {"name": "Центр России / Поволжье", "coef": 1.00},
    "msk":      {"name": "Москва и область",         "coef": 1.15},
    "spb":      {"name": "Санкт-Петербург",          "coef": 1.10},
    "south":    {"name": "Юг России",                "coef": 0.95},
    "ural":     {"name": "Урал и Сибирь",            "coef": 1.05},
    "far_east": {"name": "Дальний Восток и Север",   "coef": 1.35},
}

DEFAULT_REGION = "center"


def region_coef(region_key: str) -> float:
    return REGIONS.get(region_key, REGIONS[DEFAULT_REGION])["coef"]


def pack_price(product_key: str, region_key: str = DEFAULT_REGION) -> float:
    """Цена упаковки с учётом региона."""
    return PRODUCTS[product_key]["pack_price"] * region_coef(region_key)


def price_per_unit(product_key: str, region_key: str = DEFAULT_REGION) -> float:
    """Цена за 1 грамм / мл / штуку с учётом региона."""
    p = PRODUCTS[product_key]
    return pack_price(product_key, region_key) / p["pack"]


def format_amount(product_key: str, amount: float) -> str:
    """Человекочитаемое количество: 1200 г -> '1.2 кг', 3 pcs -> '3 шт'."""
    unit = PRODUCTS[product_key]["unit"]
    if unit == "pcs":
        return f"{int(round(amount))} шт"
    if amount >= 1000:
        value = amount / 1000
        suffix = "кг" if unit == "g" else "л"
        return f"{value:.1f}".rstrip("0").rstrip(".") + f" {suffix}"
    return f"{int(round(amount))} {'г' if unit == 'g' else 'мл'}"
