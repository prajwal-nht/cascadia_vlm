# Cascadia VLM Challenge

Automated scoring system for the board game Cascadia using OpenAI GPT-4o-mini Vision.

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Environment**:
   Create a `.env` file in this directory with your OpenAI API key:
   ```text
   OPENAI_API_KEY=your_key_here
   ```

3. **Run Analysis**:
   ```bash
   python run_analysis.py
   ```

## Features
- **Visual Analysis**: Extracts animal counts and habitat sizes directly from board images.
- **Rule Engine**: Implements official scoring for Bears, Elk, Salmon, Hawks, and Foxes (Card A).
- **Majority Bonuses**: Automatically calculates terrain majority bonuses for all players.
- **Optimized**: Fast processing with small image payloads and direct API requests.
