"""
Справочник продуктов: цены и фасовки.

ВАЖНО: цены здесь — ОРИЕНТИРОВОЧНЫЕ для средней полосы России (2026).
Рекомендуется обновлять раз в 2-3 месяца.

Формат записи:
    "ключ": {
        "name": "Как показывать в списке покупок",
        "unit": "g" | "ml" | "pcs",
        "pack": 400,                   # сколько в одной упаковке
        "pack_price": 49,              # сколько стоит упаковка, руб
        "category": "категория",       # для удобства навигации
    }
"""

PRODUCTS = {
    # ========== КРУПЫ, МАКАРОНЫ, ХЛЕБ ==========
    "oats":             {"name": "Овсяные хлопья",            "unit": "g",  "pack": 400,  "pack_price": 65,   "category": "крупы"},
    "oats_flakes":      {"name": "Овсяные хлопья быстрого приготовления", "unit": "g", "pack": 800, "pack_price": 110, "category": "крупы"},
    "buckwheat":        {"name": "Гречка",                    "unit": "g",  "pack": 800,  "pack_price": 95,   "category": "крупы"},
    "rice":             {"name": "Рис белый длиннозерный",    "unit": "g",  "pack": 800,  "pack_price": 105,  "category": "крупы"},
    "rice_arborio":     {"name": "Рис Арборио",               "unit": "g",  "pack": 500,  "pack_price": 180,  "category": "крупы"},
    "brown_rice":       {"name": "Рис бурый нешлифованный",   "unit": "g",  "pack": 500,  "pack_price": 125,  "category": "крупы"},
    "quinoa":           {"name": "Киноа",                     "unit": "g",  "pack": 300,  "pack_price": 240,  "category": "крупы"},
    "bulgur":           {"name": "Булгур",                    "unit": "g",  "pack": 500,  "pack_price": 85,   "category": "крупы"},
    "couscous":         {"name": "Кускус",                    "unit": "g",  "pack": 500,  "pack_price": 120,  "category": "крупы"},
    "millet":           {"name": "Пшено",                     "unit": "g",  "pack": 800,  "pack_price": 75,   "category": "крупы"},
    "pearl_barley":     {"name": "Перловая крупа",            "unit": "g",  "pack": 800,  "pack_price": 70,   "category": "крупы"},
    "wheat_berries":    {"name": "Полба / спельта",           "unit": "g",  "pack": 500,  "pack_price": 150,  "category": "крупы"},
    "pasta":            {"name": "Макароны из твердых сортов","unit": "g",  "pack": 450,  "pack_price": 75,   "category": "макароны"},
    "pasta_wholegrain": {"name": "Макароны цельнозерновые",   "unit": "g",  "pack": 400,  "pack_price": 95,   "category": "макароны"},
    "pasta_glutenfree": {"name": "Макароны без глютена",      "unit": "g",  "pack": 250,  "pack_price": 140,  "category": "макароны"},
    "noodles_egg":      {"name": "Лапша яичная",              "unit": "g",  "pack": 400,  "pack_price": 80,   "category": "макароны"},
    "noodles_rice":     {"name": "Рисовая лапша",             "unit": "g",  "pack": 200,  "pack_price": 110,  "category": "макароны"},
    "noodles_udon":     {"name": "Лапша удон",                "unit": "g",  "pack": 200,  "pack_price": 130,  "category": "макароны"},
    "noodles_soba":     {"name": "Лапша соба (гречневая)",    "unit": "g",  "pack": 300,  "pack_price": 140,  "category": "макароны"},
    "bread_white":      {"name": "Хлеб белый",                "unit": "g",  "pack": 400,  "pack_price": 45,   "category": "хлеб"},
    "bread_rye":        {"name": "Хлеб ржаной / бородинский", "unit": "g",  "pack": 400,  "pack_price": 50,   "category": "хлеб"},
    "bread_wholegrain": {"name": "Хлеб цельнозерновой",       "unit": "g",  "pack": 350,  "pack_price": 65,   "category": "хлеб"},
    "bread_ciabatta":   {"name": "Чиабатта",                  "unit": "g",  "pack": 250,  "pack_price": 85,   "category": "хлеб"},
    "bread_baguette":   {"name": "Багет",                     "unit": "g",  "pack": 250,  "pack_price": 75,   "category": "хлеб"},
    "bread_pita":       {"name": "Пита / лаваш",              "unit": "g",  "pack": 300,  "pack_price": 55,   "category": "хлеб"},
    "bread_tortilla":   {"name": "Тортилья пшеничная",        "unit": "g",  "pack": 320,  "pack_price": 95,   "category": "хлеб"},
    "bread_tortilla_corn": {"name": "Тортилья кукурузная",    "unit": "g",  "pack": 240,  "pack_price": 110,  "category": "хлеб"},
    "crispbread":       {"name": "Хлебцы",                    "unit": "g",  "pack": 100,  "pack_price": 55,   "category": "хлеб"},
    "flour_wheat":      {"name": "Мука пшеничная",            "unit": "g",  "pack": 1000, "pack_price": 85,   "category": "мука"},
    "flour_wholegrain": {"name": "Мука цельнозерновая",       "unit": "g",  "pack": 1000, "pack_price": 110,  "category": "мука"},

    # ========== МЯСО, ПТИЦА, ЯЙЦА ==========
    "chicken":          {"name": "Куриное филе",              "unit": "g",  "pack": 1000, "pack_price": 380,  "category": "птица"},
    "chicken_thigh":    {"name": "Куриные бёдра",             "unit": "g",  "pack": 1000, "pack_price": 320,  "category": "птица"},
    "chicken_wings":    {"name": "Куриные крылышки",          "unit": "g",  "pack": 1000, "pack_price": 290,  "category": "птица"},
    "turkey":           {"name": "Филе индейки",              "unit": "g",  "pack": 800,  "pack_price": 450,  "category": "птица"},
    "turkey_mince":     {"name": "Фарш из индейки",           "unit": "g",  "pack": 500,  "pack_price": 280,  "category": "птица"},
    "chicken_mince":    {"name": "Фарш куриный",              "unit": "g",  "pack": 500,  "pack_price": 220,  "category": "птица"},
    "beef":             {"name": "Говядина (вырезка)",        "unit": "g",  "pack": 800,  "pack_price": 640,  "category": "мясо"},
    "beef_mince":       {"name": "Фарш говяжий",              "unit": "g",  "pack": 500,  "pack_price": 380,  "category": "мясо"},
    "pork":             {"name": "Свинина (корейка/вырезка)", "unit": "g",  "pack": 800,  "pack_price": 480,  "category": "мясо"},
    "pork_mince":       {"name": "Фарш свиной",               "unit": "g",  "pack": 500,  "pack_price": 260,  "category": "мясо"},
    "pork_ribs":        {"name": "Свиные рёбрышки",           "unit": "g",  "pack": 800,  "pack_price": 420,  "category": "мясо"},
    "mixed_mince":      {"name": "Фарш мясной смешанный",     "unit": "g",  "pack": 500,  "pack_price": 290,  "category": "мясо"},
    "veal":             {"name": "Телятина",                  "unit": "g",  "pack": 600,  "pack_price": 720,  "category": "мясо"},
    "lamb":             {"name": "Баранина",                  "unit": "g",  "pack": 600,  "pack_price": 680,  "category": "мясо"},
    "rabbit":           {"name": "Кролик",                    "unit": "g",  "pack": 800,  "pack_price": 550,  "category": "мясо"},
    "beef_liver":       {"name": "Печень говяжья",            "unit": "g",  "pack": 500,  "pack_price": 260,  "category": "мясо"},
    "eggs":             {"name": "Яйца куриные",              "unit": "pcs","pack": 10,   "pack_price": 110,  "category": "яйца"},
    "eggs_quail":       {"name": "Яйца перепелиные",          "unit": "pcs","pack": 20,   "pack_price": 140,  "category": "яйца"},

    # ========== РЫБА, МОРЕПРОДУКТЫ ==========
    "fish_pollock":     {"name": "Рыба минтай",               "unit": "g",  "pack": 700,  "pack_price": 280,  "category": "рыба"},
    "fish_cod":         {"name": "Рыба треска",               "unit": "g",  "pack": 700,  "pack_price": 320,  "category": "рыба"},
    "fish_pink_salmon": {"name": "Рыба горбуша",              "unit": "g",  "pack": 700,  "pack_price": 350,  "category": "рыба"},
    "fish_mackerel":    {"name": "Рыба скумбрия",             "unit": "g",  "pack": 500,  "pack_price": 220,  "category": "рыба"},
    "fish_trout":       {"name": "Форель / семга",            "unit": "g",  "pack": 400,  "pack_price": 480,  "category": "рыба"},
    "fish_sardine":     {"name": "Сардина консервированная",  "unit": "g",  "pack": 240,  "pack_price": 95,   "category": "рыба"},
    "tuna_canned":      {"name": "Тунец консервированный",    "unit": "g",  "pack": 185,  "pack_price": 140,  "category": "рыба"},
    "shrimp":           {"name": "Креветки очищенные",        "unit": "g",  "pack": 400,  "pack_price": 450,  "category": "морепродукты"},
    "squid":            {"name": "Кальмары",                  "unit": "g",  "pack": 400,  "pack_price": 320,  "category": "морепродукты"},
    "mussels":          {"name": "Мидии",                     "unit": "g",  "pack": 450,  "pack_price": 380,  "category": "морепродукты"},

    # ========== МОЛОЧНОЕ ==========
    "milk_cow":         {"name": "Молоко коровье 3,2%",       "unit": "ml", "pack": 1000, "pack_price": 85,   "category": "молочное"},
    "milk_1pct":        {"name": "Молоко 1%",                 "unit": "ml", "pack": 1000, "pack_price": 80,   "category": "молочное"},
    "kefir":            {"name": "Кефир 2,5%",                "unit": "ml", "pack": 1000, "pack_price": 90,   "category": "молочное"},
    "ryazhenka":        {"name": "Ряженка",                   "unit": "ml", "pack": 500,  "pack_price": 65,   "category": "молочное"},
    "cottage_cheese":   {"name": "Творог 5%",                 "unit": "g",  "pack": 350,  "pack_price": 130,  "category": "молочное"},
    "cottage_cheese_2": {"name": "Творог обезжиренный 2%",    "unit": "g",  "pack": 350,  "pack_price": 120,  "category": "молочное"},
    "greek_yogurt":     {"name": "Греческий йогурт",          "unit": "g",  "pack": 500,  "pack_price": 180,  "category": "молочное"},
    "yogurt_natural":   {"name": "Йогурт натуральный",        "unit": "g",  "pack": 400,  "pack_price": 95,   "category": "молочное"},
    "sour_cream":       {"name": "Сметана 15%",               "unit": "g",  "pack": 300,  "pack_price": 85,   "category": "молочное"},
    "sour_cream_20":    {"name": "Сметана 20%",               "unit": "g",  "pack": 300,  "pack_price": 95,   "category": "молочное"},
    "cheese_russian":   {"name": "Сыр твёрдый (Российский)",  "unit": "g",  "pack": 200,  "pack_price": 180,  "category": "молочное"},
    "cheese_mozzarella":{"name": "Сыр моцарелла",             "unit": "g",  "pack": 250,  "pack_price": 220,  "category": "молочное"},
    "cheese_feta":      {"name": "Сыр фета / брынза",         "unit": "g",  "pack": 250,  "pack_price": 190,  "category": "молочное"},
    "cheese_cottage":   {"name": "Творожный сыр",             "unit": "g",  "pack": 200,  "pack_price": 140,  "category": "молочное"},
    "cheese_cream":     {"name": "Сливочный сыр",             "unit": "g",  "pack": 200,  "pack_price": 160,  "category": "молочное"},
    "butter":           {"name": "Масло сливочное",           "unit": "g",  "pack": 200,  "pack_price": 180,  "category": "молочное"},

    # ========== РАСТИТЕЛЬНОЕ МОЛОКО ==========
    "plant_milk":       {"name": "Растительное молоко",       "unit": "ml", "pack": 1000, "pack_price": 140,  "category": "раст_молоко"},
    "milk_soy":         {"name": "Соевое молоко",             "unit": "ml", "pack": 1000, "pack_price": 130,  "category": "раст_молоко"},
    "milk_oat":         {"name": "Овсяное молоко",            "unit": "ml", "pack": 1000, "pack_price": 150,  "category": "раст_молоко"},
    "milk_almond":      {"name": "Миндальное молоко",         "unit": "ml", "pack": 1000, "pack_price": 220,  "category": "раст_молоко"},
    "milk_coconut":     {"name": "Кокосовое молоко",          "unit": "ml", "pack": 400,  "pack_price": 180,  "category": "раст_молоко"},

    # ========== ОВОЩИ, ЗЕЛЕНЬ ==========
    "tomato":           {"name": "Помидоры",                  "unit": "g",  "pack": 1000, "pack_price": 190,  "category": "овощи"},
    "tomato_cherry":    {"name": "Помидоры черри",            "unit": "g",  "pack": 500,  "pack_price": 160,  "category": "овощи"},
    "cucumber":         {"name": "Огурцы",                    "unit": "g",  "pack": 1000, "pack_price": 180,  "category": "овощи"},
    "bell_pepper":      {"name": "Перец болгарский",          "unit": "g",  "pack": 500,  "pack_price": 140,  "category": "овощи"},
    "eggplant":         {"name": "Баклажаны",                 "unit": "g",  "pack": 1000, "pack_price": 150,  "category": "овощи"},
    "zucchini":         {"name": "Кабачки",                   "unit": "g",  "pack": 1000, "pack_price": 120,  "category": "овощи"},
    "pumpkin":          {"name": "Тыква",                     "unit": "g",  "pack": 2000, "pack_price": 110,  "category": "овощи"},
    "beetroot":         {"name": "Свёкла",                    "unit": "g",  "pack": 1000, "pack_price": 55,   "category": "овощи"},
    "carrot":           {"name": "Морковь",                   "unit": "g",  "pack": 1000, "pack_price": 55,   "category": "овощи"},
    "onion":            {"name": "Лук репчатый",              "unit": "g",  "pack": 1000, "pack_price": 50,   "category": "овощи"},
    "garlic":           {"name": "Чеснок",                    "unit": "g",  "pack": 200,  "pack_price": 45,   "category": "овощи"},
    "potato":           {"name": "Картофель",                 "unit": "g",  "pack": 1000, "pack_price": 60,   "category": "овощи"},
    "cabbage":          {"name": "Капуста белокочанная",      "unit": "g",  "pack": 1000, "pack_price": 55,   "category": "овощи"},
    "cabbage_red":      {"name": "Капуста краснокочанная",    "unit": "g",  "pack": 800,  "pack_price": 85,   "category": "овощи"},
    "broccoli":         {"name": "Брокколи",                  "unit": "g",  "pack": 400,  "pack_price": 175,  "category": "овощи"},
    "cauliflower":      {"name": "Цветная капуста",           "unit": "g",  "pack": 600,  "pack_price": 130,  "category": "овощи"},
    "asparagus":        {"name": "Спаржа",                    "unit": "g",  "pack": 300,  "pack_price": 260,  "category": "овощи"},
    "spinach":          {"name": "Шпинат свежий",             "unit": "g",  "pack": 200,  "pack_price": 130,  "category": "зелень"},
    "lettuce":          {"name": "Салат листовой",            "unit": "g",  "pack": 150,  "pack_price": 110,  "category": "зелень"},
    "arugula":          {"name": "Руккола",                   "unit": "g",  "pack": 100,  "pack_price": 120,  "category": "зелень"},
    "parsley":          {"name": "Петрушка",                  "unit": "g",  "pack": 100,  "pack_price": 45,   "category": "зелень"},
    "dill":             {"name": "Укроп",                     "unit": "g",  "pack": 100,  "pack_price": 45,   "category": "зелень"},
    "cilantro":         {"name": "Кинза / кориандр",          "unit": "g",  "pack": 50,   "pack_price": 55,   "category": "зелень"},
    "basil_fresh":      {"name": "Базилик свежий",            "unit": "g",  "pack": 50,   "pack_price": 65,   "category": "зелень"},
    "mint":             {"name": "Мята свежая",                "unit": "g",  "pack": 30,   "pack_price": 55,   "category": "зелень"},
    "green_onion":      {"name": "Лук зелёный",               "unit": "g",  "pack": 100,  "pack_price": 55,   "category": "зелень"},
    "celery":           {"name": "Сельдерей черешковый",      "unit": "g",  "pack": 400,  "pack_price": 95,   "category": "овощи"},
    "radish":           {"name": "Редис",                     "unit": "g",  "pack": 300,  "pack_price": 65,   "category": "овощи"},
    "corn":             {"name": "Кукуруза консервированная", "unit": "g",  "pack": 340,  "pack_price": 75,   "category": "консервы"},
    "green_peas":       {"name": "Зелёный горошек консервированный", "unit": "g", "pack": 400, "pack_price": 65, "category": "консервы"},
    "beans_canned":     {"name": "Фасоль консервированная",   "unit": "g",  "pack": 400,  "pack_price": 75,   "category": "консервы"},
    "olives":           {"name": "Маслины / оливки",          "unit": "g",  "pack": 300,  "pack_price": 120,  "category": "консервы"},
    "capers":           {"name": "Каперсы",                   "unit": "g",  "pack": 100,  "pack_price": 140,  "category": "консервы"},
    "mushrooms":        {"name": "Шампиньоны свежие",         "unit": "g",  "pack": 400,  "pack_price": 150,  "category": "грибы"},
    "mushrooms_oyster": {"name": "Вёшенки",                   "unit": "g",  "pack": 400,  "pack_price": 130,  "category": "грибы"},
    "mushrooms_dried":  {"name": "Грибы сушёные",             "unit": "g",  "pack": 50,   "pack_price": 180,  "category": "грибы"},
    "ginger_root":      {"name": "Имбирь корень",             "unit": "g",  "pack": 200,  "pack_price": 85,   "category": "овощи"},
    "chili":            {"name": "Перец чили",                "unit": "g",  "pack": 50,   "pack_price": 80,   "category": "овощи"},
    "avocado":          {"name": "Авокадо",                   "unit": "pcs","pack": 1,    "pack_price": 140,  "category": "овощи"},

    # ========== ФРУКТЫ, ЯГОДЫ ==========
    "banana":           {"name": "Бананы",                    "unit": "g",  "pack": 1000, "pack_price": 130,  "category": "фрукты"},
    "apple":            {"name": "Яблоки",                    "unit": "g",  "pack": 1000, "pack_price": 140,  "category": "фрукты"},
    "pear":             {"name": "Груши",                     "unit": "g",  "pack": 1000, "pack_price": 160,  "category": "фрукты"},
    "orange":           {"name": "Апельсины",                 "unit": "g",  "pack": 1000, "pack_price": 150,  "category": "фрукты"},
    "mandarin":         {"name": "Мандарины",                 "unit": "g",  "pack": 1000, "pack_price": 140,  "category": "фрукты"},
    "lemon":            {"name": "Лимоны",                    "unit": "g",  "pack": 500,  "pack_price": 110,  "category": "фрукты"},
    "lime":             {"name": "Лайм",                      "unit": "g",  "pack": 250,  "pack_price": 130,  "category": "фрукты"},
    "kiwi":             {"name": "Киви",                      "unit": "g",  "pack": 500,  "pack_price": 120,  "category": "фрукты"},
    "pineapple":        {"name": "Ананас",                    "unit": "g",  "pack": 1500, "pack_price": 220,  "category": "фрукты"},
    "mango":            {"name": "Манго",                     "unit": "g",  "pack": 500,  "pack_price": 180,  "category": "фрукты"},
    "grapes":           {"name": "Виноград",                  "unit": "g",  "pack": 500,  "pack_price": 170,  "category": "фрукты"},
    "peach":            {"name": "Персики / нектарины",       "unit": "g",  "pack": 1000, "pack_price": 190,  "category": "фрукты"},
    "plum":             {"name": "Сливы",                     "unit": "g",  "pack": 1000, "pack_price": 150,  "category": "фрукты"},
    "watermelon":       {"name": "Арбуз",                     "unit": "g",  "pack": 5000, "pack_price": 250,  "category": "фрукты"},
    "melon":            {"name": "Дыня",                      "unit": "g",  "pack": 3000, "pack_price": 180,  "category": "фрукты"},
    "berries":          {"name": "Ягоды замороженные (смесь)","unit": "g",  "pack": 300,  "pack_price": 210,  "category": "ягоды"},
    "strawberry":       {"name": "Клубника",                  "unit": "g",  "pack": 300,  "pack_price": 280,  "category": "ягоды"},
    "blueberry":        {"name": "Голубика",                  "unit": "g",  "pack": 150,  "pack_price": 320,  "category": "ягоды"},
    "cranberry":        {"name": "Клюква",                    "unit": "g",  "pack": 200,  "pack_price": 180,  "category": "ягоды"},
    "pomegranate":      {"name": "Гранат",                    "unit": "g",  "pack": 500,  "pack_price": 160,  "category": "фрукты"},

    # ========== БОБОВЫЕ, РАСТИТЕЛЬНЫЙ БЕЛОК ==========
    "lentils":          {"name": "Чечевица",                  "unit": "g",  "pack": 450,  "pack_price": 115,  "category": "бобовые"},
    "chickpeas":        {"name": "Нут",                       "unit": "g",  "pack": 450,  "pack_price": 125,  "category": "бобовые"},
    "tofu":             {"name": "Тофу",                      "unit": "g",  "pack": 300,  "pack_price": 210,  "category": "раст_белок"},
    "tempeh":           {"name": "Темпе",                     "unit": "g",  "pack": 250,  "pack_price": 280,  "category": "раст_белок"},
    "seitan":           {"name": "Сейтан",                    "unit": "g",  "pack": 300,  "pack_price": 250,  "category": "раст_белок"},
    "beans_white":      {"name": "Фасоль белая",              "unit": "g",  "pack": 450,  "pack_price": 110,  "category": "бобовые"},
    "beans_red":        {"name": "Фасоль красная",            "unit": "g",  "pack": 450,  "pack_price": 115,  "category": "бобовые"},
    "peas_dried":       {"name": "Горох колотый",             "unit": "g",  "pack": 800,  "pack_price": 75,   "category": "бобовые"},
    "mung_beans":       {"name": "Маш",                       "unit": "g",  "pack": 400,  "pack_price": 130,  "category": "бобовые"},

    # ========== ОРЕХИ, СЕМЕЧКИ, СУХОФРУКТЫ ==========
    "walnuts":          {"name": "Грецкие орехи",             "unit": "g",  "pack": 150,  "pack_price": 250,  "category": "орехи"},
    "almonds":          {"name": "Миндаль",                   "unit": "g",  "pack": 150,  "pack_price": 320,  "category": "орехи"},
    "cashews":          {"name": "Кешью",                     "unit": "g",  "pack": 150,  "pack_price": 340,  "category": "орехи"},
    "pistachios":       {"name": "Фисташки",                  "unit": "g",  "pack": 100,  "pack_price": 380,  "category": "орехи"},
    "pine_nuts":        {"name": "Кедровые орехи",            "unit": "g",  "pack": 100,  "pack_price": 450,  "category": "орехи"},
    "sunflower_seeds":  {"name": "Семечки подсолнечника",     "unit": "g",  "pack": 200,  "pack_price": 75,   "category": "семена"},
    "pumpkin_seeds":    {"name": "Тыквенные семечки",         "unit": "g",  "pack": 200,  "pack_price": 110,  "category": "семена"},
    "chia_seeds":       {"name": "Семена чиа",                "unit": "g",  "pack": 200,  "pack_price": 220,  "category": "семена"},
    "flax_seeds":       {"name": "Семена льна",               "unit": "g",  "pack": 200,  "pack_price": 65,   "category": "семена"},
    "sesame_seeds":     {"name": "Кунжут",                    "unit": "g",  "pack": 150,  "pack_price": 95,   "category": "семена"},
    "nuts_mix":         {"name": "Орехи и сухофрукты (смесь)","unit": "g",  "pack": 200,  "pack_price": 260,  "category": "орехи"},
    "raisins":          {"name": "Изюм",                      "unit": "g",  "pack": 200,  "pack_price": 85,   "category": "сухофрукты"},
    "dried_apricots":   {"name": "Курага",                    "unit": "g",  "pack": 200,  "pack_price": 110,  "category": "сухофрукты"},
    "prunes":           {"name": "Чернослив",                 "unit": "g",  "pack": 200,  "pack_price": 120,  "category": "сухофрукты"},
    "dates":            {"name": "Финики",                    "unit": "g",  "pack": 300,  "pack_price": 180,  "category": "сухофрукты"},
    "dried_figs":       {"name": "Инжир сушёный",             "unit": "g",  "pack": 200,  "pack_price": 220,  "category": "сухофрукты"},

    # ========== МАСЛА ==========
    "olive_oil":        {"name": "Масло оливковое",           "unit": "ml", "pack": 800,  "pack_price": 480,  "category": "масла"},
    "olive_oil_extra":  {"name": "Масло оливковое Extra Virgin","unit":"ml","pack": 500,  "pack_price": 420,  "category": "масла"},
    "sunflower_oil":    {"name": "Масло подсолнечное",        "unit": "ml", "pack": 1000, "pack_price": 120,  "category": "масла"},
    "coconut_oil":      {"name": "Масло кокосовое",           "unit": "ml", "pack": 500,  "pack_price": 280,  "category": "масла"},
    "flax_oil":         {"name": "Масло льняное",             "unit": "ml", "pack": 250,  "pack_price": 180,  "category": "масла"},
    "sesame_oil":       {"name": "Масло кунжутное",           "unit": "ml", "pack": 250,  "pack_price": 220,  "category": "масла"},

    # ========== СОУСЫ, ПРИПРАВЫ ==========
    "tomato_sauce":     {"name": "Томатный соус",             "unit": "g",  "pack": 350,  "pack_price": 95,   "category": "соусы"},
    "tomato_paste":     {"name": "Томатная паста",            "unit": "g",  "pack": 140,  "pack_price": 55,   "category": "соусы"},
    "soy_sauce":        {"name": "Соевый соус",               "unit": "ml", "pack": 250,  "pack_price": 95,   "category": "соусы"},
    "soy_sauce_tamari": {"name": "Соевый соус тамари (б/г)", "unit": "ml",  "pack": 250,  "pack_price": 140,  "category": "соусы"},
    "balsamic_vinegar": {"name": "Бальзамический уксус",      "unit": "ml", "pack": 250,  "pack_price": 180,  "category": "соусы"},
    "apple_vinegar":    {"name": "Уксус яблочный",            "unit": "ml", "pack": 250,  "pack_price": 75,   "category": "соусы"},
    "mustard":          {"name": "Горчица",                   "unit": "g",  "pack": 140,  "pack_price": 45,   "category": "соусы"},
    "horseradish":      {"name": "Хрен",                      "unit": "g",  "pack": 140,  "pack_price": 55,   "category": "соусы"},
    "adjika":           {"name": "Аджика",                    "unit": "g",  "pack": 200,  "pack_price": 85,   "category": "соусы"},
    "tkemali":          {"name": "Ткемали",                   "unit": "g",  "pack": 300,  "pack_price": 95,   "category": "соусы"},
    "mayo_light":       {"name": "Майонез лёгкий",            "unit": "g",  "pack": 400,  "pack_price": 85,   "category": "соусы"},
    "ketchup":          {"name": "Кетчуп",                    "unit": "g",  "pack": 350,  "pack_price": 75,   "category": "соусы"},
    "pesto":            {"name": "Соус песто",                "unit": "g",  "pack": 190,  "pack_price": 220,  "category": "соусы"},
    "hummus":           {"name": "Хумус",                     "unit": "g",  "pack": 200,  "pack_price": 160,  "category": "соусы"},
    "tahini":           {"name": "Тахини (кунжутная паста)",  "unit": "g",  "pack": 300,  "pack_price": 280,  "category": "соусы"},
    "peanut_butter":    {"name": "Арахисовая паста",          "unit": "g",  "pack": 300,  "pack_price": 240,  "category": "соусы"},
    "peanut_butter_nat":{"name": "Арахисовая паста натуральная","unit":"g", "pack": 340,  "pack_price": 260,  "category": "соусы"},
    "sriracha":         {"name": "Соус шрирача",              "unit": "ml", "pack": 200,  "pack_price": 180,  "category": "соусы"},

    # ========== СПЕЦИИ (мелкая фасовка, цена за упаковку) ==========
    "salt":             {"name": "Соль",                      "unit": "g",  "pack": 1000, "pack_price": 35,   "category": "специи"},
    "black_pepper":     {"name": "Перец чёрный молотый",      "unit": "g",  "pack": 50,   "pack_price": 45,   "category": "специи"},
    "paprika":          {"name": "Паприка молотая",           "unit": "g",  "pack": 50,   "pack_price": 55,   "category": "специи"},
    "turmeric":         {"name": "Куркума",                   "unit": "g",  "pack": 40,   "pack_price": 65,   "category": "специи"},
    "cumin":            {"name": "Кумин (зира)",              "unit": "g",  "pack": 40,   "pack_price": 70,   "category": "специи"},
    "coriander_ground": {"name": "Кориандр молотый",          "unit": "g",  "pack": 40,   "pack_price": 45,   "category": "специи"},
    "oregano":          {"name": "Орегано",                   "unit": "g",  "pack": 20,   "pack_price": 55,   "category": "специи"},
    "thyme":            {"name": "Тимьян",                    "unit": "g",  "pack": 20,   "pack_price": 60,   "category": "специи"},
    "rosemary":         {"name": "Розмарин",                  "unit": "g",  "pack": 20,   "pack_price": 65,   "category": "специи"},
    "ginger_ground":    {"name": "Имбирь молотый",            "unit": "g",  "pack": 30,   "pack_price": 55,   "category": "специи"},
    "cinnamon":         {"name": "Корица молотая",            "unit": "g",  "pack": 30,   "pack_price": 50,   "category": "специи"},
    "nutmeg":           {"name": "Мускатный орех",            "unit": "g",  "pack": 20,   "pack_price": 70,   "category": "специи"},
    "curry":            {"name": "Карри",                     "unit": "g",  "pack": 40,   "pack_price": 60,   "category": "специи"},
    "khmeli_suneli":    {"name": "Хмели-сунели",              "unit": "g",  "pack": 30,   "pack_price": 55,   "category": "специи"},
    "garlic_powder":    {"name": "Чеснок сушёный",            "unit": "g",  "pack": 40,   "pack_price": 45,   "category": "специи"},
    "onion_powder":     {"name": "Лук сушёный",               "unit": "g",  "pack": 40,   "pack_price": 45,   "category": "специи"},
    "red_pepper_flakes":{"name": "Хлопья красного перца",     "unit": "g",  "pack": 30,   "pack_price": 50,   "category": "специи"},
    "zaatar":           {"name": "Заатар",                    "unit": "g",  "pack": 40,   "pack_price": 120,  "category": "специи"},
    "dried_basil":      {"name": "Базилик сушёный",           "unit": "g",  "pack": 20,   "pack_price": 50,   "category": "специи"},

    # ========== СЛАДОСТИ, ДЕСЕРТЫ ==========
    "honey":            {"name": "Мёд",                       "unit": "g",  "pack": 250,  "pack_price": 260,  "category": "сладости"},
    "maple_syrup":      {"name": "Кленовый сироп",            "unit": "ml", "pack": 250,  "pack_price": 320,  "category": "сладости"},
    "cocoa_powder":     {"name": "Какао-порошок",             "unit": "g",  "pack": 100,  "pack_price": 95,   "category": "сладости"},
    "dark_chocolate":   {"name": "Шоколад тёмный 70%",        "unit": "g",  "pack": 90,   "pack_price": 110,  "category": "сладости"},
    "vanilla":          {"name": "Ванилин / ванильный сахар", "unit": "g",  "pack": 10,   "pack_price": 35,   "category": "сладости"},
    "gelatin":          {"name": "Желатин",                   "unit": "g",  "pack": 50,   "pack_price": 55,   "category": "сладости"},
    "coconut_flakes":   {"name": "Кокосовая стружка",         "unit": "g",  "pack": 100,  "pack_price": 85,   "category": "сладости"},
    "sugar":            {"name": "Сахар",                     "unit": "g",  "pack": 1000, "pack_price": 75,   "category": "сладости"},
    "brown_sugar":      {"name": "Сахар коричневый",          "unit": "g",  "pack": 500,  "pack_price": 95,   "category": "сладости"},
    "stevia":           {"name": "Стевия (заменитель)",       "unit": "g",  "pack": 50,   "pack_price": 120,  "category": "сладости"},

    # ========== СПОРТПИТ ==========
    "protein_powder":   {"name": "Протеин сывороточный",      "unit": "g",  "pack": 900,  "pack_price": 2400, "category": "спортпит"},

    # ========== НАПИТКИ, ПРОЧЕЕ ==========
    "coffee":           {"name": "Кофе молотый",              "unit": "g",  "pack": 250,  "pack_price": 280,  "category": "напитки"},
    "coffee_instant":   {"name": "Кофе растворимый",          "unit": "g",  "pack": 95,   "pack_price": 220,  "category": "напитки"},
    "tea_black":        {"name": "Чай чёрный",                "unit": "g",  "pack": 100,  "pack_price": 85,   "category": "напитки"},
    "tea_green":        {"name": "Чай зелёный",               "unit": "g",  "pack": 100,  "pack_price": 95,   "category": "напитки"},
    "coconut_cream":    {"name": "Кокосовые сливки",          "unit": "ml", "pack": 400,  "pack_price": 220,  "category": "раст_молоко"},
    "yeast":            {"name": "Дрожжи сухие",              "unit": "g",  "pack": 100,  "pack_price": 45,   "category": "прочее"},
    "baking_powder":    {"name": "Разрыхлитель",              "unit": "g",  "pack": 50,   "pack_price": 40,   "category": "прочее"},
    "soda":             {"name": "Сода пищевая",              "unit": "g",  "pack": 100,  "pack_price": 30,   "category": "прочее"},
}


# ========== Региональные коэффициенты ==========
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


def products_by_category() -> dict:
    """Группировка продуктов по категориям."""
    result: dict[str, list] = {}
    for key, p in PRODUCTS.items():
        cat = p.get("category", "прочее")
        result.setdefault(cat, []).append((key, p))
    return result
