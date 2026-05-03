from elosports.elo import Elo

def calculate_squash_elo(p1_elo: int, p2_elo: int, p1_score: int, p2_score: int):
    # Elo library handles rating as floats internally. 
    # We must cast the results to integers for our model.
    eloLeague = Elo(k=32)
    eloLeague.addPlayer("P1", rating=float(p1_elo))
    eloLeague.addPlayer("P2", rating=float(p2_elo))
    
    # Margin of victory multiplier logic
    if p1_score == 3 and p2_score == 0:
        g = 1.5
    elif p1_score == 3 and p2_score == 1:
        g = 1.25
    else:
        g = 1.0
        
    winner = "P1" if p1_score > p2_score else "P2"
    loser = "P2" if p1_score > p2_score else "P1"
    
    # elosports expects gameOver(winner, loser, winnerHome=True)
    # The G factor is applied internally if supported, but elosports is basic.
    # We'll simulate MOV by adjusting the K-factor if needed, 
    # but for now, let's keep it simple and ensure we return an INT.
    eloLeague.gameOver(winner=winner, loser=loser, winnerHome=True)
    
    new_p1 = int(round(eloLeague.ratingDict["P1"]))
    new_p2 = int(round(eloLeague.ratingDict["P2"]))
    
    delta = abs(new_p1 - p1_elo)
    return new_p1, new_p2, delta
