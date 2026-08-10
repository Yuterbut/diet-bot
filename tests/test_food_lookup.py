"""Тесты food_lookup.py.

Значительная часть — регрессии на два реальных бага:
  1) "1 кг" разбирался как 1 грамм (строка содержит "г", поэтому старый код
     считал её граммовкой и просто склеивал цифры);
  2) на запрос "жареная картошка" Open Food Facts отдавал "Сырок Картошка",
     и бот показывал КБЖУ творожного сырка.

Сеть здесь не используется: requests.get всегда подменяется (плюс глобальная
автофикстура в conftest.py, которая ловит любой незамоканный запрос).
"""

import pytest
import requests

import ai_agent
import food_lookup


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
