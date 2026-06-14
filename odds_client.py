import os
import requests

BASE_URL = "https://api.the-odds-api.com/v4"

SPORT_KEYS = {
    "nba": "basketball_nba",
    "nfl": "americanfootball_nfl",
    "soccer": "soccer_usa_mls",
    "ufc": "mma_mixed_martial_arts",
    "boxing": "boxing_boxing",
    "world_cup": "soccer_fifa_world_cup",
    "intl": "soccer_conmebol_copa_america",  # covers CONCACAF, friendlies, qualifiers
    "tennis": "tennis_wta_queens_club_champ",
}


def get_events(sport: str) -> list[dict]:
    api_key = os.getenv("ODDS_API_KEY")
    sport_key = SPORT_KEYS.get(sport)
    if not sport_key:
        return []

    url = f"{BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    raw = response.json()

    events = []
    for game in raw:
        home = game.get("home_team")
        away = game.get("away_team")
        commence = game.get("commence_time")

        home_odds = None
        away_odds = None
        home_spread = None
        away_spread = None
        home_spread_odds = None
        away_spread_odds = None
        total_over = None
        total_under = None
        total_points = None

        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                key = market.get("key")
                outcomes = market.get("outcomes", [])
                if key == "h2h" and home_odds is None:
                    for o in outcomes:
                        if o["name"] == home:
                            home_odds = o["price"]
                        elif o["name"] == away:
                            away_odds = o["price"]
                elif key == "spreads" and home_spread is None:
                    for o in outcomes:
                        if o["name"] == home:
                            home_spread = o.get("point")
                            home_spread_odds = o["price"]
                        elif o["name"] == away:
                            away_spread = o.get("point")
                            away_spread_odds = o["price"]
                elif key == "totals" and total_over is None:
                    for o in outcomes:
                        if o["name"] == "Over":
                            total_over = o["price"]
                            total_points = o.get("point")
                        elif o["name"] == "Under":
                            total_under = o["price"]

        if home_odds is not None and away_odds is not None:
            events.append({
                "id": game.get("id"),
                "sport": sport,
                "home_team": home,
                "away_team": away,
                "commence_time": commence,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "home_spread": home_spread,
                "home_spread_odds": home_spread_odds,
                "away_spread": away_spread,
                "away_spread_odds": away_spread_odds,
                "total_points": total_points,
                "total_over_odds": total_over,
                "total_under_odds": total_under,
            })

    return events


PLAYER_PROP_MARKETS = (
    "player_points,player_rebounds,player_assists,"
    "player_threes,player_blocks,player_steals"
)

GAME_PROP_MARKETS = "alternate_spreads,alternate_totals,team_totals"

STAT_LABELS = {
    "player_points": "Points",
    "player_rebounds": "Rebounds",
    "player_assists": "Assists",
    "player_threes": "3-Pointers",
    "player_blocks": "Blocks",
    "player_steals": "Steals",
}


def _fetch_event_odds(sport_key: str, event_id: str, markets: str) -> list:
    api_key = os.getenv("ODDS_API_KEY")
    url = f"{BASE_URL}/sports/{sport_key}/events/{event_id}/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": markets,
        "oddsFormat": "american",
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get("bookmakers", [])


def get_player_props(event_id: str) -> list[dict]:
    try:
        bookmakers = _fetch_event_odds("basketball_nba", event_id, PLAYER_PROP_MARKETS)
    except Exception:
        return []

    props: dict[tuple, dict] = {}
    for bookmaker in bookmakers:
        for market in bookmaker.get("markets", []):
            stat_key = market.get("key")
            stat_label = STAT_LABELS.get(stat_key)
            if not stat_label:
                continue
            for outcome in market.get("outcomes", []):
                player = outcome.get("description") or outcome.get("name")
                side = outcome.get("name")
                line = outcome.get("point")
                price = outcome.get("price")
                key = (player, stat_key, line)
                if key not in props:
                    props[key] = {"player": player, "stat": stat_label, "line": line, "over_odds": None, "under_odds": None}
                if side == "Over":
                    props[key]["over_odds"] = price
                elif side == "Under":
                    props[key]["under_odds"] = price

    return [p for p in props.values() if p["over_odds"] and p["under_odds"]]


def get_game_props(event_id: str, sport_key: str) -> list[dict]:
    try:
        bookmakers = _fetch_event_odds(sport_key, event_id, GAME_PROP_MARKETS)
    except Exception:
        return []

    props: dict[tuple, dict] = {}
    for bookmaker in bookmakers:
        for market in bookmaker.get("markets", []):
            market_key = market.get("key")
            for outcome in market.get("outcomes", []):
                name = outcome.get("name")
                desc = outcome.get("description", name)
                line = outcome.get("point")
                price = outcome.get("price")
                label = f"{market_key.replace('_', ' ').title()}: {desc}"
                key = (label, line)
                if key not in props:
                    props[key] = {"description": label, "line": line, "over_odds": None, "under_odds": None}
                side = outcome.get("name")
                if side in ("Over", "Yes"):
                    props[key]["over_odds"] = price
                elif side in ("Under", "No"):
                    props[key]["under_odds"] = price

    return list(props.values())
