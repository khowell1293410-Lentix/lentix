import requests

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

LEAGUE_MAP = {
    "world_cup": "soccer/fifa.world",
    "soccer": "soccer/usa.1",
    "nba": "basketball/nba",
    "ufc": "mma/ufc",
    "boxing": "boxing/boxing",
}

ESPN_TEAM_IDS = {
    "Haiti": ("soccer/fifa.world", "2654"),
    "Scotland": ("soccer/fifa.world", "580"),
    "Brazil": ("soccer/fifa.world", "6"),
    "Morocco": ("soccer/fifa.world", "131"),
    "Australia": ("soccer/fifa.world", "14"),
    "Turkey": ("soccer/fifa.world", "154"),
    "Germany": ("soccer/fifa.world", "75"),
    "Netherlands": ("soccer/fifa.world", "128"),
    "France": ("soccer/fifa.world", "66"),
    "Argentina": ("soccer/fifa.world", "7"),
    "England": ("soccer/fifa.world", "448"),
    "Spain": ("soccer/fifa.world", "157"),
    "Portugal": ("soccer/fifa.world", "165"),
    "USA": ("soccer/fifa.world", "564"),
}


def get_team_roster(team_name: str) -> dict:
    entry = ESPN_TEAM_IDS.get(team_name)
    if not entry:
        return {"team": team_name, "players": [], "unavailable": []}

    league, team_id = entry
    try:
        r = requests.get(
            f"{ESPN_BASE}/{league}/teams/{team_id}/roster",
            timeout=10
        )
        r.raise_for_status()
        athletes = r.json().get("athletes", [])
    except Exception:
        return {"team": team_name, "players": [], "unavailable": []}

    players = []
    unavailable = []
    for a in athletes:
        status = a.get("status", {})
        status_name = status.get("name", "Active")
        player = {
            "name": a.get("fullName", "Unknown"),
            "position": a.get("position", {}).get("abbreviation", "?"),
            "status": status_name,
            "jersey": a.get("jersey", ""),
        }
        players.append(player)
        if status_name != "Active":
            unavailable.append(player)

    return {
        "team": team_name,
        "total": len(players),
        "players": players,
        "unavailable": unavailable,
        "all_clear": len(unavailable) == 0,
    }


def get_live_scores(sport: str) -> list[dict]:
    league = LEAGUE_MAP.get(sport)
    if not league:
        return []
    try:
        r = requests.get(f"{ESPN_BASE}/{league}/scoreboard", timeout=10)
        r.raise_for_status()
        events = r.json().get("events", [])
    except Exception:
        return []

    scores = []
    for e in events:
        comp = e.get("competitions", [{}])[0]
        status = comp.get("status", {})
        state = status.get("type", {}).get("state", "pre")
        detail = status.get("displayClock", "")
        period = status.get("period", 0)
        period_label = status.get("type", {}).get("shortDetail", "")

        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})

        scores.append({
            "home_team": home.get("team", {}).get("displayName", ""),
            "away_team": away.get("team", {}).get("displayName", ""),
            "home_score": home.get("score", "0"),
            "away_score": away.get("score", "0"),
            "state": state,
            "clock": detail,
            "period": period,
            "period_label": period_label,
            "is_live": state == "in",
            "is_final": state == "post",
        })
    return scores


def get_tennis_matches() -> list[dict]:
    matches = []
    for league, tour in [("tennis/atp", "ATP"), ("tennis/wta", "WTA")]:
        try:
            r = requests.get(f"{ESPN_BASE}/{league}/scoreboard", timeout=10)
            r.raise_for_status()
        except Exception:
            continue
        for event in r.json().get("events", []):
            tournament = event.get("name", "")
            for grp in event.get("groupings", []):
                for comp in grp.get("competitions", []):
                    comps = comp.get("competitors", [])
                    if len(comps) < 2:
                        continue
                    status = comp.get("status", {})
                    state = status.get("type", {}).get("state", "pre")
                    period = status.get("period", 0)
                    clock = status.get("displayClock", "")
                    detail = status.get("type", {}).get("shortDetail", "")

                    def player_name(c):
                        return c.get("athlete", {}).get("displayName") or c.get("team", {}).get("displayName", "TBD")

                    def set_scores(c):
                        return [int(ls.get("value", 0)) for ls in c.get("linescores", [])]

                    p1, p2 = comps[0], comps[1]
                    matches.append({
                        "id": comp.get("id", ""),
                        "tour": tour,
                        "tournament": tournament,
                        "round": comp.get("round", {}).get("displayName", ""),
                        "player1": player_name(p1),
                        "player2": player_name(p2),
                        "player1_seed": p1.get("curatedRank", {}).get("current"),
                        "player2_seed": p2.get("curatedRank", {}).get("current"),
                        "sets1": set_scores(p1),
                        "sets2": set_scores(p2),
                        "state": state,
                        "period": period,
                        "clock": clock,
                        "detail": detail,
                        "is_live": state == "in",
                        "is_final": state == "post",
                        "winner": player_name(p1) if p1.get("winner") else (player_name(p2) if p2.get("winner") else None),
                    })
    matches.sort(key=lambda m: (0 if m["is_live"] else 1 if not m["is_final"] else 2))
    return matches


def get_match_squads(home_team: str, away_team: str) -> dict:
    home = get_team_roster(home_team)
    away = get_team_roster(away_team)
    flags = []
    for p in home["unavailable"] + away["unavailable"]:
        flags.append(f"{p['name']} ({p['team'] if 'team' in p else ''}) — {p['status']}")
    return {
        "home": home,
        "away": away,
        "injury_flags": flags,
        "clean_bill": len(flags) == 0,
    }
