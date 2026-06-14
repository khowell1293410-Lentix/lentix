from odds_client import get_events
from models import soccer_model, nba_model, ufc_model
from models.value_detector import detect_value, american_to_prob

SOCCER_SPORTS = {"soccer", "world_cup"}
NBA_SPORTS = {"nba"}
UFC_SPORTS = {"ufc", "boxing"}


def _baseline_analyze(event: dict) -> dict:
    """Fallback: implied probability + home edge for unsupported sports."""
    home_implied = american_to_prob(event["home_odds"])
    away_implied = american_to_prob(event["away_odds"])
    total = home_implied + away_implied
    home_prob = min(0.95, (home_implied / total) + 0.03)
    away_prob = 1 - home_prob

    value = detect_value(
        home_prob if home_prob >= away_prob else away_prob,
        event["home_odds"] if home_prob >= away_prob else event["away_odds"]
    )

    predicted_winner = event["home_team"] if home_prob >= away_prob else event["away_team"]
    confidence = round(max(home_prob, away_prob) * 100, 1)

    return {
        **event,
        "predicted_winner": predicted_winner,
        "confidence": confidence,
        "home_win_prob": round(home_prob * 100, 1),
        "away_win_prob": round(away_prob * 100, 1),
        "edge_pct": value["edge_pct"],
        "is_value": value["is_value"],
        "kelly_stake_pct": value["kelly_stake_pct"],
        "expected_value": value["expected_value"],
        "flags": [],
        "model": "baseline",
    }


def _analyze_event(event: dict, sport: str) -> dict:
    try:
        if sport in SOCCER_SPORTS:
            return soccer_model.analyze(event)
        if sport in NBA_SPORTS:
            return nba_model.analyze(event)
        if sport in UFC_SPORTS:
            return ufc_model.analyze(event)
        return _baseline_analyze(event)
    except Exception as e:
        result = _baseline_analyze(event)
        result["model_error"] = str(e)
        return result


def get_predictions(sport: str) -> list[dict]:
    events = get_events(sport)
    predictions = [_analyze_event(e, sport) for e in events]
    return sorted(predictions, key=lambda x: x["confidence"], reverse=True)


def get_value_bets(sport: str, min_edge: float = 5.0) -> list[dict]:
    predictions = get_predictions(sport)
    value = [p for p in predictions if p.get("edge_pct", 0) >= min_edge]
    return sorted(value, key=lambda x: x["edge_pct"], reverse=True)
