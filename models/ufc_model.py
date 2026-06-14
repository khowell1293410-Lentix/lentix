from models.value_detector import detect_value, american_to_prob

FINISH_RATE_WEIGHT = 0.15
REACH_THRESHOLD = 3.0  # inches


def _finish_prob_adjustment(finish_rate_a: float, finish_rate_b: float) -> float:
    """Higher combined finish rate = more volatile outcome = slight favorite boost."""
    combined = (finish_rate_a + finish_rate_b) / 2
    return (combined - 0.5) * 0.1


def analyze(event: dict) -> dict:
    home_odds = event["home_odds"]
    away_odds = event["away_odds"]

    home_implied = american_to_prob(home_odds)
    away_implied = american_to_prob(away_odds)
    total = home_implied + away_implied
    home_prob = home_implied / total
    away_prob = away_implied / total

    # Pull optional fighter metadata if enriched upstream
    home_finish_rate = event.get("home_finish_rate", 0.5)
    away_finish_rate = event.get("away_finish_rate", 0.5)
    home_strike_acc = event.get("home_strike_accuracy", 0.45)
    away_strike_acc = event.get("away_strike_accuracy", 0.45)
    home_td_def = event.get("home_td_defense", 0.6)
    away_td_def = event.get("away_td_defense", 0.6)
    reach_gap = event.get("reach_gap_inches", 0.0)  # positive = home fighter longer

    # Striking edge
    strike_delta = (home_strike_acc - away_strike_acc) * 0.2
    home_prob = min(0.92, max(0.08, home_prob + strike_delta))

    # Reach disadvantage flag
    flags = []
    if abs(reach_gap) >= REACH_THRESHOLD:
        if reach_gap > 0:
            home_prob = min(0.92, home_prob + 0.02)
            flags.append(f"📏 Home fighter +{reach_gap}\" reach advantage")
        else:
            home_prob = max(0.08, home_prob - 0.02)
            flags.append(f"📏 Away fighter +{abs(reach_gap)}\" reach advantage")
    away_prob = 1 - home_prob

    finish_prob = round(((home_finish_rate + away_finish_rate) / 2) * 100, 1)

    home_value = detect_value(home_prob, home_odds)
    away_value = detect_value(away_prob, away_odds)

    if home_prob >= away_prob:
        predicted_winner = event["home_team"]
        confidence = round(home_prob * 100, 1)
        value = home_value
    else:
        predicted_winner = event["away_team"]
        confidence = round(away_prob * 100, 1)
        value = away_value

    return {
        **event,
        "predicted_winner": predicted_winner,
        "confidence": confidence,
        "home_win_prob": round(home_prob * 100, 1),
        "away_win_prob": round(away_prob * 100, 1),
        "finish_probability": finish_prob,
        "edge_pct": value["edge_pct"],
        "is_value": value["is_value"],
        "kelly_stake_pct": value["kelly_stake_pct"],
        "expected_value": value["expected_value"],
        "flags": flags,
        "model": "ufc_analytics",
    }
