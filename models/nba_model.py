from datetime import datetime
from models.value_detector import detect_value, american_to_prob

HOME_COURT_BOOST = 0.035
BACK_TO_BACK_PENALTY = 0.06
ONE_DAY_REST_PENALTY = 0.03


def _days_rest(commence_time: str, last_game_time: str | None) -> int:
    if not last_game_time:
        return 3
    try:
        game = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        last = datetime.fromisoformat(last_game_time.replace("Z", "+00:00"))
        return max(0, (game - last).days)
    except Exception:
        return 3


def _rest_factor(days: int) -> float:
    if days == 0:
        return -BACK_TO_BACK_PENALTY
    if days == 1:
        return -ONE_DAY_REST_PENALTY
    return 0.0


def analyze(event: dict) -> dict:
    home_odds = event["home_odds"]
    away_odds = event["away_odds"]

    home_implied = american_to_prob(home_odds)
    away_implied = american_to_prob(away_odds)
    total = home_implied + away_implied
    home_prob = home_implied / total
    away_prob = away_implied / total

    # Home court edge
    home_prob = min(0.95, home_prob + HOME_COURT_BOOST)
    away_prob = 1 - home_prob

    # Rest adjustment from event metadata if available
    home_rest = event.get("home_rest_days")
    away_rest = event.get("away_rest_days")
    if home_rest is not None and away_rest is not None:
        home_prob = min(0.95, max(0.05, home_prob + _rest_factor(home_rest) - _rest_factor(away_rest)))
        away_prob = 1 - home_prob

    # Value detection
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

    flags = []
    if home_rest == 0:
        flags.append("🏃 Home back-to-back")
    if away_rest == 0:
        flags.append("🏃 Away back-to-back")

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
        "flags": flags,
        "model": "nba_efficiency",
    }
