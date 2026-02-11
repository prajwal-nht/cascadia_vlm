"""
Main Cascadia Scoring Engine
Combines VLM analysis with rule-based scoring
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import json

from vlm_analyzer import PlayerBoard
from scoring_rules import CascadiaScoringRules, AnimalPosition, HabitatTile


@dataclass
class PlayerScore:
    """Complete score breakdown for one player"""
    player_id: int
    animal_scores: Dict[str, int]
    animal_explanations: Dict[str, str]
    habitat_scores: Dict[str, int]
    habitat_total: int
    nature_tokens: int
    majority_bonuses: Dict[str, int]
    total_score: int


class CascadiaScorer:
    """Main scoring engine for Cascadia game"""
    
    def __init__(self):
        self.rules = CascadiaScoringRules()
    
    def score_game(self, player_boards: List[PlayerBoard], 
                   scoring_cards: Dict[str, Dict]) -> List[PlayerScore]:
        """
        Score complete game for all players
        
        Args:
            player_boards: List of PlayerBoard objects from VLM analysis
            scoring_cards: Scoring rules from card analysis
            
        Returns:
            List of PlayerScore objects with complete breakdown
        """
        player_scores = []
        
        for board in player_boards:
            score = self._score_player(board, scoring_cards)
            player_scores.append(score)
        
        # Calculate majority bonuses
        player_scores = self._calculate_majority_bonuses(player_scores)
        
        return player_scores
    
    def _score_player(self, board: PlayerBoard, 
                     scoring_cards: Dict[str, Dict]) -> PlayerScore:
        """Score individual player board using VLM patterns"""
        
        animal_scores = {}
        animal_explanations = {}
        patterns = board.wildlife_patterns
        
        # 1. Bears (Pairs)
        # Default card A: 4 pts per pair
        bear_pairs = patterns.get('bear_pairs', 0)
        pair_val = 4  # Fallback
        if 'bear' in scoring_cards and 'pair' in scoring_cards['bear'].get('scoring', {}):
            pair_val = scoring_cards['bear']['scoring']['pair']
        animal_scores['bear'] = bear_pairs * pair_val
        animal_explanations['bear'] = f"{bear_pairs} pairs @ {pair_val}pts"
        
        # 2. Elk (Lines)
        # Default card A: 1=2, 2=5, 3=9, 4+=13
        elk_lines = patterns.get('elk_lines', [])
        elk_total = 0
        elk_rules = scoring_cards.get('elk', {}).get('scoring', {'1': 2, '2': 5, '3': 9, '4+': 13})
        for length in elk_lines:
            pts = 0
            if str(length) in elk_rules:
                pts = elk_rules[str(length)]
            elif length >= 4:
                pts = elk_rules.get('4+', 13)
            elk_total += pts
        animal_scores['elk'] = elk_total
        animal_explanations['elk'] = f"Lines: {elk_lines}"
        
        # 3. Salmon (Runs)
        # Default card A: 1=2, 2=5, 3=8, 4=11, 5+=14 (checking rules, usually run scoring is length based)
        # VLM prompt returns list of run lengths
        salmon_runs = patterns.get('salmon_runs', [])
        salmon_total = 0
        salmon_rules = scoring_cards.get('salmon', {}).get('scoring', {}) # Expect {"1": 2, "2": 5...}
        for length in salmon_runs:
            pts = 0 
            # Logic similar to elk but specific to salmon rules provided
            if str(length) in salmon_rules:
                pts = salmon_rules[str(length)]
            elif length >= 5: # Cap often at 5
                pts = salmon_rules.get('5+', 0)
            salmon_total += pts
        animal_scores['salmon'] = salmon_total
        animal_explanations['salmon'] = f"Runs: {salmon_runs}"

        # 4. Hawks (Isolated)
        isolated_hawks = patterns.get('isolated_hawks', 0)
        # Default 2-3 pts depending on count, or flat? Card A is usually: 1=2, 2=5, 3=8... based on total count of isolated hawks
        # Wait, Hawk A is "Count number of isolated hawks... score based on table"
        # Table: 1->2, 2->5, 3->8, 4->11, 5->14, 6->18, 7->22, 8+->26
        # Need to check how 'scoring' is returned.
        # Assuming table lookup based on TOTAL count
        hawk_rules = scoring_cards.get('hawk', {}).get('scoring', {})
        hawk_pts = 0
        count_key = str(isolated_hawks)
        if count_key in hawk_rules:
            hawk_pts = hawk_rules[count_key]
        elif isolated_hawks > 0:
            # Fallback or max value
            keys = [k for k in hawk_rules.keys() if k.isdigit()]
            if keys:
                max_k = max(int(k) for k in keys)
                if isolated_hawks >= max_k:
                    hawk_pts = hawk_rules[str(max_k)] # approximate max cap
        animal_scores['hawk'] = hawk_pts
        animal_explanations['hawk'] = f"{isolated_hawks} isolated"

        # 5. Fox (Neighbors)
        # List of [unique_count, unique_count...]
        fox_neighbors = patterns.get('fox_neighbors', [])
        fox_total = 0
        fox_rules = scoring_cards.get('fox', {}).get('scoring', {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5})
        for count in fox_neighbors:
            pts = fox_rules.get(str(count), count) # Default to 1pt per neighbor if logic missing
            fox_total += pts
        animal_scores['fox'] = fox_total
        animal_explanations['fox'] = f"Neighbors: {fox_neighbors}"
        
        # Score Habitats (Largest Contiguous)
        habitat_scores = board.largest_habitats
        habitat_total = sum(habitat_scores.values())
        
        # Nature Tokens (1 pt each)
        nature_score = board.nature_tokens
        
        # Calculate total (before majority bonuses)
        total = sum(animal_scores.values()) + habitat_total + nature_score
        
        return PlayerScore(
            player_id=board.player_id,
            animal_scores=animal_scores,
            animal_explanations=animal_explanations,
            habitat_scores=habitat_scores,
            habitat_total=habitat_total,
            nature_tokens=board.nature_tokens,
            majority_bonuses={},  # Calculated later
            total_score=total
        )
    
    # Removed _extract_animal_positions and _extract_habitat_tiles as they are no longer needed

    
    def _calculate_majority_bonuses(self, 
                                   player_scores: List[PlayerScore]) -> List[PlayerScore]:
        """Calculate majority bonuses for habitat types"""
        num_players = len(player_scores)
        terrain_types = ['mountain', 'forest', 'prairie', 'wetland', 'river']
        
        for terrain in terrain_types:
            # Get scores for this terrain
            scores = [(ps.player_id, ps.habitat_scores.get(terrain, 0)) 
                     for ps in player_scores]
            scores.sort(key=lambda x: x[1], reverse=True)
            
            if num_players == 2:
                # 2 player: winner gets 2, tie = 1 each
                if scores[0][1] > scores[1][1]:
                    self._add_bonus(player_scores, scores[0][0], terrain, 2)
                elif scores[0][1] == scores[1][1] and scores[0][1] > 0:
                    self._add_bonus(player_scores, scores[0][0], terrain, 1)
                    self._add_bonus(player_scores, scores[1][0], terrain, 1)
            else:
                # 3-4 players
                # Check for tie for first place
                max_score = scores[0][1]
                if max_score == 0: continue # No points if 0 size

                tied_for_first = [s for s in scores if s[1] == max_score]
                
                if len(tied_for_first) == 1:
                    # Clear winner - 3 pts
                    self._add_bonus(player_scores, tied_for_first[0][0], terrain, 3)
                    
                    # Check for second place (only if another player exists)
                    if len(scores) > 1:
                        second_score = scores[1][1]
                        if second_score > 0:
                            tied_for_second = [s for s in scores if s[1] == second_score]
                            if len(tied_for_second) == 1:
                                # Clear second - 1 pt
                                self._add_bonus(player_scores, tied_for_second[0][0], terrain, 1)
                            # Else: tie for second = 0 pts
                        
                elif len(tied_for_first) == 2:
                    # Two way tie for first - 2 pts each
                    for winner in tied_for_first:
                        self._add_bonus(player_scores, winner[0], terrain, 2)
                else:
                    # 3+ way tie for first - 1 pt each
                    for winner in tied_for_first:
                         self._add_bonus(player_scores, winner[0], terrain, 1)
        
        # Recalculate totals
        for ps in player_scores:
            ps.total_score = (sum(ps.animal_scores.values()) + 
                            ps.habitat_total + 
                            sum(ps.majority_bonuses.values()) +
                            ps.nature_tokens)
        
        return player_scores
    
    def _add_bonus(self, player_scores: List[PlayerScore], 
                   player_id: int, terrain: str, bonus: int):
        """Add majority bonus to player"""
        for ps in player_scores:
            if ps.player_id == player_id:
                ps.majority_bonuses[terrain] = bonus
                break
    
    def determine_winner(self, player_scores: List[PlayerScore]) -> Tuple[int, str]:
        """
        Determine game winner
        
        Returns:
            (winner_player_id, explanation)
        """
        sorted_scores = sorted(player_scores, 
                              key=lambda x: (x.total_score, x.nature_tokens), 
                              reverse=True)
        
        winner = sorted_scores[0]
        
        if len(sorted_scores) > 1 and sorted_scores[0].total_score == sorted_scores[1].total_score:
            if sorted_scores[0].nature_tokens == sorted_scores[1].nature_tokens:
                return winner.player_id, f"Player {winner.player_id} wins (tied, victory shared)"
            else:
                return winner.player_id, f"Player {winner.player_id} wins on tiebreaker (nature tokens)"
        
        return winner.player_id, f"Player {winner.player_id} wins with {winner.total_score} points"
    
    def format_results(self, player_scores: List[PlayerScore]) -> Dict:
        """Format results as structured JSON"""
        winner_id, winner_explanation = self.determine_winner(player_scores)
        
        return {
            "winner": {
                "player_id": winner_id,
                "explanation": winner_explanation
            },
            "players": [asdict(ps) for ps in player_scores],
            "summary": {
                f"player_{ps.player_id}": {
                    "total": ps.total_score,
                    "animals": sum(ps.animal_scores.values()),
                    "habitats": ps.habitat_total,
                    "bonuses": sum(ps.majority_bonuses.values())
                }
                for ps in player_scores
            }
        }
