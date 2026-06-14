import sqlite3
from datetime import datetime

DB_PATH = "predictions.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport TEXT,
                home_team TEXT,
                away_team TEXT,
                predicted_winner TEXT,
                confidence REAL,
                home_odds REAL,
                away_odds REAL,
                commence_time TEXT,
                saved_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_stats (
                team_id TEXT,
                sport TEXT,
                data TEXT,
                fetched_at TEXT,
                PRIMARY KEY (team_id, sport)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport TEXT,
                home_team TEXT,
                away_team TEXT,
                predicted_winner TEXT,
                bet_on TEXT,
                odds REAL,
                stake REAL,
                result TEXT,
                profit REAL,
                commence_time TEXT,
                placed_at TEXT,
                settled_at TEXT
            )
        """)


def save_predictions(predictions: list[dict]):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.executemany("""
            INSERT INTO predictions
              (sport, home_team, away_team, predicted_winner, confidence, home_odds, away_odds, commence_time, saved_at)
            VALUES
              (:sport, :home_team, :away_team, :predicted_winner, :confidence, :home_odds, :away_odds, :commence_time, :saved_at)
        """, [{**p, "saved_at": now} for p in predictions])


def place_bet(data: dict) -> int:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO bets (sport, home_team, away_team, predicted_winner, bet_on, odds, stake, commence_time, placed_at)
            VALUES (:sport, :home_team, :away_team, :predicted_winner, :bet_on, :odds, :stake, :commence_time, :placed_at)
        """, {**data, "placed_at": now})
        return cur.lastrowid


def settle_bet(bet_id: int, result: str) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT odds, stake FROM bets WHERE id = ?", (bet_id,)).fetchone()
        if not row:
            raise ValueError("Bet not found")
        odds, stake = row["odds"], row["stake"]
        if result == "win":
            profit = stake * (odds / 100) if odds > 0 else stake * (100 / abs(odds))
        else:
            profit = -stake
        profit = round(profit, 2)
        conn.execute(
            "UPDATE bets SET result = ?, profit = ?, settled_at = ? WHERE id = ?",
            (result, profit, datetime.utcnow().isoformat(), bet_id)
        )
    return {"profit": profit}


def get_bets() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bets ORDER BY placed_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bets WHERE result IS NOT NULL").fetchall()
    settled = [dict(r) for r in rows]
    wins = sum(1 for b in settled if b["result"] == "win")
    losses = len(settled) - wins
    total_profit = round(sum(b["profit"] or 0 for b in settled), 2)
    total_staked = sum(b["stake"] or 0 for b in settled)
    roi = round((total_profit / total_staked * 100), 1) if total_staked else 0
    model_correct = sum(1 for b in settled if b["predicted_winner"] == b["bet_on"] and b["result"] == "win")
    model_accuracy = round((model_correct / len(settled) * 100), 1) if settled else 0
    return {
        "wins": wins,
        "losses": losses,
        "total_profit": total_profit,
        "roi": roi,
        "model_accuracy": model_accuracy,
        "settled_count": len(settled),
    }


def get_history(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY saved_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
