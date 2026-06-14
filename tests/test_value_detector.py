import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.value_detector import american_to_prob, american_to_decimal, detect_value


def test_american_to_prob_favorite():
    prob = american_to_prob(-200)
    assert abs(prob - 0.6667) < 0.001


def test_american_to_prob_underdog():
    prob = american_to_prob(+100)
    assert abs(prob - 0.5) < 0.001


def test_american_to_prob_heavy_underdog():
    prob = american_to_prob(+300)
    assert abs(prob - 0.25) < 0.001


def test_american_to_decimal_positive():
    assert american_to_decimal(+100) == 2.0


def test_american_to_decimal_negative():
    assert abs(american_to_decimal(-200) - 1.5) < 0.001


def test_detect_value_positive_edge():
    result = detect_value(model_prob=0.65, market_odds=+120)
    assert result["is_value"] is True
    assert result["edge_pct"] > 0
    assert result["kelly_stake_pct"] > 0


def test_detect_value_no_edge():
    result = detect_value(model_prob=0.45, market_odds=-110)
    assert result["is_value"] is False
    assert result["kelly_stake_pct"] == 0


def test_detect_value_returns_all_keys():
    result = detect_value(model_prob=0.55, market_odds=-110)
    for key in ("model_prob", "market_prob", "edge_pct", "is_value", "kelly_stake_pct", "expected_value"):
        assert key in result
