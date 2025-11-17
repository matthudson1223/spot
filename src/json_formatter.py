"""
JSON formatter for crossword puzzles

Formats puzzle data into clean, standardized JSON output
"""
import json
from datetime import datetime
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JSONFormatter:
    """Formats crossword puzzles as JSON"""

    def format_puzzle(self, puzzle_data: Dict) -> Dict:
        """
        Format puzzle data into clean JSON structure

        Args:
            puzzle_data: Raw puzzle data

        Returns:
            Formatted puzzle dictionary
        """
        formatted = {
            "metadata": self._format_metadata(puzzle_data),
            "puzzle": self._format_puzzle_data(puzzle_data),
            "statistics": self._format_statistics(puzzle_data),
            "solution": self._format_solution(puzzle_data)
        }

        return formatted

    def _format_metadata(self, puzzle_data: Dict) -> Dict:
        """Format puzzle metadata"""
        return {
            "puzzle_id": puzzle_data.get("puzzle_id", "unknown"),
            "generated_at": puzzle_data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "theme": puzzle_data.get("theme", "General"),
            "difficulty": puzzle_data.get("day_of_week", puzzle_data.get("difficulty", "Wednesday")),
            "size": {
                "rows": puzzle_data.get("size", [15, 15])[0],
                "cols": puzzle_data.get("size", [15, 15])[1]
            },
            "quality_score": puzzle_data.get("quality_score", 0.0),
            "generation_time_seconds": puzzle_data.get("generation_time", 0.0),
            "source": puzzle_data.get("source", "ai_generated")
        }

    def _format_puzzle_data(self, puzzle_data: Dict) -> Dict:
        """Format main puzzle data (grid, clues)"""
        grid = puzzle_data.get("grid", {})

        return {
            "grid": {
                "layout": grid.get("layout", []),
                "numbers": grid.get("numbers", [])
            },
            "clues": {
                "across": puzzle_data.get("clues", {}).get("across", {}),
                "down": puzzle_data.get("clues", {}).get("down", {})
            },
            "theme_answers": puzzle_data.get("theme_answers", [])
        }

    def _format_statistics(self, puzzle_data: Dict) -> Dict:
        """Format puzzle statistics"""
        answers = puzzle_data.get("answers", {})
        across_count = len(answers.get("across", []))
        down_count = len(answers.get("down", []))

        grid_layout = puzzle_data.get("grid", {}).get("layout", [])
        black_count = sum(row.count(0) for row in grid_layout)
        total_cells = len(grid_layout) * len(grid_layout[0]) if grid_layout else 0

        return {
            "word_count": across_count + down_count,
            "across_count": across_count,
            "down_count": down_count,
            "theme_answer_count": len(puzzle_data.get("theme_answers", [])),
            "black_square_count": black_count,
            "black_square_ratio": round(black_count / total_cells, 3) if total_cells > 0 else 0,
            "total_cells": total_cells
        }

    def _format_solution(self, puzzle_data: Dict) -> Dict:
        """Format solution data (answers with positions)"""
        return {
            "across": [
                {
                    "number": ans.get("number"),
                    "answer": ans.get("answer"),
                    "position": ans.get("start_pos"),
                    "length": ans.get("length"),
                    "is_theme": ans.get("is_theme", False)
                }
                for ans in puzzle_data.get("answers", {}).get("across", [])
            ],
            "down": [
                {
                    "number": ans.get("number"),
                    "answer": ans.get("answer"),
                    "position": ans.get("start_pos"),
                    "length": ans.get("length"),
                    "is_theme": ans.get("is_theme", False)
                }
                for ans in puzzle_data.get("answers", {}).get("down", [])
            ]
        }

    def save_formatted_puzzle(self, puzzle_data: Dict, filepath: str) -> None:
        """Save formatted puzzle to JSON file"""
        formatted = self.format_puzzle(puzzle_data)

        with open(filepath, 'w') as f:
            json.dump(formatted, f, indent=2)

        logger.info(f"Formatted puzzle saved to: {filepath}")

    def format_as_string(self, puzzle_data: Dict, indent: int = 2) -> str:
        """Format puzzle as JSON string"""
        formatted = self.format_puzzle(puzzle_data)
        return json.dumps(formatted, indent=indent)


def main():
    """Test JSON formatter"""
    import sys
    from utils import load_jsonl

    if len(sys.argv) < 2:
        print("Usage: python json_formatter.py <puzzle_file.jsonl>")
        sys.exit(1)

    # Load puzzle
    puzzles = load_jsonl(sys.argv[1])
    if not puzzles:
        print(f"No puzzles found in {sys.argv[1]}")
        sys.exit(1)

    # Format first puzzle
    formatter = JSONFormatter()
    formatted = formatter.format_puzzle(puzzles[0])

    # Print formatted JSON
    print(json.dumps(formatted, indent=2))


if __name__ == "__main__":
    main()
