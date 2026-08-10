"""Тесты food_lookup.py.

Значительная часть — регрессии на три реальных бага:
  1) "1 кг" разбирался как 1 грамм (строка содержит "г", поэтому старый код
     считал её граммовкой и просто склеивал цифры);
  2) на запрос "жареная картошка" Open Food Facts отдавал "Сырок Картошка",
     и бот показывал КБЖУ творожного сырка;
  3) "2 яблока" записывались как 100 г яблока (~52 ккал): счёт в штуках
     игнорировался, потому что единицы веса в запросе не было.

Сеть здесь не используется: requests.get всегда подменяется (плюс глобальная
автофикстура в conftest.py, которая ловит любой незамоканный запрос).
"""

import pytest
import requests

import ai_agent
import food_lookup
import nutrition_data
import products


# ---------- _parse_grams ----------

@pytest.mark.parametrize("text,expected", [
    ("100 г", 100.0),
    ("100г", 100.0),
    ("250 гр", 250.0),
    ("42g", 42.0),
    ("300 грамм", 300.0),
    ("150 граммов", 150.0),
])
def test_parse_grams_reads_gram_units(text, expected):
    assert food_lookup._parse_grams(text) == pytest.approx(expected)


def test_parse_grams_accepts_comma_as_decimal_separator():
    assert food_lookup._parse_grams("52,7g") == pytest.approx(52.7)


def test_parse_grams_accepts_dot_as_decimal_separator():
    assert food_lookup._parse_grams("52.7 г") == pytest.approx(52.7)


@pytest.mark.parametrize("text,expected", [
    ("1 кг", 1000.0),
    ("1кг", 1000.0),
    ("1 kg", 1000.0),
    ("1 килограмм", 1000.0),
    ("2 килограмма", 2000.0),
    ("1,5 кг", 1500.0),
])
def test_parse_grams_kilograms_convert_to_grams(text, expected):
    """Регрессия: "кг" содержит "г", раньше "1 кг" превращался в 1 грамм."""
    assert food_lookup._parse_grams(text) == pytest.approx(expected)


def test_parse_grams_kilogram_is_thousand_times_gram():
    assert food_lookup._parse_grams("1 кг") == 1000 * food_lookup._parse_grams("1 г")


def test_parse_grams_finds_amount_inside_a_phrase():
    assert food_lookup._parse_grams("творог 5% 200 г") == pytest.approx(200.0)


@pytest.mark.parametrize("text", ["200", "1.5", "тарелка борща"])
def test_parse_grams_returns_none_without_a_unit(text):
    assert food_lookup._parse_grams(text) is None


@pytest.mark.parametrize("text", ["абракадабра", "", None, "квас 500 мл"])
def test_parse_grams_returns_none_for_junk(text):
    assert food_lookup._parse_grams(text) is None


@pytest.mark.parametrize("text", ["5 кг", "3000 г", "0,5 г"])
def test_parse_grams_rejects_out_of_range_values(text):
    """Диапазон 1..2000 г: мешок картошки или крошка в 0,5 г — не порция еды."""
    assert food_lookup._parse_grams(text) is None


# ---------- _parse_pieces ----------

@pytest.mark.parametrize("text,expected", [
    ("2 яблока", 2),
    ("1 банан", 1),
    ("3 яйца", 3),
    ("5 яиц", 5),
    ("2 авокадо", 2),
    ("10 перепелиных яиц", 10),
])
def test_parse_pieces_reads_a_count_with_a_noun(text, expected):
    assert food_lookup._parse_pieces(text) == expected


@pytest.mark.parametrize("text,expected", [("2 шт", 2), ("2шт", 2), ("3 штуки", 3), ("1 штука", 1)])
def test_parse_pieces_reads_an_explicit_piece_unit(text, expected):
    assert food_lookup._parse_pieces(text) == expected


def test_parse_pieces_bare_name_means_one_piece():
    """Регрессия: "яблоко" оценивалось как 100 г яблока."""
    assert food_lookup._parse_pieces("яблоко") == 1


@pytest.mark.parametrize("text", ["гречка", "огурец", "жареная картошка", "тарелка борща"])
def test_parse_pieces_ignores_food_that_is_not_counted_in_pieces(text):
    assert food_lookup._parse_pieces(text) is None


def test_parse_pieces_ignores_a_food_name_used_as_an_adjective():
    # "банановый смузи" — не один банан
    assert food_lookup._parse_pieces("банановый смузи") is None


@pytest.mark.parametrize("text", [
    "200 грамм жареной картошки",
    "арбуз 1 килограмм",
    "1 кг",
    "2 яблока 300 г",
    "5 килограмм",
    "квас 500 мл",
])
def test_parse_pieces_yields_to_an_explicit_weight(text):
    """Вес всегда важнее счёта, иначе сломались бы "арбуз 1 килограмм" и Ко."""
    assert food_lookup._parse_pieces(text) is None


@pytest.mark.parametrize("text", ["0 яблок", "100 яблок", "999999999999 яблок"])
def test_parse_pieces_rejects_absurd_counts(text):
    assert food_lookup._parse_pieces(text) is None


@pytest.mark.parametrize("text", [None, "", "   ", "?!", "2", "абракадабра"])
def test_parse_pieces_survives_junk(text):
    assert food_lookup._parse_pieces(text) is None


# ---------- _piece_food ----------

@pytest.mark.parametrize("text,key,grams", [
    ("2 яблока", "apple", 180),
    ("яблоко", "apple", 180),
    ("яблоки", "apple", 180),
    ("1 банан", "banana", 120),
    ("2 банана", "banana", 120),
    ("3 яйца", "eggs", 50),
    ("5 яиц", "eggs", 50),
    ("2 авокадо", "avocado", 150),
])
def test_piece_food_matches_loose_noun_forms(text, key, grams):
    assert food_lookup._piece_food(text) == (key, grams)


def test_piece_food_prefers_quail_eggs_over_chicken_ones():
    assert food_lookup._piece_food("10 перепелиных яиц")[0] == "eggs_quail"


@pytest.mark.parametrize("text", ["2 банановых кекса", "яблочный сок", "жареная картошка", "гречка", ""])
def test_piece_food_ignores_adjectives_and_unknown_food(text):
    assert food_lookup._piece_food(text) is None


def test_piece_food_keys_exist_in_the_nutrition_table():
    """Таблица весов бесполезна, если по ключу нет КБЖУ (и нечем подписать карточку)."""
    for _stems, key, _grams in food_lookup._PIECE_FOODS:
        assert key in nutrition_data.NUTRI
        assert products.PRODUCTS.get(key, {}).get("name")


# ---------- _counted_food ----------

@pytest.mark.parametrize("text,key", [
    ("2 яблока", "apple"),
    ("2 больших яблока", "apple"),
    ("2 шт яблок", "apple"),
    ("омлет из 3 яиц", "eggs"),
    ("10 перепелиных яиц", "eggs_quail"),
    ("яблоко", "apple"),
])
def test_counted_food_finds_what_was_counted(text, key):
    assert food_lookup._counted_food(text)[0] == key


@pytest.mark.parametrize("text", ["3 бутерброда с яйцом", "2 котлеты с яйцом", "2 шт", "5 пельменей"])
def test_counted_food_ignores_ingredients_that_were_not_counted(text):
    """Считали бутерброды, а не яйца — вес бутерброда мы не знаем, дальше ИИ."""
    assert food_lookup._counted_food(text) is None


# ---------- _serving_piece_grams ----------

@pytest.mark.parametrize("serving,expected", [
    ("1 шт (180 г)", 180.0),
    ("1 штука (55 г)", 55.0),
    ("1 piece (30 g)", 30.0),
])
def test_serving_piece_grams_reads_a_per_item_serving(serving, expected):
    assert food_lookup._serving_piece_grams(serving) == pytest.approx(expected)


def test_serving_piece_grams_ignores_a_plain_weight_serving():
    # "30 г" — порция производителя, а не вес штуки
    assert food_lookup._serving_piece_grams("30 г") is None


def test_serving_piece_grams_ignores_a_multi_item_serving():
    # "2 шт (60 г)" — вес двух печений, не одного
    assert food_lookup._serving_piece_grams("2 шт (60 г)") is None


@pytest.mark.parametrize("serving", [None, "", "1 шт", "1 шт (900 г)"])
def test_serving_piece_grams_returns_none_without_a_believable_weight(serving):
    assert food_lookup._serving_piece_grams(serving) is None


# ---------- _is_relevant ----------

def test_is_relevant_rejects_the_syrok_kartoshka_regression():
    """Реальный сбой: на "жареная картошка" OFF отдавал творожный сырок."""
    assert food_lookup._is_relevant("жареная картошка", "Сырок Картошка") is False


def test_is_relevant_accepts_a_genuine_match():
    assert food_lookup._is_relevant("жареная картошка", "Картошка жареная по-деревенски") is True


def test_is_relevant_accepts_exact_name():
    assert food_lookup._is_relevant("гречка", "Гречка ядрица") is True


def test_is_relevant_rejects_unrelated_product():
    assert food_lookup._is_relevant("куриная грудка", "Шоколад молочный") is False


def test_is_relevant_ignores_missing_product_name():
    assert food_lookup._is_relevant("гречка", None) is False


def test_is_relevant_allows_anything_when_query_has_no_meaningful_words():
    # запрос "1 кг" целиком состоит из граммовки — фильтровать нечем
    assert food_lookup._is_relevant("1 кг", "Что угодно") is True


def test_is_relevant_ignores_weight_words_in_the_query():
    # "200 г" не должно требовать слова "грамм" в названии товара
    assert food_lookup._is_relevant("творог 200 г", "Творог 5%") is True


# ---------- _from_off_hit ----------

def _hit(**overrides):
    hit = {
        "product_name": "Огурец свежий",
        "nutriments": {
            "energy-kcal_100g": 27,
            "proteins_100g": 1.0,
            "fat_100g": 0.2,
            "carbohydrates_100g": 4.0,
        },
    }
    hit.update(overrides)
    return hit


def test_from_off_hit_scales_by_user_amount_not_by_package_weight():
    """Регрессия: 1 кг продукта с 27 ккал/100 г — это 270 ккал, а не 27."""
    result = food_lookup._from_off_hit(_hit(quantity="500 г"), user_grams=1000)

    assert result["kcal"] == 270
    assert result["protein"] == 10
    assert result["carbs"] == 40
    assert result["portion"] == "1000 г"


def test_from_off_hit_user_amount_below_100g_scales_down():
    result = food_lookup._from_off_hit(_hit(), user_grams=50)
    assert result["kcal"] == 14  # round(27 * 0.5) = 14 (округление half-even от 13.5)
    assert result["portion"] == "50 г"


def test_from_off_hit_without_user_amount_uses_package_quantity():
    result = food_lookup._from_off_hit(_hit(quantity="150 г"))
    assert result["portion"] == "150 г"
    assert result["kcal"] == round(27 * 1.5)


def test_from_off_hit_falls_back_to_serving_size_when_no_quantity():
    result = food_lookup._from_off_hit(_hit(serving_size="30 g"))
    assert result["portion"] == "30 г"


def test_from_off_hit_ignores_bulk_packaging_over_200g():
    # "1 кг" — вес мешка крупы, а не порция: берём стандартные 100 г
    result = food_lookup._from_off_hit(_hit(quantity="1 кг"))
    assert result["portion"] == "100 г"
    assert result["kcal"] == 27


def test_from_off_hit_defaults_to_100g_when_no_weight_data():
    result = food_lookup._from_off_hit(_hit())
    assert result["portion"] == "100 г"
    assert result["kcal"] == 27


def test_from_off_hit_returns_none_without_calorie_data():
    assert food_lookup._from_off_hit({"product_name": "X", "nutriments": {}}) is None
    assert food_lookup._from_off_hit({"product_name": "X"}) is None


def test_from_off_hit_treats_missing_macros_as_zero():
    result = food_lookup._from_off_hit({"nutriments": {"energy-kcal_100g": 100}})
    assert (result["protein"], result["fat"], result["carbs"]) == (0, 0, 0)
    assert result["name"] == "Продукт"


def test_from_off_hit_marks_the_source():
    assert food_lookup._from_off_hit(_hit())["note"] == "источник: Open Food Facts"


# ---------- _from_off_hit: счёт в штуках ----------

def _apple_hit(**overrides):
    hit = {
        "product_name": "Яблоко",
        "nutriments": {
            "energy-kcal_100g": 52,
            "proteins_100g": 0.3,
            "fat_100g": 0.2,
            "carbohydrates_100g": 14,
        },
    }
    hit.update(overrides)
    return hit


def test_from_off_hit_multiplies_the_known_piece_weight():
    result = food_lookup._from_off_hit(_apple_hit(), pieces=2, piece_grams=180)

    assert result["portion"] == "2 шт (≈360 г)"
    assert result["kcal"] == round(52 * 3.6)
    assert result["carbs"] == round(14 * 3.6)


def test_from_off_hit_portion_says_what_was_counted():
    """В карточке подтверждения "360 г" выглядит как измеренный вес — врать нельзя."""
    assert "2 шт" in food_lookup._from_off_hit(_apple_hit(), pieces=2, piece_grams=180)["portion"]


def test_from_off_hit_prefers_product_serving_size_over_the_local_table():
    hit = _apple_hit(serving_size="1 шт (200 г)")
    assert food_lookup._from_off_hit(hit, pieces=2, piece_grams=180)["portion"] == "2 шт (≈400 г)"


def test_from_off_hit_refuses_to_count_pieces_it_cannot_weigh():
    """Главный баг: "2 яблока" превращались в 100 г. Лучше None — дальше ИИ."""
    assert food_lookup._from_off_hit(_apple_hit(), pieces=2) is None


def test_from_off_hit_ignores_package_quantity_when_counting_pieces():
    # "1 кг" — фасовка пакета яблок, а не вес одного
    result = food_lookup._from_off_hit(_apple_hit(quantity="1 кг"), pieces=2, piece_grams=180)
    assert result["portion"] == "2 шт (≈360 г)"


def test_from_off_hit_explicit_grams_win_over_pieces():
    result = food_lookup._from_off_hit(_apple_hit(), user_grams=300, pieces=2, piece_grams=180)
    assert result["portion"] == "300 г"


# ---------- _from_local_pieces ----------

def test_from_local_pieces_counts_apples():
    result = food_lookup._from_local_pieces("2 яблока")

    assert result["portion"] == "2 шт (≈360 г)"
    assert 150 <= result["kcal"] <= 250
    assert result["note"]


def test_from_local_pieces_uses_per_piece_values_for_eggs():
    """NUTRI хранит яйца за штуку, а не за 100 г — легко поделить лишний раз."""
    result = food_lookup._from_local_pieces("3 яйца")

    assert result["portion"] == "3 шт (≈150 г)"
    assert result["kcal"] == 3 * nutrition_data.NUTRI["eggs"][0]
    assert 180 <= result["kcal"] <= 300


def test_from_local_pieces_scales_per_100g_values_by_weight():
    # банан лежит в NUTRI за 100 г: 120 г банана — это меньше, чем 89 ккал * 1
    result = food_lookup._from_local_pieces("1 банан")

    assert result["portion"] == "1 шт (≈120 г)"
    assert result["kcal"] == round(nutrition_data.NUTRI["banana"][0] * 1.2)


def test_from_local_pieces_bare_name_is_one_piece():
    assert food_lookup._from_local_pieces("яблоко")["portion"] == "1 шт (≈180 г)"


def test_from_local_pieces_names_the_product_readably():
    assert food_lookup._from_local_pieces("3 яйца")["name"] == "Яйца куриные"


@pytest.mark.parametrize("text", [
    "2 котлеты", "2 шт", "жареная картошка", "200 грамм жареной картошки", "арбуз 1 килограмм",
    "3 бутерброда с яйцом", "",
])
def test_from_local_pieces_returns_none_when_it_cannot_be_sure(text):
    assert food_lookup._from_local_pieces(text) is None


# ---------- search(): requests замокан ----------

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture
def fake_off(monkeypatch):
    """Подменяет requests.get и записывает вызовы: (payload_or_exc) -> список вызовов."""
    calls = []

    def install(payload=None, exc=None):
        def fake_get(url, **kwargs):
            calls.append({"url": url, **kwargs})
            if exc is not None:
                raise exc
            return _FakeResponse(payload)

        monkeypatch.setattr(food_lookup.requests, "get", fake_get)
        return calls

    return install


def test_search_returns_first_relevant_hit(fake_off):
    fake_off({"hits": [_hit(product_name="Огурец тепличный")]})

    result = food_lookup.search("огурец")

    assert result is not None
    assert result["name"] == "Огурец тепличный"
    assert result["kcal"] == 27


def test_search_queries_open_food_facts_with_the_user_text(fake_off):
    calls = fake_off({"hits": []})

    food_lookup.search("огурец")

    assert len(calls) == 1
    assert calls[0]["url"] == food_lookup.SEARCH_URL
    assert calls[0]["params"]["q"] == "огурец"


def test_search_skips_irrelevant_hits_and_returns_none(fake_off):
    fake_off({"hits": [_hit(product_name="Сырок Картошка")]})

    assert food_lookup.search("жареная картошка") is None


def test_search_walks_past_irrelevant_hits_to_a_relevant_one(fake_off):
    fake_off({"hits": [
        _hit(product_name="Сырок Картошка"),
        _hit(product_name="Картошка жареная", nutriments={"energy-kcal_100g": 190}),
    ]})

    result = food_lookup.search("жареная картошка")

    assert result is not None
    assert result["name"] == "Картошка жареная"


def test_search_scales_result_by_grams_from_the_query(fake_off):
    fake_off({"hits": [_hit(product_name="Огурец свежий")]})

    result = food_lookup.search("огурец 1 кг")

    assert result["kcal"] == 270
    assert result["portion"] == "1000 г"


def test_search_returns_none_on_empty_hits(fake_off):
    fake_off({"hits": []})
    assert food_lookup.search("огурец") is None


def test_search_returns_none_when_off_is_down(fake_off):
    fake_off(exc=requests.RequestException("connection reset"))
    assert food_lookup.search("огурец") is None


def test_search_returns_none_on_broken_json(fake_off):
    fake_off(exc=ValueError("no json"))
    assert food_lookup.search("огурец") is None


def test_search_skips_hits_without_calorie_data(fake_off):
    fake_off({"hits": [{"product_name": "Огурец свежий", "nutriments": {}}]})
    assert food_lookup.search("огурец") is None


# ---------- estimate(): база -> ИИ ----------

def test_estimate_prefers_open_food_facts(fake_off, monkeypatch):
    fake_off({"hits": [_hit(product_name="Огурец свежий")]})
    monkeypatch.setattr(ai_agent, "estimate_food",
                        lambda text: pytest.fail("ИИ не должен вызываться, товар найден"))

    result = food_lookup.estimate("огурец")

    assert result["note"] == "источник: Open Food Facts"


def test_estimate_falls_back_to_ai_when_nothing_relevant(fake_off, monkeypatch):
    fake_off({"hits": [_hit(product_name="Сырок Картошка")]})
    ai_calls = []
    monkeypatch.setattr(ai_agent, "estimate_food",
                        lambda text: ai_calls.append(text) or {"name": "Жареная картошка", "kcal": 300})

    result = food_lookup.estimate("жареная картошка")

    assert ai_calls == ["жареная картошка"]
    assert result == {"name": "Жареная картошка", "kcal": 300}


def test_estimate_falls_back_to_ai_when_off_is_down(fake_off, monkeypatch):
    fake_off(exc=requests.RequestException("timeout"))
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: {"name": text, "kcal": 100})

    assert food_lookup.estimate("тарелка борща")["kcal"] == 100


def test_estimate_returns_none_when_both_sources_fail(fake_off, monkeypatch):
    fake_off({"hits": []})
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: None)

    assert food_lookup.estimate("нечто несъедобное") is None


# ---------- счёт в штуках: search() и estimate() целиком ----------

def _eggs_hit(**overrides):
    hit = {"product_name": "Яйца куриные С1", "nutriments": {"energy-kcal_100g": 157}}
    hit.update(overrides)
    return hit


def test_search_counts_pieces_by_the_local_piece_weight(fake_off):
    fake_off({"hits": [_eggs_hit()]})

    result = food_lookup.search("3 яйца")

    assert result["portion"] == "3 шт (≈150 г)"
    assert result["kcal"] == round(157 * 1.5)


def test_search_counts_pieces_by_the_product_serving_size(fake_off):
    fake_off({"hits": [_eggs_hit(serving_size="1 шт (55 г)")]})

    assert food_lookup.search("3 яйца")["portion"] == "3 шт (≈165 г)"


def test_search_returns_none_when_the_piece_weight_is_unknown(fake_off):
    """"2 шт" — непонятно чего: лучше ничего, чем 100 г наугад."""
    fake_off({"hits": [_hit()]})

    assert food_lookup.search("2 шт") is None


def test_search_keeps_the_100g_default_for_food_without_pieces(fake_off):
    fake_off({"hits": [_hit(product_name="Огурец тепличный")]})

    assert food_lookup.search("огурец")["portion"] == "100 г"


def test_estimate_counts_two_apples_instead_of_returning_100g(fake_off, monkeypatch):
    """Жалоба владельца: "2 яблока" -> 52 ккал (100 г яблока) вместо ~190."""
    fake_off({"hits": [_apple_hit()]})
    monkeypatch.setattr(ai_agent, "estimate_food",
                        lambda text: pytest.fail("вес яблока известен, ИИ не нужен"))

    result = food_lookup.estimate("2 яблока")

    assert "2 шт" in result["portion"]
    assert 150 <= result["kcal"] <= 250


def test_estimate_counts_one_banana(fake_off, monkeypatch):
    fake_off({"hits": []})
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: pytest.fail("ИИ не нужен"))

    result = food_lookup.estimate("1 банан")

    assert result["portion"] == "1 шт (≈120 г)"
    assert 80 <= result["kcal"] <= 140


def test_estimate_counts_three_eggs(fake_off, monkeypatch):
    fake_off({"hits": [_eggs_hit()]})
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: pytest.fail("ИИ не нужен"))

    result = food_lookup.estimate("3 яйца")

    assert result["portion"] == "3 шт (≈150 г)"
    assert 180 <= result["kcal"] <= 300


def test_estimate_bare_apple_is_one_piece_not_100g(fake_off, monkeypatch):
    fake_off({"hits": []})
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: pytest.fail("ИИ не нужен"))

    result = food_lookup.estimate("яблоко")

    assert result["portion"] == "1 шт (≈180 г)"
    assert 60 <= result["kcal"] <= 130


def test_estimate_defers_to_ai_when_a_piece_weight_is_unguessable(fake_off, monkeypatch):
    """Котлета котлете рознь: честная прикидка ИИ лучше выдуманных 100 г."""
    fake_off({"hits": [_hit(product_name="Котлеты куриные", nutriments={"energy-kcal_100g": 220})]})
    ai_calls = []
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: ai_calls.append(text) or {
        "name": "Котлеты куриные", "portion": "2 шт (≈160 г)", "kcal": 350})

    result = food_lookup.estimate("2 котлеты")

    assert ai_calls == ["2 котлеты"]
    assert 200 <= result["kcal"] <= 600


def test_estimate_does_not_count_a_filling_as_the_dish(fake_off, monkeypatch):
    """"3 бутерброда с яйцом" — это не три яйца."""
    fake_off({"hits": []})
    ai_calls = []
    monkeypatch.setattr(ai_agent, "estimate_food",
                        lambda text: ai_calls.append(text) or {"name": text, "kcal": 600})

    assert food_lookup.estimate("3 бутерброда с яйцом")["kcal"] == 600
    assert ai_calls == ["3 бутерброда с яйцом"]


def test_estimate_sends_a_bare_piece_count_to_ai(fake_off, monkeypatch):
    fake_off({"hits": [_hit()]})
    ai_calls = []
    monkeypatch.setattr(ai_agent, "estimate_food",
                        lambda text: ai_calls.append(text) or {"name": text, "kcal": 200})

    assert food_lookup.estimate("2 шт")["kcal"] == 200
    assert ai_calls == ["2 шт"]


# ---------- штуки не должны сломать разбор веса ----------

def test_estimate_still_scales_watermelon_by_kilograms(fake_off, monkeypatch):
    fake_off({"hits": [_hit(product_name="Арбуз", nutriments={"energy-kcal_100g": 30})]})
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: pytest.fail("товар найден"))

    result = food_lookup.estimate("арбуз 1 килограмм")

    assert result["portion"] == "1000 г"
    assert result["kcal"] == 300


def test_estimate_still_scales_fried_potato_by_grams(fake_off, monkeypatch):
    fake_off({"hits": [_hit(product_name="Картошка жареная по-деревенски",
                            nutriments={"energy-kcal_100g": 190})]})
    monkeypatch.setattr(ai_agent, "estimate_food", lambda text: pytest.fail("товар найден"))

    result = food_lookup.estimate("жареная картошка 200 г")

    assert result["portion"] == "200 г"
    assert result["kcal"] == 380


def test_estimate_still_rejects_the_syrok_kartoshka_hit(fake_off, monkeypatch):
    fake_off({"hits": [_hit(product_name="Сырок Картошка")]})
    ai_calls = []
    monkeypatch.setattr(ai_agent, "estimate_food",
                        lambda text: ai_calls.append(text) or {"name": "Жареная картошка", "kcal": 300})

    assert food_lookup.estimate("жареная картошка")["kcal"] == 300
    assert ai_calls == ["жареная картошка"]
