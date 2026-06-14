def american_to_decimal(odds: float) -> float:
    if odds > 0:
        return (odds / 100) + 1
    return (100 / abs(odds)) + 1


def american_to_prob(odds: float) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def detect_value(model_prob: float, market_odds: float, quarter_kelly: bool = True) -> dict:
    """
    Compare model probability vs market implied probability.
    Returns edge metrics and Kelly Criterion stake recommendation.
    """
    market_prob = american_to_prob(market_odds)
    decimal_odds = american_to_decimal(market_odds)

    # Remove vig from implied prob for cleaner comparison
    edge = float(model_prob) - float(market_prob)
    is_value = bool(edge > 0.05)  # 5% minimum edge threshold

    # Kelly Criterion: f = (bp - q) / b  where b = decimal_odds - 1
    b = decimal_odds - 1
    p = model_prob
    q = 1 - model_prob
    full_kelly = (b * p - q) / b if b > 0 else 0
    kelly_stake_pct = max(0, full_kelly * (0.25 if quarter_kelly else 1.0))

    expected_value = (model_prob * (decimal_odds - 1)) - (1 - model_prob)

    return {
        "model_prob": round(model_prob * 100, 1),
        "market_prob": round(market_prob * 100, 1),
        "edge_pct": round(edge * 100, 1),
        "is_value": is_value,
        "kelly_stake_pct": round(kelly_stake_pct * 100, 1),
        "expected_value": round(expected_value, 3),
    }
