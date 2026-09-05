from meza.orchestrator.router import classify_intent, route_domains


def test_route_production_keywords():
    assert "production" in route_domains("Почему задерживается производство заказа 123?")


def test_route_warehouse_keywords():
    assert "warehouse" in route_domains("Какие материалы заканчиваются на складе?")


def test_route_finance_keywords():
    assert "finance" in route_domains("Почему снизилась маржинальность заказа?")


def test_route_vague_question_fans_out_broadly():
    domains = route_domains("Что сейчас происходит в компании?")
    assert "overview" in domains
    assert "production" in domains
    assert "finance" in domains


def test_classify_intent_what_changed():
    assert classify_intent("Что изменилось за последние 24 часа?") == "what_changed"


def test_classify_intent_daily_brief():
    assert classify_intent("Подготовь утренний отчёт") == "daily_brief"


def test_classify_intent_none_for_unrelated_text():
    assert classify_intent("Привет, как дела?") is None
