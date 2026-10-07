from app.services.intent import classify_intent
from app.services.ner import extract_entities, entities_to_ir_format
from app.services.preprocessing import normalize_text


def test_comparison():
    assert classify_intent("Compare sales between Colombo and Kandy in January") == "COMPARISON"


def test_ranking():
    assert classify_intent("Which product had the highest sales last month?") == "RANKING"


def test_aggregation():
    assert classify_intent("What is the total revenue this month?") == "AGGREGATION"


def test_forecast():
    assert classify_intent("What will the sales be next month?") == "FORECAST_REQUEST"


def test_entities():
    entities = extract_entities("Compare sales between Colombo and Kandy in January")
    ir = entities_to_ir_format(entities)
    assert "Colombo" in ir["location"]
    assert "Kandy" in ir["location"]
    assert "sales" in ir["metric"]
    assert "January" in ir["time_period"]


def test_normalization():
    assert normalize_text("  hello    world  ") == "hello world"
