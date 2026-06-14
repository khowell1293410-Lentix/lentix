def analyze_live_signal(match: dict) -> dict:
    """
    Detect potential live bet windows based on match state.
    Returns a signal with reason and recommended side.
    """
    no_signal = {"signal": False, "reason": None, "bet_on": None, "strength": None}

    if not match.get("is_live"):
        return no_signal

    sets1 = match.get("sets1", [])
    sets2 = match.get("sets2", [])
    p1 = match.get("player1", "")
    p2 = match.get("player2", "")
    seed1 = match.get("player1_seed")
    seed2 = match.get("player2_seed")

    if len(sets1) == 0 and len(sets2) == 0:
        return no_signal

    sets_played = len(sets1)
    p1_sets_won = sum(1 for i in range(sets_played) if sets1[i] > sets2[i])
    p2_sets_won = sets_played - p1_sets_won

    # Determine favorite by seed (lower seed = better ranked)
    if seed1 and seed2:
        favorite = p1 if seed1 < seed2 else p2
        underdog = p2 if seed1 < seed2 else p1
        fav_sets_won = p1_sets_won if seed1 < seed2 else p2_sets_won
        dog_sets_won = p2_sets_won if seed1 < seed2 else p1_sets_won
    else:
        favorite = underdog = None
        fav_sets_won = dog_sets_won = 0

    signals = []

    # --- Signal: Favorite down a set (odds drift = value on fav) ---
    if favorite and dog_sets_won > fav_sets_won:
        signals.append({
            "reason": f"{favorite} (fav) is down — odds have drifted, potential value",
            "bet_on": favorite,
            "strength": "high",
        })

    # --- Signal: Underdog just took a set off the favorite (momentum) ---
    if favorite and sets_played >= 1:
        last_s1 = sets1[-1] if sets1 else 0
        last_s2 = sets2[-1] if sets2 else 0
        last_set_winner = p1 if last_s1 > last_s2 else p2
        if last_set_winner == underdog and sets_played < 3:
            signals.append({
                "reason": f"{underdog} just took a set — live odds may overcorrect",
                "bet_on": favorite,
                "strength": "medium",
            })

    # --- Signal: Deciding set, bet on set momentum winner ---
    if p1_sets_won == 1 and p2_sets_won == 1 and sets_played == 2:
        last_s1 = sets1[-1] if sets1 else 0
        last_s2 = sets2[-1] if sets2 else 0
        momentum_player = p1 if last_s1 > last_s2 else p2
        signals.append({
            "reason": f"Deciding set — {momentum_player} has set momentum",
            "bet_on": momentum_player,
            "strength": "medium",
        })

    # --- Signal: Dominant set played (bagel or breadstick = hot streak) ---
    if sets_played >= 1:
        last_s1 = sets1[-1] if sets1 else 0
        last_s2 = sets2[-1] if sets2 else 0
        if (last_s1 == 6 and last_s2 <= 1) or (last_s2 == 6 and last_s1 <= 1):
            hot_player = p1 if last_s1 > last_s2 else p2
            signals.append({
                "reason": f"{hot_player} just dominated a set ({last_s1}-{last_s2}) — on fire",
                "bet_on": hot_player,
                "strength": "high",
            })

    # --- Signal: First set close (6-7 or 7-6 tiebreak) — tight match, take underdog ---
    if sets_played >= 1:
        s1, s2 = sets1[0], sets2[0]
        if (s1 == 7 and s2 == 6) or (s1 == 6 and s2 == 7):
            tiebreak_winner = p1 if s1 > s2 else p2
            if tiebreak_winner == underdog:
                signals.append({
                    "reason": f"{underdog} won first set tiebreak — closer match than seeding suggests",
                    "bet_on": underdog,
                    "strength": "medium",
                })

    if not signals:
        return no_signal

    best = max(signals, key=lambda s: {"high": 2, "medium": 1}.get(s["strength"], 0))
    return {"signal": True, **best}
