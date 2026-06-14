import math
from scipy.stats import poisson
from data_sources.football_data import get_team_matches, get_head_to_head, search_team
from models.value_detector import detect_value, american_to_prob

LEAGUE_AVG_GOALS = 1.35
HOME_ADVANTAGE = 1.15
FORM_DECAY = 0.85  # exponential weight decay per game back


def _parse_goals(match: dict, team_id: int) -> tuple[int, int]:
    home_id = match.get("homeTeam", {}).get("id")
    score = match.get("score", {}).get("fullTime", {})
    if home_id == team_id:
        return score.get("home", 0) or 0, score.get("away", 0) or 0
    return score.get("away", 0) or 0, score.get("home", 0) or 0


def _form_stats(matches: list[dict], team_id: int) -> dict:
    """Weighted attack/defense stats using exponential decay on recency."""
    if not matches:
        return {"attack": 1.0, "defense": 1.0, "form": [], "avg_scored": LEAGUE_AVG_GOALS, "avg_conceded": LEAGUE_AVG_GOALS}

    scored = conceded = weight_sum = 0.0
    form = []
    for i, m in enumerate(reversed(matches[-10:])):
        w = FORM_DECAY ** i
        gf, ga = _parse_goals(m, team_id)
        scored += gf * w
        conceded += ga * w
        weight_sum += w
        if i < 5:
            form.append("W" if gf > ga else ("D" if gf == ga else "L"))

    avg_scored = scored / weight_sum if weight_sum else LEAGUE_AVG_GOALS
    avg_conceded = conceded / weight_sum if weight_sum else LEAGUE_AVG_GOALS

    return {
        "attack": avg_scored / LEAGUE_AVG_GOALS,
        "defense": avg_conceded / LEAGUE_AVG_GOALS,
        "form": form,
        "avg_scored": round(avg_scored, 2),
        "avg_conceded": round(avg_conceded, 2),
    }


def _h2h_adjustment(h2h_matches: list[dict], home_id: int) -> float:
    """±5% if one team dominates H2H."""
    if len(h2h_matches) < 3:
        return 0.0
    home_wins = sum(
        1 for m in h2h_matches
        if _parse_goals(m, home_id)[0] > _parse_goals(m, home_id)[1]
    )
    ratio = home_wins / len(h2h_matches)
    if ratio >= 0.67:
        return 0.05
    if ratio <= 0.33:
        return -0.05
    return 0.0


def _scoreline_grid(home_xg: float, away_xg: float, max_goals: int = 6) -> dict:
    home_win = draw = away_win = 0.0
    top_scorelines = []

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
            if p > 0.03:
                top_scorelines.append({"score": f"{i}-{j}", "prob": round(p * 100, 1)})

    top_scorelines.sort(key=lambda x: x["prob"], reverse=True)
    return {
        "home_win": round(home_win, 4),
        "draw": round(draw, 4),
        "away_win": round(away_win, 4),
        "top_scorelines": top_scorelines[:5],
    }


def analyze(event: dict) -> dict:
    home_team = event["home_team"]
    away_team = event["away_team"]
    home_odds = event["home_odds"]
    away_odds = event["away_odds"]

    # Look up teams
    home_info = search_team(home_team)
    away_info = search_team(away_team)

    home_id = home_info.get("id") if home_info else None
    away_id = away_info.get("id") if away_info else None

    # Fetch match history
    home_matches = get_team_matches(home_id) if home_id else []
    away_matches = get_team_matches(away_id) if away_id else []
    h2h = get_head_to_head(home_id, away_id) if home_id and away_id else []

    home_stats = _form_stats(home_matches, home_id)
    away_stats = _form_stats(away_matches, away_id)

    # Poisson expected goals
    home_xg = home_stats["attack"] * away_stats["defense"] * LEAGUE_AVG_GOALS * HOME_ADVANTAGE
    away_xg = away_stats["attack"] * home_stats["defense"] * LEAGUE_AVG_GOALS

    home_xg = round(max(0.2, home_xg), 2)
    away_xg = round(max(0.2, away_xg), 2)

    grid = _scoreline_grid(home_xg, away_xg)
    h2h_adj = _h2h_adjustment(h2h, home_id) if home_id else 0.0

    home_win_prob = min(0.95, max(0.05, grid["home_win"] + h2h_adj))
    away_win_prob = min(0.95, max(0.05, grid["away_win"] - h2h_adj))
    draw_prob = max(0.0, 1 - home_win_prob - away_win_prob)

    # Value detection
    home_value = detect_value(home_win_prob, home_odds)
    away_value = detect_value(away_win_prob, away_odds)

    if home_win_prob >= away_win_prob:
        predicted_winner = home_team
        confidence = round(home_win_prob * 100, 1)
        value = home_value
    else:
        predicted_winner = away_team
        confidence = round(away_win_prob * 100, 1)
        value = away_value

    return {
        **event,
        "predicted_winner": predicted_winner,
        "confidence": confidence,
        "home_xg": home_xg,
        "away_xg": away_xg,
        "home_win_prob": round(home_win_prob * 100, 1),
        "draw_prob": round(draw_prob * 100, 1),
        "away_win_prob": round(away_win_prob * 100, 1),
        "home_form": home_stats["form"],
        "away_form": away_stats["form"],
        "top_scorelines": grid["top_scorelines"],
        "edge_pct": value["edge_pct"],
        "is_value": value["is_value"],
        "kelly_stake_pct": value["kelly_stake_pct"],
        "expected_value": value["expected_value"],
        "h2h_count": len(h2h),
        "model": "poisson",
    }
