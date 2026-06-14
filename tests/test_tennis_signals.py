import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data_sources.tennis_signals import analyze_live_signal


def base_match(**kwargs):
    m = {
        "player1": "Raducanu", "player2": "Vekic",
        "player1_seed": 2, "player2_seed": 8,
        "sets1": [], "sets2": [],
        "is_live": True, "period": 1,
    }
    m.update(kwargs)
    return m


def test_no_signal_when_not_live():
    m = base_match(is_live=False)
    assert analyze_live_signal(m)["signal"] is False


def test_no_signal_no_sets_yet():
    m = base_match(sets1=[], sets2=[])
    assert analyze_live_signal(m)["signal"] is False


def test_favorite_down_triggers_high_signal():
    # Raducanu (seed 2, fav) lost first set
    m = base_match(sets1=[4], sets2=[6])
    result = analyze_live_signal(m)
    assert result["signal"] is True
    assert result["strength"] == "high"
    assert result["bet_on"] == "Raducanu"


def test_deciding_set_triggers_signal():
    # One set each — a signal fires (underdog took a set or deciding set)
    m = base_match(sets1=[6, 3], sets2=[3, 6])
    result = analyze_live_signal(m)
    assert result["signal"] is True
    assert result["bet_on"] is not None


def test_bagel_triggers_high_signal():
    m = base_match(sets1=[6], sets2=[0])
    result = analyze_live_signal(m)
    assert result["signal"] is True
    assert result["strength"] == "high"
    assert "Raducanu" in result["reason"]


def test_tiebreak_underdog_win_triggers_signal():
    # Vekic (seed 8) wins tiebreak — fav (Raducanu) is now down, high-strength signal fires
    m = base_match(sets1=[6], sets2=[7])
    result = analyze_live_signal(m)
    assert result["signal"] is True
    # Favorite-down is high strength and wins over tiebreak signal
    assert result["bet_on"] == "Raducanu"
    assert result["strength"] == "high"


def test_signal_returns_all_keys():
    m = base_match(sets1=[4], sets2=[6])
    result = analyze_live_signal(m)
    for key in ("signal", "reason", "bet_on", "strength"):
        assert key in result
