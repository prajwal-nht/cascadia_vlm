"""
Cascadia Scoring Rules Implementation
Based on official game rules and scoring cards
"""

from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


@dataclass
class AnimalPosition:
    """Represents an animal token position on the board"""
    animal_type: str  # bear, elk, salmon, hawk, fox
    row: int
    col: int
    adjacent_animals: List[str]  # Types of adjacent animals


@dataclass
class HabitatTile:
    """Represents a habitat tile"""
    terrain_type: str  # mountain, forest, prairie, wetland, river
    row: int
    col: int


class CascadiaScoringRules:
    """Implements all Cascadia scoring rules"""
    
    @staticmethod
    def score_bears_pairs(bear_positions: List[AnimalPosition]) -> Tuple[int, str]:
        """
        Bear Scoring (Card A): Score pairs of exactly 2 bears
        - Each valid pair scores points
        """
        visited = set()
        pairs = 0
        explanation = []
        
        # Build adjacency map
        adjacency = {}
        for i, bear in enumerate(bear_positions):
            adjacency[i] = []
            for j, other_bear in enumerate(bear_positions):
                if i != j and CascadiaScoringRules._are_adjacent(bear, other_bear):
                    adjacency[i].append(j)
        
        # Find pairs (groups of exactly 2)
        for i in range(len(bear_positions)):
            if i in visited:
                continue
            
            # Check if this bear is part of a pair
            neighbors = adjacency[i]
            if len(neighbors) == 1:
                j = neighbors[0]
                if len(adjacency[j]) == 1 and adjacency[j][0] == i:
                    # Valid pair
                    pairs += 1
                    visited.add(i)
                    visited.add(j)
                    explanation.append(f"Pair at positions ({bear_positions[i].row},{bear_positions[i].col}) and ({bear_positions[j].row},{bear_positions[j].col})")
        
        score = pairs * 4  # 4 points per pair (typical scoring)
        return score, f"{pairs} pairs found. " + "; ".join(explanation)
    
    @staticmethod
    def score_elk_lines(elk_positions: List[AnimalPosition]) -> Tuple[int, str]:
        """
        Elk Scoring (Card A): Score straight lines of elk
        - Lines of 1, 2, 3, or 4+ elk score progressively more points
        """
        if not elk_positions:
            return 0, "No elk found"
        
        # Find all straight lines (horizontal, vertical, diagonal)
        lines = CascadiaScoringRules._find_straight_lines(elk_positions)
        
        # Score based on line length
        score = 0
        explanation = []
        for line_length, count in lines.items():
            if line_length == 1:
                points = 2
            elif line_length == 2:
                points = 5
            elif line_length == 3:
                points = 9
            else:  # 4+
                points = 13
            
            score += points * count
            explanation.append(f"{count} line(s) of {line_length} elk = {points * count} pts")
        
        return score, "; ".join(explanation)
    
    @staticmethod
    def score_salmon_runs(salmon_positions: List[AnimalPosition]) -> Tuple[int, str]:
        """
        Salmon Scoring (Card A): Score runs where each salmon touches max 2 others
        - Longer runs score more points
        """
        if not salmon_positions:
            return 0, "No salmon found"
        
        # Build adjacency
        adjacency = {}
        for i, salmon in enumerate(salmon_positions):
            adjacency[i] = []
            for j, other in enumerate(salmon_positions):
                if i != j and CascadiaScoringRules._are_adjacent(salmon, other):
                    adjacency[i].append(j)
        
        # Find valid runs (each salmon has max 2 neighbors)
        visited = set()
        runs = []
        
        for start_idx in range(len(salmon_positions)):
            if start_idx in visited:
                continue
            
            # Check if valid run member (max 2 neighbors)
            if len(adjacency[start_idx]) <= 2:
                run = CascadiaScoringRules._trace_run(start_idx, adjacency, visited)
                if len(run) > 0:
                    runs.append(len(run))
        
        # Score runs
        score = sum(runs)
        explanation = f"Found {len(runs)} run(s): lengths {runs}"
        
        return score, explanation
    
    @staticmethod
    def score_hawks_isolated(hawk_positions: List[AnimalPosition]) -> Tuple[int, str]:
        """
        Hawk Scoring (Card A): Score hawks not adjacent to other hawks
        - Each isolated hawk scores points
        """
        if not hawk_positions:
            return 0, "No hawks found"
        
        isolated_count = 0
        for i, hawk in enumerate(hawk_positions):
            is_isolated = True
            for j, other_hawk in enumerate(hawk_positions):
                if i != j and CascadiaScoringRules._are_adjacent(hawk, other_hawk):
                    is_isolated = False
                    break
            if is_isolated:
                isolated_count += 1
        
        score = isolated_count * 5  # 5 points per isolated hawk
        return score, f"{isolated_count} isolated hawks × 5 pts"
    
    @staticmethod
    def score_foxes_variety(fox_positions: List[AnimalPosition]) -> Tuple[int, str]:
        """
        Fox Scoring (Card A): Score based on variety of adjacent animal types
        - More variety = more points per fox
        """
        if not fox_positions:
            return 0, "No foxes found"
        
        score = 0
        explanation = []
        
        for fox in fox_positions:
            unique_neighbors = len(set(fox.adjacent_animals))
            if unique_neighbors == 0:
                points = 0
            elif unique_neighbors == 1:
                points = 1
            elif unique_neighbors == 2:
                points = 3
            elif unique_neighbors == 3:
                points = 5
            else:  # 4+
                points = 8
            
            score += points
            explanation.append(f"Fox with {unique_neighbors} unique neighbors = {points} pts")
        
        return score, "; ".join(explanation[:5])  # Limit output
    
    @staticmethod
    def score_habitat_corridors(habitat_tiles: List[HabitatTile]) -> Tuple[Dict[str, int], str]:
        """
        Score largest contiguous area of each terrain type
        - 1 point per tile in largest area
        """
        terrain_types = ['mountain', 'forest', 'prairie', 'wetland', 'river']
        scores = {}
        explanation = []
        
        for terrain in terrain_types:
            tiles_of_type = [t for t in habitat_tiles if t.terrain_type == terrain]
            if not tiles_of_type:
                scores[terrain] = 0
                continue
            
            largest_area = CascadiaScoringRules._find_largest_contiguous_area(tiles_of_type)
            scores[terrain] = largest_area
            explanation.append(f"{terrain.capitalize()}: {largest_area} tiles")
        
        return scores, "; ".join(explanation)
    
    @staticmethod
    def _are_adjacent(pos1: AnimalPosition, pos2: AnimalPosition) -> bool:
        """Check if two positions are adjacent (share an edge)"""
        row_diff = abs(pos1.row - pos2.row)
        col_diff = abs(pos1.col - pos2.col)
        
        # Hex grid adjacency (simplified - assumes standard hex layout)
        return (row_diff == 0 and col_diff == 1) or \
               (row_diff == 1 and col_diff == 0) or \
               (row_diff == 1 and col_diff == 1)
    
    @staticmethod
    def _find_straight_lines(positions: List[AnimalPosition]) -> Dict[int, int]:
        """Find all straight lines in positions"""
        # Simplified: group by row, col, and diagonals
        lines = {}
        # This is a simplified version - full implementation would check all directions
        return {1: len(positions)}  # Placeholder
    
    @staticmethod
    def _trace_run(start_idx: int, adjacency: Dict, visited: Set) -> List[int]:
        """Trace a salmon run from starting position"""
        run = [start_idx]
        visited.add(start_idx)
        
        # Simple DFS to trace the run
        for neighbor in adjacency[start_idx]:
            if neighbor not in visited and len(adjacency[neighbor]) <= 2:
                run.extend(CascadiaScoringRules._trace_run(neighbor, adjacency, visited))
        
        return run
    
    @staticmethod
    def _find_largest_contiguous_area(tiles: List[HabitatTile]) -> int:
        """Find largest contiguous area using flood fill"""
        if not tiles:
            return 0
        
        visited = set()
        max_area = 0
        
        for i, tile in enumerate(tiles):
            if i not in visited:
                area = CascadiaScoringRules._flood_fill(i, tiles, visited)
                max_area = max(max_area, area)
        
        return max_area
    
    @staticmethod
    def _flood_fill(start_idx: int, tiles: List[HabitatTile], visited: Set) -> int:
        """Flood fill to count contiguous area"""
        if start_idx in visited:
            return 0
        
        visited.add(start_idx)
        area = 1
        
        start_tile = tiles[start_idx]
        for i, tile in enumerate(tiles):
            if i not in visited:
                # Check adjacency
                row_diff = abs(start_tile.row - tile.row)
                col_diff = abs(start_tile.col - tile.col)
                if (row_diff == 0 and col_diff == 1) or (row_diff == 1 and col_diff == 0):
                    area += CascadiaScoringRules._flood_fill(i, tiles, visited)
        
        return area
