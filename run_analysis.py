"""
Main Entry Point for Cascadia VLM Challenge
Run complete analysis and generate results
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure the script directory is in the path so we can import our modules
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR))

from vlm_analyzer import VLMAnalyzer
from cascadia_scorer import CascadiaScorer

def main():
    """Run complete Cascadia scoring analysis"""
    
    # Load environment variables
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
    
    API_KEY = os.getenv("OPENAI_API_KEY")
    
    def find_image(base_name):
        """Find image with either .jpg or .png extension relative to script"""
        images_dir = SCRIPT_DIR / "images"
        for ext in ['.jpg', '.png']:
            path = images_dir / f"{base_name}{ext}"
            if path.exists():
                return str(path)
        return str(images_dir / f"{base_name}.jpg")
    
    BOARD_IMAGE = find_image("board_positions")
    SCORING_CARDS_IMAGE = find_image("scoring_cards")
    
    print("Cascadia Scoring Analysis")
    print(f"Board: {Path(BOARD_IMAGE).name}")
    print(f"Cards: {Path(SCORING_CARDS_IMAGE).name}\n")
    
    # Initialize components
    try:
        analyzer = VLMAnalyzer(api_key=API_KEY)
        scorer = CascadiaScorer()
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Scoring rules (Card A)
    scoring_rules = {
        "bear": {"rule": "Pairs of exactly 2 bears", "scoring": {"pair": 4}},
        "elk": {"rule": "Straight lines of elk", "scoring": {"1": 2, "2": 5, "3": 9, "4+": 13}},
        "salmon": {"rule": "Salmon runs", "scoring": {"1": 2, "2": 5, "3": 8, "4": 11, "5+": 14}},
        "hawk": {"rule": "Isolated hawks", "scoring": {"1": 2, "2": 5, "3": 8, "4": 11, "5": 14, "6": 18, "7": 22, "8+": 26}},
        "fox": {"rule": "Unique neighbors", "scoring": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}}
    }
    
    # Analyze boards
    try:
        player_boards = analyzer.analyze_board_positions(BOARD_IMAGE)
    except Exception as e:
        print(f"Error: {e}")
        return
    
    for board in player_boards:
        print(f"Player {board.player_id}: Animals={board.animals}, Habitats={board.largest_habitats}")
    
    player_scores = scorer.score_game(player_boards, scoring_rules)
    
    print("\nSCORE BREAKDOWN")
    for ps in player_scores:
        print(f"Player {ps.player_id}: Total {ps.total_score} pts (Animals: {sum(ps.animal_scores.values())}, Habitats: {ps.habitat_total}, Bonuses: {sum(ps.majority_bonuses.values())})")
    
    winner_id, winner_explanation = scorer.determine_winner(player_scores)
    print(f"\nRESULT: {winner_explanation}")
    
    # Save results
    results = scorer.format_results(player_scores)
    output_dir = SCRIPT_DIR / "results"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "final_scores.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nOutput saved to: {output_file.name}")

if __name__ == "__main__":
    main()
