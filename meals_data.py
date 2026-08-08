"""
База блюд.

У каждого блюда:
    name        — название
    goals       — для каких целей подходит: loss / gain / maintain / variety
    tags        — какие ограничения соблюдает: vegetarian / gluten_free / lactose_free
    ingredients — продукты на ОДНУ порцию: {ключ_продукта: количество}
                  Ключи берутся из products.py, количество в тех же единицах
                  (г / мл / шт), что указаны там в поле "unit".

Чтобы добавить блюдо — скопируй любую запись и поправь. Бот подхватит его сам.
"""

MEALS = {
    "breakfast": [
        {
            "name": "Гречневая каша с яблоком и орехами",
            "goals": ['loss', 'gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"buckwheat": 70, "apple": 120, "walnuts": 15},
        },
        {
            "name": "Рисовая каша на растительном молоке",
            "goals": ['gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"rice": 80, "plant_milk": 200, "banana": 100},
        },
        {
            "name": "Омлет с авокадо и помидорами",
            "goals": ['loss', 'gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"eggs": 2, "avocado": 0.5, "tomato": 80, "olive_oil": 5},
        },
        {
            "name": "Овсянка с бананом и грецкими орехами",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "lactose_free"],
            "ingredients": {"oats": 60, "banana": 120, "walnuts": 15},
        },
        {
            "name": "Яичница с помидорами и шпинатом",
            "goals": ["loss", "gain", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"eggs": 2, "tomato": 100, "spinach": 40, "olive_oil": 5},
        },
        {
            "name": "Гречневая каша с отварной курицей",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"buckwheat": 70, "chicken": 120, "olive_oil": 5},
        },
        {
            "name": "Творог с ягодами и мёдом",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free"],
            "ingredients": {"cottage_cheese": 150, "berries": 60, "honey": 15},
        },
        {
            "name": "Смузи: банан, шпинат, овсянка",
            "goals": ["loss", "variety"],
            "tags": ["vegetarian", "lactose_free"],
            "ingredients": {"banana": 120, "spinach": 40, "plant_milk": 200, "oats": 30},
        },
        {
            "name": "Тост с авокадо и яйцом",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["vegetarian", "lactose_free"],
            "ingredients": {"bread": 60, "avocado": 0.5, "eggs": 1},
        },
        {
            "name": "Рисовая каша с яблоком",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"rice": 70, "apple": 120, "honey": 10},
        },
        {
            "name": "Овсянка с яблоком",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "lactose_free"],
            "ingredients": {"oats": 70, "apple": 130},
        },
    ],
    "lunch": [
        {
            "name": "Овощной плов с нутом",
            "goals": ['gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"rice": 100, "chickpeas": 90, "carrot": 80, "onion": 60, "olive_oil": 15},
            "recipe": {
                "time": 55,
                "steps": [
                    "Нут замочить заранее на 8 часов и отварить 40 минут до мягкости (или взять консервированный).",
                    "Рис промыть до прозрачной воды — иначе плов слипнется.",
                    "В казане разогреть масло, обжарить лук полукольцами 5 минут до золотистого цвета.",
                    "Добавить морковь крупной соломкой, жарить ещё 5 минут, затем всыпать нут и специи.",
                    "Выложить рис ровным слоем, не перемешивая. Залить горячей водой на 1,5 см выше риса.",
                    "Готовить на среднем огне, пока вода не сравняется с рисом, затем убавить огонь до минимума, накрыть крышкой и томить 20 минут.",
                    "Снять с огня, дать постоять 10 минут под крышкой и только потом перемешать.",
                ],
            },
        },
        {
            "name": "Чечевица с рисом и овощами",
            "goals": ['loss', 'gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"lentils": 80, "rice": 60, "carrot": 60, "onion": 40, "olive_oil": 10},
        },
        {
            "name": "Картофель с тофу и овощами",
            "goals": ['gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"potato": 200, "tofu": 100, "vegetables_mix": 120, "olive_oil": 10},
        },
        {
            "name": "Гречка с грибами и луком",
            "goals": ['loss', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"buckwheat": 80, "mushrooms": 150, "onion": 50, "olive_oil": 10},
        },
        {
            "name": "Гречка с тушёной морковью и луком",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"buckwheat": 90, "carrot": 80, "onion": 50, "olive_oil": 5},
        },
        {
            "name": "Картофель с яйцом и салатом",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"potato": 200, "eggs": 2, "cucumber": 80, "olive_oil": 5},
        },
        {
            "name": "Куриная грудка с киноа и овощами",
            "goals": ["loss", "gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"chicken": 150, "quinoa": 70, "vegetables_mix": 150},
        },
        {
            "name": "Суп-пюре из чечевицы",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"lentils": 80, "carrot": 60, "onion": 40, "potato": 100, "olive_oil": 5},
            "recipe": {
                "time": 45,
                "steps": [
                    "Чечевицу промыть. Красная разваривается за 20 минут, зелёная — за 40, учитывай это при расчёте времени.",
                    "Лук и морковь нарезать мелким кубиком, обжарить на масле 7 минут до мягкости.",
                    "Картофель нарезать кубиками, добавить в кастрюлю вместе с чечевицей и обжаренными овощами.",
                    "Залить водой так, чтобы она покрывала овощи на 3 см. Довести до кипения, снять пену.",
                    "Варить на слабом огне 25-35 минут, пока чечевица полностью не разварится.",
                    "Пробить блендером до однородности. Если густо — добавить горячей воды. Посолить, поперчить.",
                ],
            },
        },
        {
            "name": "Паста с томатным соусом",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["vegetarian", "lactose_free"],
            "ingredients": {"pasta": 100, "tomato_sauce": 100, "olive_oil": 5},
        },
        {
            "name": "Рис с тушёными овощами и тофу",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"rice": 80, "tofu": 100, "vegetables_mix": 150},
        },
        {
            "name": "Говядина с гречкой и салатом",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"beef": 130, "buckwheat": 70, "cucumber": 80, "tomato": 80},
        },
        {
            "name": "Салат с киноа, нутом и брынзой",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free"],
            "ingredients": {"quinoa": 60, "chickpeas": 80, "feta": 50, "lettuce": 50, "olive_oil": 5},
        },
        {
            "name": "Куриный суп с картофелем",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"chicken": 120, "potato": 150, "carrot": 60, "onion": 40},
            "recipe": {
                "time": 60,
                "steps": [
                    "Курицу залить холодной водой, довести до кипения. Первую воду слить и залить свежей — бульон будет прозрачнее.",
                    "Варить 30 минут на слабом огне, снимая пену. Кипение должно быть еле заметным.",
                    "Достать курицу, нарезать. Картофель нарезать кубиками и отправить в бульон.",
                    "Лук и морковь мелко нарезать, обжарить на масле 5-7 минут, добавить в суп.",
                    "Варить 15 минут до мягкости картофеля, вернуть мясо, посолить.",
                    "Снять с огня и дать настояться под крышкой 10 минут — вкус станет заметно насыщеннее.",
                ],
            },
        },
        {
            "name": "Гуляш из говядины с гречкой",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"beef": 150, "onion": 60, "carrot": 60,
                            "tomato_sauce": 80, "buckwheat": 70, "olive_oil": 10},
            "recipe": {
                "time": 90,
                "steps": [
                    "Мясо нарезать кубиками примерно 3 см, обсушить бумажным полотенцем — так оно лучше подрумянится.",
                    "Разогреть сковороду с маслом на сильном огне, обжарить мясо порциями до румяной корочки (5-7 минут). Не класть всё сразу, иначе мясо начнёт тушиться вместо жарки.",
                    "Лук нарезать полукольцами, морковь — соломкой. Добавить к мясу, жарить 5 минут до мягкости лука.",
                    "Влить томатный соус и стакан горячей воды, посолить, поперчить. Довести до кипения.",
                    "Убавить огонь до минимума, накрыть крышкой и тушить 60-70 минут, пока мясо не станет мягким. Помешивать каждые 20 минут, при необходимости подливать воду.",
                    "За 20 минут до готовности отварить гречку: 1 часть крупы на 2 части воды, довести до кипения и варить под крышкой 15 минут.",
                    "Подавать гуляш с гречкой, полив соусом из сковороды.",
                ],
            },
        },
        {
            "name": "Плов с курицей",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"rice": 100, "chicken": 150, "carrot": 80,
                            "onion": 60, "olive_oil": 15},
            "recipe": {
                "time": 60,
                "steps": [
                    "Рис промыть в холодной воде 4-5 раз, пока вода не станет прозрачной — это главное условие рассыпчатого плова.",
                    "Курицу нарезать крупными кусками. В казане или толстостенной кастрюле разогреть масло и обжарить курицу до золотистого цвета (около 7 минут).",
                    "Добавить лук полукольцами, обжарить 4 минуты. Затем морковь крупной соломкой (не тереть на тёрке — она разварится), жарить ещё 5 минут.",
                    "Посолить, добавить специи по вкусу, влить горячую воду так, чтобы она покрыла содержимое на 1 см. Тушить 20 минут на среднем огне.",
                    "Выложить рис ровным слоем поверх мяса, НЕ перемешивая. Долить горячей воды на 1,5 см выше уровня риса.",
                    "Готовить на среднем огне без крышки, пока вода не уйдёт вровень с рисом (10-15 минут).",
                    "Сделать в рисе несколько отверстий до дна, накрыть крышкой, убавить огонь до минимума и томить 20 минут. После выключения дать постоять 10 минут и только потом перемешать.",
                ],
            },
        },
    ],
    "dinner": [
        {
            "name": "Омлет с брокколи",
            "goals": ['loss', 'gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"eggs": 3, "broccoli": 120, "olive_oil": 5},
        },
        {
            "name": "Овощное рагу с тофу",
            "goals": ['gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"tofu": 120, "potato": 150, "carrot": 60, "onion": 40, "tomato_sauce": 60},
            "recipe": {
                "time": 45,
                "steps": [
                    "Тофу обсушить бумажным полотенцем и нарезать кубиками — лишняя влага мешает ему подрумяниться.",
                    "Обжарить тофу на масле до золотистой корочки со всех сторон (около 8 минут), выложить на тарелку.",
                    "В той же сковороде обжарить лук и морковь 5 минут.",
                    "Добавить картофель кубиками, влить томатный соус и стакан воды, посолить.",
                    "Тушить под крышкой 25 минут до мягкости картофеля.",
                    "Вернуть тофу в сковороду, прогреть вместе 3 минуты и снять с огня.",
                ],
            },
        },
        {
            "name": "Киноа с нутом и овощами",
            "goals": ['loss', 'gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"quinoa": 70, "chickpeas": 90, "vegetables_mix": 130, "olive_oil": 10},
        },
        {
            "name": "Тушёные грибы с картофелем",
            "goals": ['gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"mushrooms": 180, "potato": 180, "onion": 50, "olive_oil": 10},
            "recipe": {
                "time": 40,
                "steps": [
                    "Грибы нарезать пластинками. Выложить на сухую сковороду и выпарить влагу 5-7 минут — иначе они будут вариться, а не жариться.",
                    "Добавить масло и лук, обжарить до золотистого цвета (5 минут).",
                    "Картофель нарезать брусочками, добавить к грибам.",
                    "Влить полстакана воды, посолить, накрыть крышкой и тушить 25 минут до мягкости картофеля.",
                    "В конце снять крышку и дать лишней жидкости выпариться 3-5 минут.",
                ],
            },
        },
        {
            "name": "Тушёная капуста с индейкой",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"cabbage": 250, "turkey": 130, "carrot": 50,
                            "onion": 50, "tomato_sauce": 50, "olive_oil": 10},
            "recipe": {
                "time": 50,
                "steps": [
                    "Индейку нарезать кубиками, обжарить на масле до белого цвета (5-7 минут).",
                    "Добавить лук кубиком и тёртую морковь, жарить 5 минут.",
                    "Капусту нашинковать тонкой соломкой, добавить в сковороду. Сначала покажется, что её слишком много — она осядет через 5-7 минут.",
                    "Влить томатный соус и полстакана воды, посолить. Перемешать.",
                    "Накрыть крышкой и тушить на слабом огне 30 минут, помешивая каждые 10 минут. Капуста должна стать мягкой, но не превратиться в кашу.",
                    "В конце попробовать на соль, при желании добавить щепотку сахара — он смягчает кислоту томата.",
                ],
            },
        },
        {
            "name": "Запечённая рыба с овощами",
            "goals": ["loss", "gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"fish": 150, "vegetables_mix": 150, "olive_oil": 5},
            "recipe": {
                "time": 40,
                "steps": [
                    "Духовку разогреть до 200 °C.",
                    "Рыбу обсушить, посолить, сбрызнуть лимонным соком и оставить на 10 минут.",
                    "Овощи нарезать крупными кусками, перемешать с маслом и солью, выложить на противень.",
                    "Запекать овощи 15 минут, затем выложить к ним рыбу.",
                    "Запекать вместе ещё 15-20 минут. Рыба готова, когда мякоть легко разделяется вилкой и стала матовой.",
                ],
            },
        },
        {
            "name": "Омлет с овощами",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"eggs": 3, "tomato": 80, "onion": 30, "olive_oil": 5},
        },
        {
            "name": "Курица с брокколи и бурым рисом",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"chicken": 140, "broccoli": 150, "brown_rice": 70},
            "recipe": {
                "time": 45,
                "steps": [
                    "Бурый рис варится дольше белого — 35-40 минут. Поставить его первым: 1 часть риса на 2,5 части воды.",
                    "Курицу нарезать полосками, обжарить на сильном огне 7-8 минут до румяности.",
                    "Брокколи разобрать на соцветия, опустить в кипяток на 4 минуты, затем откинуть — так она останется яркой и хрустящей.",
                    "Соединить курицу с брокколи, посолить, прогреть вместе 2 минуты.",
                    "Подавать с готовым рисом.",
                ],
            },
        },
        {
            "name": "Овощное рагу с нутом",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"chickpeas": 90, "potato": 120, "carrot": 60, "onion": 40, "tomato_sauce": 60},
            "recipe": {
                "time": 50,
                "steps": [
                    "Нут желательно замочить с вечера на 8 часов, тогда он сварится за 40 минут. Если времени нет, подойдёт консервированный — добавляй его в самом конце.",
                    "Лук и морковь обжарить на масле 5 минут.",
                    "Картофель нарезать кубиками, добавить к овощам, обжарить ещё 5 минут.",
                    "Влить томатный соус и стакан воды, добавить отваренный нут, посолить.",
                    "Тушить под крышкой 25-30 минут до мягкости картофеля, помешивая пару раз.",
                    "В конце добавить зелень и дать постоять 5 минут.",
                ],
            },
        },
        {
            "name": "Творожная запеканка",
            "goals": ["maintain", "gain", "variety"],
            "tags": ["vegetarian", "gluten_free"],
            "ingredients": {"cottage_cheese": 180, "eggs": 1, "honey": 10},
            "recipe": {
                "time": 60,
                "steps": [
                    "Духовку разогреть до 180 °C заранее — запеканка не любит холодную духовку.",
                    "Творог протереть через сито или пробить блендером, чтобы не было крупинок.",
                    "Добавить яйцо и мёд, тщательно перемешать до однородной массы.",
                    "Форму смазать маслом, выложить массу, разровнять ложкой.",
                    "Выпекать 35-40 минут до золотистой корочки. Не открывать духовку первые 25 минут, иначе запеканка осядет.",
                    "Дать остыть в форме минимум 15 минут — горячая запеканка разваливается при нарезке.",
                ],
            },
        },
        {
            "name": "Индейка с киноа и салатом",
            "goals": ["loss", "gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"turkey": 140, "quinoa": 70, "lettuce": 50, "cucumber": 70},
        },
        {
            "name": "Рыба с картофелем и салатом",
            "goals": ["maintain", "gain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"fish": 150, "potato": 180, "cucumber": 80, "olive_oil": 5},
        },
    ],
    "snack": [
        {
            "name": "Смузи с бананом и арахисовой пастой",
            "goals": ['gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"banana": 130, "plant_milk": 200, "peanut_butter": 20},
        },
        {
            "name": "Горсть грецких орехов",
            "goals": ['loss', 'gain', 'maintain', 'variety'],
            "tags": ['vegetarian', 'gluten_free', 'lactose_free'],
            "ingredients": {"walnuts": 30},
        },
        {
            "name": "Горсть орехов и сухофруктов",
            "goals": ["loss", "gain", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"nuts_mix": 40},
        },
        {
            "name": "Яблоко с арахисовой пастой",
            "goals": ["loss", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"apple": 150, "peanut_butter": 20},
        },
        {
            "name": "Греческий йогурт с мёдом",
            "goals": ["maintain", "gain", "variety"],
            "tags": ["vegetarian", "gluten_free"],
            "ingredients": {"greek_yogurt": 150, "honey": 10},
        },
        {
            "name": "Два варёных яйца",
            "goals": ["gain", "maintain", "variety"],
            "tags": ["gluten_free", "lactose_free"],
            "ingredients": {"eggs": 2},
        },
        {
            "name": "Банан",
            "goals": ["loss", "gain", "maintain", "variety"],
            "tags": ["vegetarian", "gluten_free", "lactose_free"],
            "ingredients": {"banana": 130},
        },
    ],
}

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
}

MEAL_TYPE_LABELS = {
    "breakfast": "🌅 Завтрак",
    "lunch": "🥗 Обед",
    "dinner": "🍽 Ужин",
    "snack": "🍎 Перекус",
}

# Бюджетные пресеты на неделю (рубли, на одного человека).
# Пороги подобраны по фактическим расчётам бота для средней полосы России.
BUDGET_PRESETS = {
    "economy": {"name": "💰 Эконом", "limit": 4000, "hint": "до 4 000 ₽"},
    "medium":  {"name": "🛒 Средний", "limit": 5500, "hint": "до 5 500 ₽"},
    "comfort": {"name": "✨ Комфорт", "limit": 7000, "hint": "до 7 000 ₽"},
    "any":     {"name": "♾ Без ограничений", "limit": None, "hint": "не ограничен"},
}
