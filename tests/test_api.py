import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch
from app import app
from db import init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        with app.app_context():
            init_db()
        yield c


def test_index_returns_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"VANTAGE" in res.data


def test_unknown_sport_returns_400(client):
    res = client.get("/api/predictions/badminton")
    assert res.status_code == 400
    assert b"Unknown sport" in res.data


def test_stats_returns_expected_keys(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.get_json()
    for key in ("wins", "losses", "total_profit", "roi", "model_accuracy"):
        assert key in data


def test_history_returns_list(client):
    res = client.get("/api/history")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_get_bets_returns_list(client):
    res = client.get("/api/bets")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_post_bet_missing_fields_returns_400(client):
    res = client.post("/api/bets", json={"sport": "nba"})
    assert res.status_code == 400


def test_post_bet_valid(client):
    res = client.post("/api/bets", json={
        "sport": "tennis",
        "home_team": "Emma Raducanu",
        "away_team": "Donna Vekic",
        "predicted_winner": "Emma Raducanu",
        "bet_on": "Emma Raducanu",
        "odds": -150,
        "stake": 50,
        "commence_time": "2026-06-14T12:30:00Z",
    })
    assert res.status_code == 201
    assert "id" in res.get_json()


def test_settle_bet_invalid_result(client):
    res = client.patch("/api/bets/1", json={"result": "push"})
    assert res.status_code == 400


def test_settle_bet_not_found(client):
    res = client.patch("/api/bets/9999", json={"result": "win"})
    assert res.status_code == 404


def test_tennis_matches_returns_list(client):
    with patch("app.get_tennis_matches", return_value=[]):
        res = client.get("/api/tennis-matches")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_scores_unknown_sport_returns_400(client):
    res = client.get("/api/scores/badminton")
    assert res.status_code == 400
