# -*- coding: utf-8 -*-
"""
Генератор расширенной базы блюд (150-200+ шт) с реально посчитанным КБЖУ
(из ингредиентов, а не придуманным), рецептом для каждого блюда, кухней
и расширенными тегами ограничений. Пишет итоговый meals_data.py.

Запуск: python scripts/generate_meals.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

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

DISPLAY_NAMES = {
    "chicken": "куриное филе", "chicken_thigh": "куриные бёдра", "chicken_wings": "куриные крылышки",
    "chicken_mince": "куриный фарш", "turkey": "филе индейки", "turkey_mince": "фарш индейки",
    "beef": "говядину", "beef_mince": "говяжий фарш", "veal": "телятину", "lamb": "баранину",
    "pork": "свинину", "pork_mince": "свиной фарш", "pork_ribs": "свиные рёбрышки",
    "mixed_mince": "смешанный фарш", "rabbit": "кролика", "beef_liver": "говяжью печень",
    "fish_cod": "треску", "fish_pollock": "минтай", "fish_pink_salmon": "горбушу", "fish_mackerel": "скумбрию",
    "fish_trout": "форель", "fish_sardine": "сардину", "tuna_canned": "тунец", "shrimp": "креветки",
    "squid": "кальмары", "mussels": "мидии",
    "eggs": "яйца", "eggs_quail": "перепелиные яйца",
    "tofu": "тофу", "tempeh": "темпе", "seitan": "сейтан",
    "lentils": "чечевицу", "chickpeas": "нут", "beans_red": "красную фасоль", "beans_white": "белую фасоль",
    "mung_beans": "маш", "peas_dried": "горох",
    "cottage_cheese": "творог", "cottage_cheese_2": "творог", "greek_yogurt": "греческий йогурт",
    "yogurt_natural": "натуральный йогурт",
    "oats": "овсяные хлопья", "oats_flakes": "овсяные хлопья", "buckwheat": "гречку", "rice": "рис",
    "rice_arborio": "рис арборио", "brown_rice": "бурый рис", "quinoa": "киноа", "bulgur": "булгур",
    "couscous": "кускус", "millet": "пшено", "pearl_barley": "перловку", "wheat_berries": "полбу",
    "pasta": "макароны", "pasta_wholegrain": "цельнозерновые макароны", "pasta_glutenfree": "макароны без глютена",
    "noodles_egg": "яичную лапшу", "noodles_rice": "рисовую лапшу", "noodles_udon": "лапшу удон",
    "noodles_soba": "лапшу соба", "bread_white": "белый хлеб", "bread_rye": "ржаной хлеб",
    "bread_wholegrain": "цельнозерновой хлеб", "bread_ciabatta": "чиабатту", "bread_baguette": "багет",
    "bread_pita": "питу", "bread_tortilla": "тортилью", "bread_tortilla_corn": "кукурузную тортилью",
    "crispbread": "хлебцы", "potato": "картофель", "pumpkin": "тыкву", "flour_wheat": "муку",
    "tomato": "помидоры", "tomato_cherry": "черри", "cucumber": "огурцы", "spinach": "шпинат",
    "lettuce": "листья салата", "arugula": "руколу", "broccoli": "брокколи", "cauliflower": "цветную капусту",
    "bell_pepper": "болгарский перец", "zucchini": "кабачок", "eggplant": "баклажан", "carrot": "морковь",
    "onion": "лук", "green_onion": "зелёный лук", "cabbage": "капусту", "cabbage_red": "краснокочанную капусту",
    "mushrooms": "грибы", "mushrooms_oyster": "вешенки", "avocado": "авокадо", "asparagus": "спаржу",
    "celery": "сельдерей", "beetroot": "свёклу", "radish": "редис", "garlic": "чеснок",
    "ginger_root": "имбирь", "chili": "перец чили", "corn": "кукурузу", "green_peas": "зелёный горошек",
    "olives": "маслины", "hummus": "хумус",
    "banana": "банан", "apple": "яблоко", "orange": "апельсин", "kiwi": "киви", "grapes": "виноград",
    "pear": "грушу", "peach": "персик", "mango": "манго", "pineapple": "ананас", "pomegranate": "гранат",
    "watermelon": "арбуз", "melon": "дыню", "lemon": "лимон", "lime": "лайм", "mandarin": "мандарин",
    "plum": "сливу", "berries": "ягоды", "blueberry": "чернику", "strawberry": "клубнику",
    "cranberry": "клюкву", "dates": "финики", "dried_apricots": "курагу", "raisins": "изюм",
    "prunes": "чернослив", "dried_figs": "инжир",
    "milk_cow": "молоко", "milk_1pct": "молоко", "kefir": "кефир", "ryazhenka": "ряженку",
    "sour_cream": "сметану", "sour_cream_20": "сметану", "butter": "сливочное масло",
    "cheese_russian": "сыр", "cheese_mozzarella": "моцареллу", "cheese_feta": "фету",
    "cheese_cottage": "творог", "cheese_cream": "творожный сыр",
    "plant_milk": "растительное молоко", "milk_oat": "овсяное молоко", "milk_almond": "миндальное молоко",
    "milk_soy": "соевое молоко", "milk_coconut": "кокосовое молоко", "coconut_cream": "кокосовые сливки",
    "olive_oil": "оливковое масло", "olive_oil_extra": "оливковое масло", "sunflower_oil": "подсолнечное масло",
    "sesame_oil": "кунжутное масло", "coconut_oil": "кокосовое масло", "flax_oil": "льняное масло",
    "walnuts": "грецкие орехи", "almonds": "миндаль", "cashews": "кешью", "pistachios": "фисташки",
    "pine_nuts": "кедровые орехи", "nuts_mix": "орехи", "peanut_butter": "арахисовую пасту",
    "peanut_butter_nat": "арахисовую пасту", "tahini": "тахини", "chia_seeds": "семена чиа",
    "flax_seeds": "семена льна", "sesame_seeds": "кунжут", "sunflower_seeds": "семечки",
    "pumpkin_seeds": "тыквенные семечки",
    "honey": "мёд", "maple_syrup": "кленовый сироп", "sugar": "сахар", "brown_sugar": "сахар",
    "cocoa_powder": "какао", "dark_chocolate": "тёмный шоколад", "coconut_flakes": "кокосовую стружку",
    "tomato_sauce": "томатный соус", "tomato_paste": "томатную пасту", "ketchup": "кетчуп",
    "mustard": "горчицу", "mayo_light": "лёгкий майонез", "soy_sauce": "соевый соус",
    "soy_sauce_tamari": "соус тамари", "pesto": "песто", "adjika": "аджику", "tkemali": "ткемали",
    "protein_powder": "протеин", "white_wine": "белое вино", "gelatin": "желатин",
    "dill": "укроп", "parsley": "петрушку", "cilantro": "кинзу", "basil_fresh": "базилик",
    "rosemary": "розмарин", "thyme": "тимьян", "oregano": "орегано", "paprika": "паприку",
    "cumin": "зиру", "curry": "карри", "turmeric": "куркуму", "nutmeg": "мускатный орех",
    "cinnamon": "корицу", "black_pepper": "чёрный перец", "salt": "соль", "mint": "мяту",
}

FLAG_TO_TAG = {  # какой ингредиентный флаг блокирует какой тег
    "meat": "vegetarian", "seafood": "vegetarian",
    "gluten": "gluten_free", "dairy": "lactose_free",
}


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
        factor = amount if key in ("eggs", "eggs_quail", "avocado") else amount / 100.0
        kcal += k * factor
        protein += p * factor
        fat += f * factor
        carbs += c * factor
    return {"kcal": round(kcal), "protein": round(protein), "fat": round(fat), "carbs": round(carbs)}


def compute_goals(kcal: int, meal_type: str) -> list:
    thresholds = {"breakfast": (280, 420), "snack": (150, 280), "lunch": (400, 600), "dinner": (350, 550)}
    low, high = thresholds.get(meal_type, (350, 550))
    goals = ["variety"]
    if kcal <= high:
        goals.append("loss")
    if kcal >= low:
        goals.append("maintain")
    if kcal >= low - 50:
        goals.append("gain")
    return sorted(set(goals), key=["loss", "gain", "maintain", "variety"].index)


def name_ing(key: str) -> str:
    return DISPLAY_NAMES.get(key, key)


# В названиях блюд протеин стоит в начале как подлежащее — там нужен именительный
# падеж, а не винительный из DISPLAY_NAMES (тот сделан под фразы рецепта вида
# "Треску обжарить...", где винительный корректен как вынесенное дополнение).
NOMINATIVE_OVERRIDE = {
    "fish_cod": "треска", "fish_pink_salmon": "горбуша", "fish_mackerel": "скумбрия",
    "fish_sardine": "сардина", "beef": "говядина", "veal": "телятина", "lamb": "баранина",
    "pork": "свинина", "rabbit": "кролик", "lentils": "чечевица", "beef_liver": "говяжья печень",
}


def name_ing_title(key: str) -> str:
    return NOMINATIVE_OVERRIDE.get(key, name_ing(key))


DISHES = []
SEEN_NAMES = set()


def add_dish(meal_type, name, ingredients, cuisine, difficulty, time, steps):
    if name in SEEN_NAMES:
        name = f"{name} (вариант {sum(1 for n in SEEN_NAMES if n.startswith(name))+1})"
    SEEN_NAMES.add(name)
    for key in ingredients:
        if key not in NUTRI:
            raise KeyError(f"Нет данных о питательности для '{key}' (блюдо: {name})")
    macros = compute_macros(ingredients)
    dish = {
        "name": name,
        "goals": compute_goals(macros["kcal"], meal_type),
        "tags": compute_tags(ingredients),
        "cuisine": cuisine,
        "difficulty": difficulty,
        "time": time,
        "ingredients": ingredients,
        **macros,
        "recipe": {"time": time, "steps": steps},
    }
    DISHES.append((meal_type, dish))


# ================= ЗАВТРАКИ =================
PORRIDGE_BASES = [("oats", 60, "Овсяная каша"), ("buckwheat", 60, "Гречневая каша"),
                   ("rice", 60, "Рисовая каша"), ("quinoa", 60, "Каша из киноа"),
                   ("millet", 60, "Пшённая каша"), ("bulgur", 60, "Каша из булгура")]
PORRIDGE_TOPPINGS = [
    ("banana", 100, "бананом", "банан", "international"), ("apple", 120, "яблоком", "яблоко", "international"),
    ("berries", 80, "ягодами", "ягоды", "international"), ("walnuts", 15, "грецкими орехами", "грецкие орехи", "international"),
    ("dried_apricots", 30, "курагой", "курагу", "middle_eastern"), ("dates", 30, "финиками", "финики", "middle_eastern"),
    ("almonds", 15, "миндалём", "миндаль", "international"), ("cocoa_powder", 8, "какао", "какао", "international"),
]
for base_key, base_amt, base_name in PORRIDGE_BASES:
    for top_key, top_amt, top_label, top_acc, cuisine in PORRIDGE_TOPPINGS:
        liquid = "milk_cow" if base_key != "rice" else "plant_milk"
        ing = {base_key: base_amt, liquid: 150, top_key: top_amt, "honey": 10}
        add_dish("breakfast", f"{base_name} с {top_label}", ing, cuisine, "easy", 15, [
            "Крупу сварить на молоке 10-12 мин, помешивая.",
            f"Добавить {top_acc} и мёд.", "Подавать тёплой.",
        ])

EGG_STYLES = [
    ("Омлет", {"eggs": 2, "milk_cow": 40, "butter": 5}, "international",
     ["Яйца взбить с молоком.", "Обжарить на масле под крышкой 4-5 мин."]),
    ("Яичница с овощами", {"eggs": 2, "tomato": 80, "bell_pepper": 50, "olive_oil": 10}, "mediterranean",
     ["Овощи обжарить 3 мин.", "Вбить яйца, жарить до готовности."]),
    ("Скрэмбл с зеленью", {"eggs": 2, "butter": 10, "spinach": 40, "green_onion": 10}, "international",
     ["Шпинат обжарить 1 мин.", "Влить взбитые яйца, помешивать до кремовой текстуры."]),
    ("Шакшука", {"eggs": 2, "tomato": 150, "bell_pepper": 60, "onion": 40, "olive_oil": 10, "paprika_placeholder": 0},
     "middle_eastern", ["Лук и перец обжарить, добавить помидоры, тушить 8 мин.", "Вбить яйца, готовить под крышкой 5 мин."]),
]
for name, ing, cuisine, steps in EGG_STYLES:
    ing = {k: v for k, v in ing.items() if not k.endswith("_placeholder")}
    add_dish("breakfast", name, ing, cuisine, "easy", 12, steps + ["Посолить, поперчить по вкусу."])

TOAST_STYLES = [
    ("Тост с авокадо", {"bread_wholegrain": 40, "avocado": 0.7, "lemon": 5}, "international",
     ["Хлеб поджарить.", "Авокадо размять с лимонным соком, намазать на тост."]),
    ("Тост с творожным сыром и лососем", {"bread_rye": 40, "cheese_cream": 30, "fish_trout": 40}, "international",
     ["Хлеб поджарить, намазать сыром.", "Сверху выложить рыбу."]),
    ("Тост с арахисовой пастой и бананом", {"bread_wholegrain": 40, "peanut_butter_nat": 20, "banana": 80},
     "american", ["Хлеб поджарить, намазать пастой.", "Сверху выложить нарезанный банан."]),
    ("Тост с яйцом-пашот", {"bread_wholegrain": 40, "eggs": 1, "avocado": 0.3}, "international",
     ["Сварить яйцо-пашот 3 мин в кипящей воде с уксусом.", "Выложить на тост с авокадо."]),
]
for name, ing, cuisine, steps in TOAST_STYLES:
    add_dish("breakfast", name, ing, cuisine, "easy", 8, steps)

BOWL_STYLES = [
    ("Творог с фруктами", "cottage_cheese", 150, [("banana", 100), ("honey", 10)], "russian"),
    ("Творог с ягодами и мёдом", "cottage_cheese", 150, [("berries", 80), ("honey", 10)], "russian"),
    ("Греческий йогурт с гранолой", "greek_yogurt", 150, [("oats_flakes", 30), ("honey", 10)], "mediterranean"),
    ("Йогурт с чиа и манго", "yogurt_natural", 150, [("chia_seeds", 15), ("mango", 80)], "international"),
    ("Творожная бабка с изюмом", "cottage_cheese", 150, [("raisins", 20), ("sour_cream", 20)], "russian"),
]
for name, base, base_amt, extras, cuisine in BOWL_STYLES:
    ing = {base: base_amt}
    for k, a in extras:
        ing[k] = a
    add_dish("breakfast", name, ing, cuisine, "easy", 5, [
        f"Смешать {name_ing(base)} с остальными ингредиентами.", "Подавать сразу.",
    ])

SMOOTHIE_STYLES = [
    ("Смузи банан-овсянка", {"banana": 100, "oats": 30, "milk_cow": 200, "peanut_butter": 15}, "american"),
    ("Смузи ягодный", {"berries": 100, "greek_yogurt": 100, "honey": 10}, "international"),
    ("Смузи зелёный", {"spinach": 40, "banana": 100, "milk_oat": 200}, "international"),
    ("Смузи протеиновый", {"protein_powder": 30, "milk_cow": 250, "banana": 80}, "american"),
    ("Смузи манго-кокос", {"mango": 120, "milk_coconut": 150, "honey": 10}, "asian"),
]
for name, ing, cuisine in SMOOTHIE_STYLES:
    add_dish("breakfast", name, ing, cuisine, "easy", 5, ["Все ингредиенты взбить в блендере до однородности."])

add_dish("breakfast", "Сырники со сметаной", {"cottage_cheese": 200, "eggs": 1, "flour_wheat": 30, "sour_cream": 30},
          "russian", "medium", 20, ["Творог смешать с яйцом и мукой.", "Сформировать сырники, обжарить по 3 мин с каждой стороны.", "Подавать со сметаной."])
add_dish("breakfast", "Блинчики на молоке", {"flour_wheat": 100, "milk_cow": 250, "eggs": 1, "butter": 10},
          "russian", "medium", 25, ["Смешать все ингредиенты в жидкое тесто.", "Жарить тонким слоем по 1 мин с каждой стороны."])
add_dish("breakfast", "Гранола домашняя с йогуртом", {"oats_flakes": 60, "honey": 15, "almonds": 15, "greek_yogurt": 100},
          "international", "easy", 10, ["Овсянку смешать с мёдом и орехами, запечь 15 мин при 180°C.", "Подавать с йогуртом."])
add_dish("breakfast", "Овсяноблин с бананом", {"oats": 40, "eggs": 1, "banana": 80, "milk_cow": 30},
          "international", "easy", 10, ["Смешать овсянку, яйцо и молоко в тесто.", "Жарить как блин 2-3 мин с каждой стороны, начинить бананом."])
add_dish("breakfast", "Яйца бенедикт", {"eggs": 2, "bread_ciabatta": 40, "butter": 10, "beef": 0},
          "french", "medium", 20, ["Хлеб поджарить.", "Сварить яйца-пашот.", "Выложить яйца на хлеб, полить растопленным маслом."])
for i, (n, ing) in enumerate([
    ("Овощной завтрак-буррито", {"bread_tortilla": 60, "eggs": 2, "bell_pepper": 50, "cheese_russian": 30}),
    ("Творожная запеканка", {"cottage_cheese": 200, "eggs": 1, "flour_wheat": 20, "raisins": 20}),
    ("Каша рисовая с тыквой", {"rice": 60, "pumpkin": 100, "milk_cow": 150, "honey": 10}),
    ("Мюсли с молоком и ягодами", {"oats_flakes": 60, "milk_cow": 150, "berries": 60, "walnuts": 10}),
]):
    add_dish("breakfast", n, ing, "international", "easy", 15, [
        "Подготовить все ингредиенты.", "Смешать/приготовить согласно составу.", "Подавать тёплым или холодным.",
    ])

# ================= ПЕРЕКУСЫ =================
SNACK_COMBOS = [
    ("Яблоко с арахисовой пастой", {"apple": 150, "peanut_butter_nat": 20}, "american"),
    ("Банан с миндалём", {"banana": 120, "almonds": 20}, "international"),
    ("Морковные палочки с хумусом", {"carrot": 150, "hummus": 50}, "middle_eastern"),
    ("Овощи с хумусом", {"cucumber": 80, "bell_pepper": 60, "celery": 40, "hummus": 60}, "middle_eastern"),
    ("Творог с огурцом", {"cottage_cheese": 150, "cucumber": 80, "dill": 5}, "russian"),
    ("Греческий йогурт с орехами", {"greek_yogurt": 150, "walnuts": 15, "honey": 15}, "mediterranean"),
    ("Сыр с виноградом", {"cheese_russian": 60, "grapes": 80}, "french"),
    ("Рисовые хлебцы с авокадо", {"crispbread": 30, "avocado": 0.4, "lemon": 5}, "international"),
    ("Творожный сыр на тосте с огурцом", {"bread_wholegrain": 40, "cheese_cream": 30, "cucumber": 50}, "international"),
    ("Йогурт с чиа и ягодами", {"yogurt_natural": 150, "chia_seeds": 15, "berries": 60}, "international"),
    ("Фруктовый салат", {"apple": 100, "banana": 80, "kiwi": 80, "orange": 80}, "international"),
    ("Сухофрукты с орехами", {"dried_apricots": 30, "raisins": 20, "walnuts": 20}, "international"),
    ("Энергетические шарики", {"oats": 60, "dates": 60, "peanut_butter": 20, "cocoa_powder": 10}, "international"),
    ("Кефир с корицей", {"kefir": 250, "cinnamon": 1}, "russian"),
    ("Тост с бананом и мёдом", {"bread_wholegrain": 40, "banana": 80, "honey": 10}, "international"),
    ("Творог с мёдом и семечками", {"cottage_cheese": 150, "honey": 10, "sunflower_seeds": 15}, "russian"),
    ("Яйцо варёное с хлебцем", {"eggs": 2, "crispbread": 20}, "international"),
    ("Сельдерей с ореховой пастой", {"celery": 100, "peanut_butter_nat": 25}, "american"),
    ("Смузи-боул с гранолой", {"berries": 100, "greek_yogurt": 100, "oats_flakes": 20}, "international"),
    ("Домашний протеиновый батончик", {"oats": 80, "protein_powder": 30, "honey": 20, "peanut_butter": 20}, "american"),
    ("Финики с миндалём", {"dates": 60, "almonds": 20}, "middle_eastern"),
    ("Хумус с питой", {"hummus": 80, "bread_pita": 40}, "middle_eastern"),
    ("Творожок с бананом и корицей", {"cottage_cheese": 150, "banana": 80, "cinnamon": 1}, "russian"),
    ("Ягодный кефирный коктейль", {"kefir": 200, "berries": 80, "honey": 10}, "russian"),
    ("Дольки апельсина с тёмным шоколадом", {"orange": 150, "dark_chocolate": 15}, "international"),
    ("Груша с творогом", {"pear": 120, "cottage_cheese": 120}, "russian"),
    ("Огурец с творожным сыром-ролл", {"cucumber": 100, "cheese_cream": 30, "bread_tortilla": 30}, "international"),
    ("Ассорти орехов", {"almonds": 15, "walnuts": 15, "cashews": 15}, "international"),
    ("Яблочные чипсы", {"apple": 200, "cinnamon": 1}, "international"),
    ("Ягоды с взбитым кокосовым кремом", {"berries": 100, "coconut_cream": 50}, "asian"),
    ("Гуакамоле с овощами", {"avocado": 1, "tomato": 60, "lime": 10, "carrot": 60}, "mexican"),
    ("Тунец на хлебце", {"tuna_canned": 60, "crispbread": 20, "cucumber": 30}, "international"),
    ("Творожно-банановый смузи", {"cottage_cheese": 100, "banana": 100, "milk_cow": 100}, "international"),
    ("Виноград с сыром фета", {"grapes": 100, "cheese_feta": 50}, "mediterranean"),
    ("Тыквенные семечки с курагой", {"pumpkin_seeds": 20, "dried_apricots": 30}, "international"),
    ("Ряженка с отрубями", {"ryazhenka": 200, "oats_flakes": 20}, "russian"),
]
for name, ing, cuisine in SNACK_COMBOS:
    add_dish("snack", name, ing, cuisine, "easy", 5, [
        f"Подготовить: {', '.join(name_ing(k) for k in ing)}.", "Смешать или выложить вместе, подавать сразу.",
    ])

# ================= ОБЕДЫ И УЖИНЫ =================
PROTEINS = [
    ("chicken", 180, "chicken"), ("chicken_thigh", 200, "chicken"), ("turkey", 180, "turkey"),
    ("beef", 180, "beef"), ("pork", 180, "pork"), ("fish_cod", 180, "fish"), ("fish_pollock", 180, "fish"),
    ("fish_pink_salmon", 160, "fish"), ("fish_trout", 150, "fish"), ("fish_mackerel", 170, "fish"),
    ("shrimp", 200, "seafood"), ("squid", 180, "seafood"), ("tofu", 180, "veg"), ("tempeh", 150, "veg"),
    ("chickpeas", 150, "veg"), ("lentils", 150, "veg"), ("beans_red", 150, "veg"), ("rabbit", 200, "meat"),
    ("turkey_mince", 180, "chicken"), ("beef_mince", 180, "beef"), ("chicken_mince", 180, "chicken"),
]
SIDES = [
    ("buckwheat", 70, "гречкой"), ("rice", 70, "рисом"), ("brown_rice", 70, "бурым рисом"),
    ("quinoa", 60, "киноа"), ("bulgur", 60, "булгуром"), ("potato", 200, "картофелем"),
    ("couscous", 60, "кускусом"), ("pasta", 80, "макаронами"),
]
VEGGIES = [
    ("broccoli", 100, "брокколи"), ("zucchini", 100, "кабачком"), ("bell_pepper", 80, "болгарским перцем"),
    ("cauliflower", 100, "цветной капустой"), ("green_peas", 80, "зелёным горошком"),
    ("eggplant", 100, "баклажаном"), ("asparagus", 100, "спаржей"), ("cabbage", 100, "капустой"),
    ("spinach", 60, "шпинатом"), ("tomato", 100, "помидорами"),
]
COOK_METHODS = [
    ("Запечённ{suffix}", "mediterranean", "easy", 30,
     lambda p, s: [f"{p.capitalize()} посолить, поперчить, выложить с овощами в форму.",
                   "Сбрызнуть оливковым маслом.", "Запекать 25-30 мин при 200°C."]),
    ("{Protein} на гриле с", "international", "easy", 25,
     lambda p, s: [f"{p.capitalize()} замариновать в масле со специями 10 мин.",
                   "Обжарить на гриле или сковороде-гриль по 5-7 мин с каждой стороны.",
                   "Подавать с гарниром."]),
    ("Тушён{suffix}", "russian", "medium", 40,
     lambda p, s: [f"{p.capitalize()} обжарить до корочки.", "Добавить овощи и немного воды, тушить 25 мин под крышкой."]),
    ("{Protein} стир-фрай с", "asian", "easy", 20,
     lambda p, s: [f"{p.capitalize()} нарезать кусочками, обжарить на сильном огне 5 мин.",
                   "Добавить овощи, жарить ещё 5 мин, влить соевый соус.", "Подавать сразу, пока горячее."]),
    ("{Protein} карри с", "asian", "medium", 35,
     lambda p, s: [f"{p.capitalize()} обжарить с луком и карри-пастой.",
                   "Добавить овощи и немного кокосового молока, тушить 20 мин.", "Подавать с рисом."]),
]

SUFFIX_BY_GROUP = {
    "fish": "ая рыба", "seafood": "ые морепродукты", "chicken": "ая курица", "turkey": "ая индейка",
    "beef": "ая говядина", "pork": "ая свинина", "meat": "ое мясо", "veg": "ое овощное блюдо",
}

count_lunch_dinner = 0
for protein_key, protein_amt, protein_group in PROTEINS:
    for i, (veg_key, veg_amt, veg_label) in enumerate(VEGGIES):
        method_idx = (hash(protein_key) + i) % len(COOK_METHODS)
        name_tpl, cuisine, difficulty, time, steps_fn = COOK_METHODS[method_idx]
        pname = name_ing(protein_key)
        if "{suffix}" in name_tpl:
            suffix = SUFFIX_BY_GROUP[protein_group]
            dish_name = f"{name_tpl.format(suffix=suffix)} с {veg_label}"
        else:
            dish_name = f"{name_tpl.format(Protein=name_ing_title(protein_key).capitalize())} {veg_label}"
        ing = {protein_key: protein_amt, veg_key: veg_amt, "olive_oil": 10, "garlic": 5}
        meal_type = "dinner" if (hash(dish_name) % 2 == 0) else "lunch"
        if meal_type == "lunch":
            side_key, side_amt, side_label = SIDES[hash(dish_name) % len(SIDES)]
            ing[side_key] = side_amt
            dish_name = f"{dish_name} и {side_label}"
        add_dish(meal_type, dish_name, ing, cuisine, difficulty, time, steps_fn(pname, veg_label))
        count_lunch_dinner += 1
        if count_lunch_dinner >= 90:
            break
    if count_lunch_dinner >= 90:
        break

SALADS = [
    ("Салат с курицей и авокадо", {"chicken": 150, "avocado": 0.5, "lettuce": 60, "tomato_cherry": 80, "olive_oil": 10}, "mediterranean"),
    ("Салат с тунцом", {"tuna_canned": 100, "cucumber": 80, "tomato": 80, "olives": 30, "olive_oil": 10}, "mediterranean"),
    ("Салат с нутом и фетой", {"chickpeas": 150, "cheese_feta": 60, "cucumber": 80, "olive_oil": 10}, "mediterranean"),
    ("Салат Цезарь с курицей", {"chicken": 150, "lettuce": 80, "cheese_russian": 30, "bread_ciabatta": 30}, "italian"),
    ("Салат с креветками и авокадо", {"shrimp": 150, "avocado": 0.7, "lettuce": 60, "lemon": 10}, "mediterranean"),
    ("Греческий салат", {"cucumber": 100, "tomato": 100, "cheese_feta": 60, "olives": 30, "olive_oil": 10}, "mediterranean"),
    ("Салат с тофу и киноа", {"tofu": 120, "quinoa": 50, "spinach": 50, "olive_oil": 10}, "asian"),
    ("Салат витаминный с капустой", {"cabbage": 150, "carrot": 60, "olive_oil": 10, "lemon": 10}, "russian"),
    ("Салат со свёклой и грецким орехом", {"beetroot": 150, "walnuts": 20, "cheese_feta": 40}, "russian"),
    ("Салат с индейкой и киноа", {"turkey": 150, "quinoa": 60, "bell_pepper": 60, "olive_oil": 10}, "international"),
]
for name, ing, cuisine in SALADS:
    add_dish("lunch", name, ing, cuisine, "easy", 15, ["Все ингредиенты нарезать.", "Смешать, заправить маслом и лимонным соком по вкусу."])

SOUPS = [
    ("Куриный суп с овощами", {"chicken": 150, "carrot": 60, "potato": 150, "onion": 40}, "russian"),
    ("Крем-суп из брокколи", {"broccoli": 250, "potato": 100, "milk_cow": 150, "butter": 10}, "international"),
    ("Чечевичный суп", {"lentils": 120, "carrot": 60, "onion": 40, "tomato_paste": 20}, "middle_eastern"),
    ("Тыквенный крем-суп", {"pumpkin": 300, "milk_cow": 150, "ginger_root": 5, "olive_oil": 10}, "international"),
    ("Борщ", {"beef": 150, "beetroot": 120, "cabbage": 100, "potato": 150, "tomato_paste": 20}, "russian"),
    ("Грибной суп", {"mushrooms": 200, "potato": 150, "sour_cream": 30, "onion": 40}, "russian"),
    ("Том-ям с креветками", {"shrimp": 150, "mushrooms": 100, "lime": 10, "chili": 3}, "asian"),
    ("Рыбный суп", {"fish_pollock": 200, "potato": 150, "carrot": 50, "onion": 40}, "russian"),
]
for name, ing, cuisine in SOUPS:
    add_dish("lunch", name, ing, cuisine, "medium", 40, [
        "Мясо/рыбу/овощи подготовить и нарезать.", "Сварить бульон или обжарить основу, добавить остальные овощи.",
        "Варить 20-30 мин до готовности, посолить по вкусу.",
    ])

PASTA_BOWLS = [
    ("Паста с курицей и томатным соусом", {"pasta": 90, "chicken": 150, "tomato_sauce": 100, "olive_oil": 10}, "italian"),
    ("Паста с тунцом", {"pasta": 90, "tuna_canned": 100, "olive_oil": 10, "garlic": 5}, "italian"),
    ("Паста с креветками", {"pasta": 90, "shrimp": 150, "garlic": 5, "olive_oil_extra": 15}, "italian"),
    ("Паста с грибами и сливками", {"pasta": 90, "mushrooms": 150, "sour_cream": 60, "onion": 30}, "italian"),
    ("Паста с овощами", {"pasta_wholegrain": 90, "zucchini": 80, "tomato": 100, "olive_oil": 10}, "italian"),
    ("Удон с курицей и овощами", {"noodles_udon": 100, "chicken": 150, "bell_pepper": 60, "soy_sauce": 15}, "asian"),
    ("Соба с овощами", {"noodles_soba": 90, "broccoli": 80, "carrot": 50, "soy_sauce": 15}, "asian"),
]
for name, ing, cuisine in PASTA_BOWLS:
    add_dish("lunch", name, ing, cuisine, "easy", 25, [
        "Отварить пасту/лапшу согласно инструкции.", "Приготовить остальные ингредиенты, смешать с пастой.",
    ])

WRAPS = [
    ("Буррито с курицей", {"bread_tortilla": 70, "chicken": 150, "beans_red": 80, "cheese_russian": 30}, "mexican"),
    ("Ролл с тунцом", {"bread_tortilla": 70, "tuna_canned": 100, "lettuce": 40, "mayo_light": 20}, "international"),
    ("Шаурма с курицей", {"bread_pita": 70, "chicken": 150, "cabbage": 60, "tomato": 60}, "middle_eastern"),
    ("Фалафель-ролл", {"bread_pita": 70, "chickpeas": 150, "hummus": 40, "cucumber": 50}, "middle_eastern"),
]
for name, ing, cuisine in WRAPS:
    add_dish("lunch", name, ing, cuisine, "easy", 20, [
        "Начинку подготовить и обжарить/отварить.", "Завернуть в лаваш/тортилью с овощами.",
    ])

STEWS = [
    ("Плов с курицей", {"chicken_thigh": 200, "rice": 80, "carrot": 60, "onion": 40}, "central_asian"),
    ("Гуляш из говядины", {"beef": 200, "bell_pepper": 60, "tomato_paste": 30, "onion": 50}, "hungarian"),
    ("Рагу из индейки с овощами", {"turkey": 180, "zucchini": 80, "eggplant": 80, "tomato": 100}, "mediterranean"),
    ("Чили кон карне", {"beef_mince": 180, "beans_red": 120, "tomato_paste": 30, "chili": 5}, "mexican"),
    ("Тажин с бараниной", {"lamb": 180, "dried_apricots": 30, "carrot": 60, "cumin": 3}, "middle_eastern"),
    ("Далл из чечевицы", {"lentils": 150, "tomato": 100, "ginger_root": 5, "curry": 5}, "asian"),
    ("Кролик, тушёный в сметане", {"rabbit": 200, "sour_cream": 60, "onion": 50, "carrot": 50}, "russian"),
    ("Свиные рёбрышки барбекю", {"pork_ribs": 250, "ketchup": 30, "honey": 15, "garlic": 5}, "american"),
]
for name, ing, cuisine in STEWS:
    add_dish("dinner", name, ing, cuisine, "medium", 50, [
        "Мясо обжарить до корочки.", "Добавить овощи и специи, тушить под крышкой 30-40 мин до готовности.",
    ])

BAKES = [
    ("Запеканка с курицей и брокколи", {"chicken": 180, "broccoli": 150, "cheese_russian": 40, "milk_cow": 60}, "international"),
    ("Овощная лазанья", {"pasta": 80, "zucchini": 100, "tomato_sauce": 100, "cheese_mozzarella": 60}, "italian"),
    ("Фаршированные перцы", {"bell_pepper": 200, "mixed_mince": 150, "rice": 50, "tomato_sauce": 80}, "russian"),
    ("Кабачки, фаршированные индейкой", {"zucchini": 300, "turkey_mince": 150, "tomato": 60, "cheese_russian": 30}, "russian"),
    ("Запечённая цветная капуста с сыром", {"cauliflower": 250, "cheese_russian": 60, "milk_cow": 50}, "international"),
]
for name, ing, cuisine in BAKES:
    add_dish("dinner", name, ing, cuisine, "medium", 45, [
        "Подготовить начинку/овощи.", "Выложить в форму слоями, посыпать сыром.", "Запекать 30-35 мин при 190°C.",
    ])

# ---------- Сборка и запись ----------
by_type = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
for meal_type, dish in DISHES:
    by_type[meal_type].append(dish)

total = sum(len(v) for v in by_type.values())
print("Итоговое количество блюд по категориям:")
for k, v in by_type.items():
    print(f"  {k}: {len(v)}")
print(f"  ВСЕГО: {total}")

used_keys = set()
for dishes in by_type.values():
    for d in dishes:
        used_keys |= set(d["ingredients"].keys())
print(f"Использовано уникальных ключей продуктов: {len(used_keys)}")

# Эти константы использует flask_app.py (клавиатуры/подписи) — они НЕ входят
# в генерируемые данные MEALS, но должны жить в том же файле. Если этот блок
# потеряется при регенерации, импорт flask_app.py упадёт сразу при старте.
STATIC_TAIL = '''

GOAL_LABELS = {
    "loss": "похудение",
    "gain": "набор массы",
    "maintain": "поддержание веса",
    "variety": "разнообразие в рационе",
}

RESTRICTION_LABELS = {
    "vegetarian": "Вегетарианство",
    "gluten_free": "Без глютена",
    "lactose_free": "Без лактозы",
    "no_nuts": "Без орехов",
    "no_seafood": "Без морепродуктов",
    "no_pork": "Без свинины",
    "no_beef": "Без говядины",
}

MEAL_TYPE_LABELS = {
    "breakfast": "MEAL_BREAKFAST_EMOJI Завтрак",
    "lunch": "MEAL_LUNCH_EMOJI Обед",
    "dinner": "MEAL_DINNER_EMOJI Ужин",
    "snack": "MEAL_SNACK_EMOJI Перекус",
}

BUDGET_PRESETS = {
    "economy": {"name": "BUDGET_ECONOMY_EMOJI Эконом", "limit": 4000, "hint": "до 4 000 РУБ_SIGN"},
    "medium":  {"name": "BUDGET_MEDIUM_EMOJI Средний", "limit": 5500, "hint": "до 5 500 РУБ_SIGN"},
    "comfort": {"name": "BUDGET_COMFORT_EMOJI Комфорт", "limit": 7000, "hint": "до 7 000 РУБ_SIGN"},
    "any":     {"name": "BUDGET_ANY_EMOJI Без ограничений", "limit": None, "hint": "не ограничен"},
}
'''
STATIC_TAIL = (STATIC_TAIL
               .replace("MEAL_BREAKFAST_EMOJI", "\U0001F305").replace("MEAL_LUNCH_EMOJI", "\U0001F957")
               .replace("MEAL_DINNER_EMOJI", "\U0001F37D").replace("MEAL_SNACK_EMOJI", "\U0001F34E")
               .replace("BUDGET_ECONOMY_EMOJI", "\U0001F4B0").replace("BUDGET_MEDIUM_EMOJI", "\U0001F6D2")
               .replace("BUDGET_COMFORT_EMOJI", "✨").replace("BUDGET_ANY_EMOJI", "♾")
               .replace("РУБ_SIGN", "₽"))

out_path = ROOT / "meals_data.py"
with out_path.open("w", encoding="utf-8") as f:
    f.write('"""\n')
    f.write("База блюд. Сгенерировано scripts/generate_meals.py — КБЖУ посчитаны\n")
    f.write("из реальных ингредиентов, у каждого блюда есть рецепт, кухня и теги.\n")
    f.write('"""\n\n')
    f.write("MEALS = ")
    f.write(json.dumps(by_type, ensure_ascii=False, indent=None))
    f.write("\n")
    f.write(STATIC_TAIL)

print(f"\nЗаписано в {out_path}")
