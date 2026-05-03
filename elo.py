def calculate_elo_change(player_elo: int, opponent_elo: int, won: bool, k_factor: int = 32) -> int:
    """
    Calculates the ELO change for a single player.
    """
    expected_score = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    actual_score = 1.0 if won else 0.0
    
    change = round(k_factor * (actual_score - expected_score))
    return int(change)

def get_new_elos(p1_elo: int, p2_elo: int, p1_won: bool):
    """
    Returns (new_p1_elo, new_p2_elo, delta)
    """
    delta = calculate_elo_change(p1_elo, p2_elo, p1_won)
    # The change for p2 is roughly the inverse of p1
    # For a zero-sum feeling, we calculate both
    p1_delta = calculate_elo_change(p1_elo, p2_elo, p1_won)
    p2_delta = calculate_elo_change(p2_elo, p1_elo, not p1_won)
    
    return p1_elo + p1_delta, p2_elo + p2_delta, abs(p1_delta)
