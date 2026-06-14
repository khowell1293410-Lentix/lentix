from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
from requests.exceptions import HTTPError
from predictor import get_predictions, get_value_bets
from odds_client import get_events, get_player_props, get_game_props, SPORT_KEYS
from db import init_db, save_predictions, get_history, place_bet, settle_bet, get_bets, get_stats
from data_sources.espn import get_match_squads, get_live_scores, get_tennis_matches

load_dotenv()

app = Flask(__name__)

SPORTS = ["nba", "nfl", "soccer", "ufc", "boxing", "world_cup", "tennis"]


@app.before_request
def setup():
    init_db()


app.before_request_funcs.setdefault(None, [])


def _api_error(e: Exception):
    msg = str(e)
    if "401" in msg:
        return jsonify({"error": "API quota reached or key invalid. Get a new key at the-odds-api.com"}), 503
    if "404" in msg:
        return jsonify({"error": "No odds available for this sport right now (off-season or no games scheduled)"}), 404
    return jsonify({"error": msg}), 500


@app.route("/")
def index():
    return render_template("index.html", sports=SPORTS)


@app.route("/api/predictions/<sport>")
def predictions(sport: str):
    if sport not in SPORTS:
        return jsonify({"error": "Unknown sport"}), 400
    try:
        data = get_predictions(sport)
        return jsonify(data)
    except Exception as e:
        return _api_error(e)


@app.route("/api/refresh/<sport>", methods=["POST"])
def refresh(sport: str):
    if sport not in SPORTS:
        return jsonify({"error": "Unknown sport"}), 400
    try:
        data = get_predictions(sport)
        save_predictions(data)
        return jsonify({"saved": len(data), "predictions": data})
    except Exception as e:
        return _api_error(e)


@app.route("/api/player-props/<sport>")
def player_props(sport: str):
    if sport not in SPORTS:
        return jsonify({"error": "Unknown sport"}), 400
    try:
        events = get_events(sport)
        result = []
        for event in events:
            props = get_player_props(event["id"])
            if props:
                result.append({
                    "home_team": event["home_team"],
                    "away_team": event["away_team"],
                    "commence_time": event["commence_time"],
                    "props": props,
                })
        return jsonify(result)
    except Exception as e:
        return _api_error(e)


@app.route("/api/game-props/<sport>")
def game_props(sport: str):
    if sport not in SPORTS:
        return jsonify({"error": "Unknown sport"}), 400
    try:
        events = get_events(sport)
        sport_key = SPORT_KEYS.get(sport, "")
        result = []
        for event in events:
            props = get_game_props(event["id"], sport_key)
            if props:
                result.append({
                    "home_team": event["home_team"],
                    "away_team": event["away_team"],
                    "commence_time": event["commence_time"],
                    "props": props,
                })
        return jsonify(result)
    except Exception as e:
        return _api_error(e)


@app.route("/api/edge-bets/<sport>")
def edge_bets(sport: str):
    if sport not in SPORTS:
        return jsonify({"error": "Unknown sport"}), 400
    try:
        return jsonify(get_value_bets(sport))
    except Exception as e:
        return _api_error(e)


@app.route("/api/bets", methods=["GET", "POST"])
def bets():
    if request.method == "POST":
        data = request.get_json()
        required = {"sport", "home_team", "away_team", "predicted_winner", "bet_on", "odds", "stake", "commence_time"}
        if not required.issubset(data or {}):
            return jsonify({"error": "Missing required fields"}), 400
        bet_id = place_bet(data)
        return jsonify({"id": bet_id}), 201
    return jsonify(get_bets())


@app.route("/api/bets/<int:bet_id>", methods=["PATCH"])
def settle(bet_id: int):
    data = request.get_json()
    result = data.get("result") if data else None
    if result not in ("win", "loss"):
        return jsonify({"error": "result must be 'win' or 'loss'"}), 400
    try:
        outcome = settle_bet(bet_id, result)
        return jsonify(outcome)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/stats")
def stats():
    return jsonify(get_stats())


@app.route("/api/scores/<sport>")
def scores(sport: str):
    if sport not in SPORTS:
        return jsonify({"error": "Unknown sport"}), 400
    try:
        return jsonify(get_live_scores(sport))
    except Exception as e:
        return _api_error(e)


@app.route("/api/squad")
def squad():
    home = request.args.get("home", "")
    away = request.args.get("away", "")
    if not home or not away:
        return jsonify({"error": "Provide home and away team names"}), 400
    try:
        return jsonify(get_match_squads(home, away))
    except Exception as e:
        return _api_error(e)


@app.route("/api/tennis-matches")
def tennis_matches_route():
    try:
        return jsonify(get_tennis_matches())
    except Exception as e:
        return _api_error(e)


@app.route("/api/history")
def history():
    return jsonify(get_history())


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
