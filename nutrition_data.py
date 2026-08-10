# -*- coding: utf-8 -*-
"""
Питательность ингредиентов и детерминированный расчёт КБЖУ / тегов / целей блюда.

Единый источник правды по КБЖУ: и офлайн-генератор базы блюд
(scripts/generate_meals.py), и работающий бот (ai_agent.generate_meal) считают
макросы ОДНИМ И ТЕМ ЖЕ кодом по одной и той же таблице. ИИ никогда не называет
калорийность сам — он выдаёт только ключи продуктов и граммовку, а числа
считаются здесь. Поэтому придуманных моделью калорий в плане быть не может.

Ключи NUTRI совпадают с ключами products.PRODUCTS (единственное исключение —
white_wine, которого нет в справочнике покупок), поэтому список покупок и
расчёт стоимости в planner.py работают с любым блюдом, собранным из этих ключей.
"""

# ---------- Питательность ингредиентов (на 100г/100мл, либо на штуку для pcs) ----------
# Источник: общепринятые справочные значения (USDA-подобные), округлено.
# flags: какие ограничения НАРУШАЕТ ингредиент: meat/seafood/pork/beef/dairy/gluten/nuts
NUTRI = {
    # белки / мясо / рыба
    "chicken":        (165, 31, 3.6, 0, {"meat"}),
    "chicken_thigh":  (209, 18, 15, 0, {"meat"}),
    "chicken_wings":  (203, 19, 13.5, 0, {"meat"}),
    "chicken_mince":  (143, 17, 8, 0, {"meat"}),
    "turkey":         (135, 30, 1, 0, {"meat"}),
    "turkey_mince":   (120, 20, 4, 0, {"meat"}),
    "beef":           (250, 26, 17, 0, {"meat", "beef"}),
    "beef_mince":     (254, 17, 20, 0, {"meat", "beef"}),
    "veal":           (172, 24, 8, 0, {"meat", "beef"}),
    "lamb":           (294, 25, 21, 0, {"meat"}),
    "pork":           (242, 27, 14, 0, {"meat", "pork"}),
    "pork_mince":     (263, 16, 21, 0, {"meat", "pork"}),
    "pork_ribs":      (277, 21, 21, 0, {"meat", "pork"}),
    "mixed_mince":    (250, 17, 19, 0, {"meat", "pork", "beef"}),
    "rabbit":         (173, 21, 8, 0, {"meat"}),
    "beef_liver":     (135, 20, 3.6, 5.3, {"meat", "beef"}),
    "fish_cod":       (82, 18, 0.7, 0, {"meat", "seafood"}),
    "fish_pollock":   (72, 16, 0.9, 0, {"meat", "seafood"}),
    "fish_pink_salmon": (142, 21, 6, 0, {"meat", "seafood"}),
    "fish_mackerel":  (205, 18, 14, 0, {"meat", "seafood"}),
    "fish_trout":     (208, 20, 13, 0, {"meat", "seafood"}),
    "fish_sardine":   (208, 25, 11, 0, {"meat", "seafood"}),
    "tuna_canned":    (116, 26, 1, 0, {"meat", "seafood"}),
    "shrimp":         (99, 24, 0.3, 0.2, {"meat", "seafood"}),
    "squid":          (92, 16, 1.4, 3.1, {"meat", "seafood"}),
    "mussels":        (86, 12, 2.2, 3.7, {"meat", "seafood"}),
    "eggs":           (78, 6.5, 5.5, 0.6, set()),  # за 1 шт (~50г)
    "eggs_quail":     (14, 1.2, 1, 0.1, set()),   # за 1 шт (~10г)
    "tofu":           (76, 8, 4.8, 1.9, set()),
    "tempeh":         (192, 20, 11, 8, set()),
    "seitan":         (370, 75, 2, 14, {"gluten"}),
    "lentils":        (116, 9, 0.4, 20, set()),
    "chickpeas":      (164, 9, 2.6, 27, set()),
    "beans_red":      (127, 8.7, 0.5, 22.8, set()),
    "beans_white":    (139, 9.7, 0.5, 25, set()),
    "mung_beans":     (105, 7, 0.4, 19, set()),
    "peas_dried":     (118, 8, 0.4, 21, set()),
    "cottage_cheese": (98, 18, 1.8, 3.3, {"dairy"}),
    "cottage_cheese_2": (121, 16, 5, 3, {"dairy"}),
    "greek_yogurt":   (59, 10, 0.4, 3.6, {"dairy"}),
    "yogurt_natural": (66, 3.5, 3.2, 4.7, {"dairy"}),
    # крупы / макароны / хлеб (сухой вес)
    "oats":           (389, 17, 7, 66, set()),
    "oats_flakes":    (352, 12, 6, 61, set()),
    "buckwheat":      (343, 13, 3.4, 72, set()),
    "rice":           (365, 7, 0.7, 80, set()),
    "rice_arborio":   (349, 7, 0.6, 79, set()),
    "brown_rice":     (370, 7.9, 2.9, 77, set()),
    "quinoa":         (368, 14, 6, 64, set()),
    "bulgur":         (342, 12, 1.3, 76, set()),
    "couscous":       (376, 13, 0.6, 77, {"gluten"}),
    "millet":         (378, 11, 4.2, 73, set()),
    "pearl_barley":   (352, 10, 1.2, 78, {"gluten"}),
    "wheat_berries":  (340, 13, 2, 72, {"gluten"}),
    "pasta":          (371, 13, 1.5, 75, {"gluten"}),
    "pasta_wholegrain": (348, 14, 2.5, 68, {"gluten"}),
    "pasta_glutenfree": (360, 8, 1.5, 79, set()),
    "noodles_egg":    (384, 14, 5, 71, {"gluten"}),
    "noodles_rice":   (364, 6, 0.6, 83, set()),
    "noodles_udon":   (127, 4, 0.4, 27, {"gluten"}),
    "noodles_soba":   (99, 5.1, 0.1, 21, {"gluten"}),
    "bread_white":    (265, 9, 3.2, 49, {"gluten"}),
    "bread_rye":      (214, 7, 1.3, 41, {"gluten"}),
    "bread_wholegrain": (247, 10, 3, 41, {"gluten"}),
    "bread_ciabatta": (271, 9, 3, 51, {"gluten"}),
    "bread_baguette": (274, 9, 1.5, 55, {"gluten"}),
    "bread_pita":     (275, 9, 1.2, 55, {"gluten"}),
    "bread_tortilla": (289, 8, 7, 48, {"gluten"}),
    "bread_tortilla_corn": (218, 5.7, 3.1, 44, set()),
    "crispbread":     (334, 9, 1.5, 70, set()),
    "potato":         (77, 2, 0.1, 17, set()),
    "pumpkin":        (26, 1, 0.1, 6.5, set()),
    "flour_wheat":    (364, 10, 1, 76, {"gluten"}),
    # овощи / зелень
    "tomato": (18, 0.9, 0.2, 3.9, set()), "tomato_cherry": (18, 0.9, 0.2, 3.9, set()),
    "cucumber": (16, 0.7, 0.1, 3.6, set()), "spinach": (23, 2.9, 0.4, 3.6, set()),
    "lettuce": (15, 1.4, 0.2, 2.9, set()), "arugula": (25, 2.6, 0.7, 3.7, set()),
    "broccoli": (34, 2.8, 0.4, 7, set()), "cauliflower": (25, 1.9, 0.3, 5, set()),
    "bell_pepper": (31, 1, 0.3, 6, set()), "zucchini": (17, 1.2, 0.3, 3.1, set()),
    "eggplant": (25, 1, 0.2, 6, set()), "carrot": (41, 0.9, 0.2, 10, set()),
    "onion": (40, 1.1, 0.1, 9, set()), "green_onion": (32, 1.8, 0.2, 7.3, set()),
    "cabbage": (25, 1.3, 0.1, 6, set()), "cabbage_red": (31, 1.4, 0.2, 7.4, set()),
    "mushrooms": (22, 3.1, 0.3, 3.3, set()), "mushrooms_oyster": (33, 3.3, 0.4, 6.1, set()),
    "avocado": (240, 3, 22, 12, set()),  # за 1 шт (~150г)
    "asparagus": (20, 2.2, 0.1, 3.9, set()), "celery": (16, 0.7, 0.2, 3, set()),
    "beetroot": (43, 1.6, 0.2, 10, set()), "radish": (16, 0.7, 0.1, 3.4, set()),
    "garlic": (149, 6.4, 0.5, 33, set()), "ginger_root": (80, 1.8, 0.8, 18, set()),
    "chili": (40, 1.9, 0.4, 9, set()), "corn": (86, 3.3, 1.4, 19, set()),
    "green_peas": (81, 5.4, 0.4, 14, set()), "olives": (115, 0.8, 11, 6, set()),
    "hummus": (166, 8, 9.6, 14, set()),
    # фрукты / ягоды / сухофрукты
    "banana": (89, 1.1, 0.3, 23, set()), "apple": (52, 0.3, 0.2, 14, set()),
    "orange": (47, 0.9, 0.1, 12, set()), "kiwi": (61, 1.1, 0.5, 15, set()),
    "grapes": (69, 0.7, 0.2, 18, set()), "pear": (57, 0.4, 0.1, 15, set()),
    "peach": (39, 0.9, 0.3, 10, set()), "mango": (60, 0.8, 0.4, 15, set()),
    "pineapple": (50, 0.5, 0.1, 13, set()), "pomegranate": (83, 1.7, 1.2, 19, set()),
    "watermelon": (30, 0.6, 0.2, 8, set()), "melon": (34, 0.8, 0.2, 8, set()),
    "lemon": (29, 1.1, 0.3, 9, set()), "lime": (30, 0.7, 0.2, 11, set()),
    "mandarin": (53, 0.8, 0.3, 13, set()), "plum": (46, 0.7, 0.3, 11, set()),
    "berries": (57, 0.7, 0.3, 14, set()), "blueberry": (57, 0.7, 0.3, 14, set()),
    "strawberry": (32, 0.7, 0.3, 7.7, set()), "cranberry": (46, 0.4, 0.1, 12, set()),
    "dates": (282, 2.5, 0.4, 75, set()), "dried_apricots": (241, 3.4, 0.5, 63, set()),
    "raisins": (299, 3.1, 0.5, 79, set()), "prunes": (240, 2.2, 0.4, 64, set()),
    "dried_figs": (249, 3.3, 0.9, 64, set()),
    # молочное / жиры
    "milk_cow": (60, 3.2, 3.3, 4.8, {"dairy"}), "milk_1pct": (42, 3.4, 1, 5, {"dairy"}),
    "kefir": (40, 3, 1, 4.7, {"dairy"}), "ryazhenka": (54, 2.8, 2.5, 4.2, {"dairy"}),
    "sour_cream": (193, 2.8, 20, 3.2, {"dairy"}), "sour_cream_20": (206, 2.8, 20, 3.2, {"dairy"}),
    "butter": (717, 0.9, 81, 0.1, {"dairy"}),
    "cheese_russian": (363, 24, 29, 0.3, {"dairy"}), "cheese_mozzarella": (280, 22, 21, 2.2, {"dairy"}),
    "cheese_feta": (264, 14, 21, 4, {"dairy"}), "cheese_cottage": (98, 18, 1.8, 3.3, {"dairy"}),
    "cheese_cream": (342, 6, 34, 4, {"dairy"}),
    "plant_milk": (35, 1, 1.5, 4, set()), "milk_oat": (48, 1, 1.5, 7, set()),
    "milk_almond": (17, 0.6, 1.2, 0.6, {"nuts"}), "milk_soy": (33, 3.3, 1.8, 1.8, set()),
    "milk_coconut": (230, 2.3, 24, 3.3, set()), "coconut_cream": (330, 3.3, 34, 6.7, set()),
    "olive_oil": (884, 0, 100, 0, set()), "olive_oil_extra": (884, 0, 100, 0, set()),
    "sunflower_oil": (884, 0, 100, 0, set()), "sesame_oil": (884, 0, 100, 0, set()),
    "coconut_oil": (862, 0, 100, 0, set()), "flax_oil": (884, 0, 100, 0, set()),
    # орехи / семена
    "walnuts": (654, 15, 65, 14, {"nuts"}), "almonds": (579, 21, 50, 22, {"nuts"}),
    "cashews": (553, 18, 44, 30, {"nuts"}), "pistachios": (562, 20, 45, 28, {"nuts"}),
    "pine_nuts": (673, 14, 68, 13, {"nuts"}), "nuts_mix": (600, 18, 52, 20, {"nuts"}),
    "peanut_butter": (588, 25, 50, 20, {"nuts"}), "peanut_butter_nat": (588, 25, 50, 20, {"nuts"}),
    "tahini": (595, 17, 54, 21, {"nuts"}),
    "chia_seeds": (486, 17, 31, 42, set()), "flax_seeds": (534, 18, 42, 29, set()),
    "sesame_seeds": (573, 18, 50, 23, set()), "sunflower_seeds": (584, 21, 51, 20, set()),
    "pumpkin_seeds": (559, 30, 49, 11, set()),
    # соусы / сладкое / прочее
    "honey": (304, 0.3, 0, 82, set()), "maple_syrup": (260, 0, 0.1, 67, set()),
    "sugar": (387, 0, 0, 100, set()), "brown_sugar": (380, 0, 0, 98, set()),
    "cocoa_powder": (228, 20, 14, 58, set()), "dark_chocolate": (546, 5, 31, 61, set()),
    "coconut_flakes": (660, 6.9, 65, 23, set()),
    "tomato_sauce": (30, 1.3, 0.3, 6, set()), "tomato_paste": (82, 4.3, 0.5, 19, set()),
    "ketchup": (101, 1.7, 0.2, 26, set()), "mustard": (66, 4.4, 4, 5, set()),
    "mayo_light": (280, 1, 28, 6, {"dairy"}), "soy_sauce": (53, 8, 0.1, 4.9, set()),
    "soy_sauce_tamari": (60, 10, 0.1, 5.6, set()), "pesto": (303, 3.6, 30, 4, {"dairy", "nuts"}),
    "adjika": (65, 2, 1, 12, set()), "tkemali": (60, 1, 0.3, 14, set()),
    "protein_powder": (380, 75, 5, 8, {"dairy"}),
    "white_wine": (82, 0.1, 0, 2.6, set()),
    "gelatin": (335, 87, 0.1, 0, set()),
    # специи / зелень (используются в малых количествах, но нужны в таблице)
    "dill": (43, 3.5, 1.1, 7, set()), "parsley": (36, 3, 0.8, 6, set()),
    "cilantro": (23, 2.1, 0.5, 3.7, set()), "basil_fresh": (23, 3.2, 0.6, 2.7, set()),
    "rosemary": (131, 3.3, 5.9, 21, set()), "thyme": (101, 5.6, 1.7, 24, set()),
    "oregano": (265, 9, 4.3, 69, set()), "paprika": (282, 14, 13, 54, set()),
    "cumin": (375, 18, 22, 44, set()), "curry": (325, 14, 14, 58, set()),
    "turmeric": (312, 9.7, 3.3, 67, set()), "nutmeg": (525, 6, 36, 49, set()),
    "cinnamon": (247, 4, 1.2, 81, set()), "black_pepper": (251, 10, 3.3, 64, set()),
    "salt": (0, 0, 0, 0, set()), "mint": (44, 3.3, 0.7, 8, set()),
}

FLAG_TO_TAG = {  # какой ингредиентный флаг блокирует какой тег
    "meat": "vegetarian", "seafood": "vegetarian",
    "gluten": "gluten_free", "dairy": "lactose_free",
}

# eggs / eggs_quail / avocado в products.PRODUCTS имеют unit="pcs": их
# "количество" — это ШТУКИ, а не граммы, и значения в NUTRI даны за штуку.
# Поэтому для них множитель равен количеству, а не количеству/100.
PER_PIECE_KEYS = ("eggs", "eggs_quail", "avocado")

# Разумные границы калорийности одного приёма пищи: (нижняя, верхняя).
# Используются в compute_goals (какой цели подходит блюдо) и как основа
# проверки правдоподобности КБЖУ у сгенерированных ИИ блюд.
MEAL_KCAL_THRESHOLDS = {"breakfast": (280, 420), "snack": (150, 280), "lunch": (400, 600), "dinner": (350, 550)}
DEFAULT_KCAL_THRESHOLDS = (350, 550)


def dish_flags(ingredients: dict) -> set:
    flags = set()
    for key in ingredients:
        flags |= NUTRI[key][4]
    return flags


def compute_tags(ingredients: dict) -> list:
    flags = dish_flags(ingredients)
    tags = []
    if "meat" not in flags and "seafood" not in flags:
        tags.append("vegetarian")
    if "gluten" not in flags:
        tags.append("gluten_free")
    if "dairy" not in flags:
        tags.append("lactose_free")
    if "nuts" not in flags:
        tags.append("no_nuts")
    if "seafood" not in flags:
        tags.append("no_seafood")
    if "pork" not in flags:
        tags.append("no_pork")
    if "beef" not in flags:
        tags.append("no_beef")
    return tags


def compute_macros(ingredients: dict) -> dict:
    kcal = protein = fat = carbs = 0.0
    for key, amount in ingredients.items():
        k, p, f, c, _ = NUTRI[key]
        factor = amount if key in PER_PIECE_KEYS else amount / 100.0
        kcal += k * factor
        protein += p * factor
        fat += f * factor
        carbs += c * factor
    return {"kcal": round(kcal), "protein": round(protein), "fat": round(fat), "carbs": round(carbs)}


def compute_goals(kcal: int, meal_type: str) -> list:
    low, high = MEAL_KCAL_THRESHOLDS.get(meal_type, DEFAULT_KCAL_THRESHOLDS)
    goals = ["variety"]
    if kcal <= high:
        goals.append("loss")
    if kcal >= low:
        goals.append("maintain")
    if kcal >= low - 50:
        goals.append("gain")
    return sorted(set(goals), key=["loss", "gain", "maintain", "variety"].index)
