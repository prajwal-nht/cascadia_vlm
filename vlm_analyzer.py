import base64
import json
import os
import requests
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from io import BytesIO
from PIL import Image


@dataclass
class PlayerBoard:
    """Represents analyzed data for one player's board"""
    player_id: int
    nature_tokens: int
    animals: Dict[str, int]  # animal_type -> count
    largest_habitats: Dict[str, int]  # terrain_type -> size of largest group
    wildlife_patterns: Dict[str, any]  # pattern_name -> count/list


class VLMAnalyzer:
    """Analyzes Cascadia board images using OpenAI's Vision-Language Models"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize VLM analyzer
        """
        self.api_key = api_key

    
    def analyze_board_positions(self, image_path: str) -> List[PlayerBoard]:
        """
        Analyze the main board image showing all three players
        """
        prompt = self._create_board_analysis_prompt()
        response = self._analyze_with_openai(image_path, prompt)
        return self._parse_board_response(response)
    
    def analyze_scoring_cards(self, image_path: str) -> Dict[str, Dict]:
        """
        Analyze scoring card image to extract scoring rules
        """
        prompt = self._create_scoring_card_prompt()
        response = self._analyze_with_openai(image_path, prompt)
        return self._parse_scoring_rules(response)
    
    def _create_board_analysis_prompt(self) -> str:
        """Create detailed prompt for board analysis"""
        return """CRITICAL: This image contains THREE (3) distinct player board arrangements (arranged Left, Middle, and Right). You MUST analyze and return data for all three players.

For EACH of the three players (Left, Middle, Right), identify and count:

1. COMPONENT COUNTS:
   - Nature Tokens (Pinecones)
   - Total count of each animal type (Bear, Elk, Salmon, Hawk, Fox)

2. HABITAT SCORING (Largest Contiguous Area):
   - For each terrain type (Mountain, Forest, Prairie, Wetland, River), count the size of the SINGLE LARGEST contiguous group.
   - IMPORTANT: Tiles must share an EDGE to be contiguous. Diagonal/corner connections DO NOT count.

3. WILDLIFE SCORING PATTERNS:
   - Bears: Count only groups of EXACTLY 2 bears. A group of 1 or 3+ bears scores 0.
   - Elk: List the lengths of all separate straight lines of elk.
   - Salmon: List the lengths of all salmon runs (chains where each salmon touches NO MORE than 2 others).
   - Hawks: Count the number of hawks that are NOT adjacent (not sharing an edge) with any other hawk.
   - Foxes: For each fox, count how many UNIQUE animal types (Bear, Elk, Salmon, Hawk) are in the 6 adjacent hexes.

Return your analysis as a JSON object:
{
  "player_1": {
    "nature_tokens": X,
    "animals": {"bear": X, "elk": X, "salmon": X, "hawk": X, "fox": X},
    "largest_habitats": {"mountain": X, "forest": X, "prairie": X, "wetland": X, "river": X},
    "wildlife_patterns": {
      "bear_pairs": X,
      "elk_lines": [lengths list],
      "salmon_runs": [lengths list],
      "isolated_hawks": X,
      "fox_neighbors": [unique neighbor count for each fox]
    }
  },
  "player_2": { ... },
  "player_3": { ... }
}
"""
    
    def _create_scoring_card_prompt(self) -> str:
        """Create prompt for scoring card analysis"""
        return """Analyze these Cascadia wildlife scoring cards. Return points for configurations as JSON."""
    
    def _process_image(self, image_path: str, max_size: int = 1536) -> bytes:
        """Read and resize image if needed, return bytes"""
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=75, optimize=True)
            return buffer.getvalue()

    def _analyze_with_openai(self, image_path: str, prompt: str) -> str:
        """Analyze image using direct requests to OpenAI API (SDK bypass)"""
        print(f"Processing {Path(image_path).name}...")
        image_bytes = self._process_image(image_path)

        image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + "\nReturn valid JSON."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}", "detail": "low"}
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 800,
            "temperature": 0
        }
        
        print(f"Requesting analysis from OpenAI...")

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code != 200:
                print(f"  > API Error ({response.status_code}): {response.text}")
                response.raise_for_status()
                
            print("  > API Response received.")
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"  > Network error: {e}")
            raise
    
    def _parse_board_response(self, response: str) -> List[PlayerBoard]:
        """Parse VLM response into PlayerBoard objects"""
        data = json.loads(response)
        players = []
        for i in range(1, 4):
            k = f"player_{i}"
            if k in data:
                p = data[k]
                players.append(PlayerBoard(
                    player_id=i,
                    nature_tokens=p.get('nature_tokens', 0),
                    animals=p.get('animals', {}),
                    largest_habitats=p.get('largest_habitats', {}),
                    wildlife_patterns=p.get('wildlife_patterns', {})
                ))
        return players
    
    def _parse_scoring_rules(self, response: str) -> Dict[str, Dict]:
        """Parse scoring card response"""
        return json.loads(response)
