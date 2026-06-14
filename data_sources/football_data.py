import os
import json
import requests
from datetime import datetime, timedelta
from db import get_conn

BASE_URL = "https://api.football-data.org/v4"
CACHE_TTL_HOURS = 6


def _headers():
    return {"X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY", "")}


def _get_cache(key: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT data, fetched_at FROM team_stats WHERE team_id = ? AND sport = 'football_data'",
            (key,)
        ).fetchone()
    if not row:
        return None
    fetched = datetime.fromisoformat(row["fetched_at"])
    if datetime.utcnow() - fetched > timedelta(hours=CACHE_TTL_HOURS):
        return None
    return json.loads(row["data"])


def _set_cache(key: str, data: dict):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO team_stats (team_id, sport, data, fetched_at)
            VALUES (?, 'football_data', ?, ?)
            ON CONFLICT(team_id, sport) DO UPDATE SET data=excluded.data, fetched_at=excluded.fetched_at
        """, (key, json.dumps(data), now))


def _get(path: str) -> dict:
    resp = requests.get(f"{BASE_URL}{path}", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_team_matches(team_id: int, limit: int = 10) -> list[dict]:
    key = f"team_matches_{team_id}_{limit}"
    cached = _get_cache(key)
    if cached:
        return cached
    try:
        data = _get(f"/teams/{team_id}/matches?status=FINISHED&limit={limit}")
        matches = data.get("matches", [])
        _set_cache(key, matches)
        return matches
    except Exception:
        return []


def get_head_to_head(team1_id: int, team2_id: int, limit: int = 10) -> list[dict]:
    key = f"h2h_{min(team1_id, team2_id)}_{max(team1_id, team2_id)}"
    cached = _get_cache(key)
    if cached:
        return cached
    try:
        data = _get(f"/teams/{team1_id}/matches?status=FINISHED&limit=50")
        matches = [
            m for m in data.get("matches", [])
            if m.get("homeTeam", {}).get("id") == team2_id
            or m.get("awayTeam", {}).get("id") == team2_id
        ][:limit]
        _set_cache(key, matches)
        return matches
    except Exception:
        return []


def search_team(name: str) -> dict | None:
    """Fuzzy search for a team by name across all competitions."""
    key = f"team_search_{name.lower().replace(' ', '_')}"
    cached = _get_cache(key)
    if cached:
        return cached
    try:
        data = _get(f"/teams?name={requests.utils.quote(name)}")
        teams = data.get("teams", [])
        if teams:
            _set_cache(key, teams[0])
            return teams[0]
    except Exception:
        pass
    return None


def get_competition_teams(competition_code: str) -> list[dict]:
    key = f"competition_teams_{competition_code}"
    cached = _get_cache(key)
    if cached:
        return cached
    try:
        data = _get(f"/competitions/{competition_code}/teams")
        teams = data.get("teams", [])
        _set_cache(key, teams)
        return teams
    except Exception:
        return []
