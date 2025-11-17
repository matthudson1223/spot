"""
Utility functions and helpers for crossword generation
"""
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise


def save_json(data: Dict, filepath: str) -> None:
    """Save data as JSON file"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved JSON to {filepath}")


def save_jsonl(data: List[Dict], filepath: str) -> None:
    """Save data as JSONL file (one JSON object per line)"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')
    logger.info(f"Saved {len(data)} items to {filepath}")


def load_jsonl(filepath: str) -> List[Dict]:
    """Load data from JSONL file"""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def validate_grid_dimensions(grid: List[List[int]], expected_size: Tuple[int, int]) -> bool:
    """Validate grid has correct dimensions"""
    if len(grid) != expected_size[0]:
        return False
    for row in grid:
        if len(row) != expected_size[1]:
            return False
    return True


def check_rotational_symmetry(grid: List[List[int]]) -> bool:
    """
    Check if grid has 180-degree rotational symmetry
    Grid values: 1 = white square, 0 = black square
    """
    n = len(grid)
    m = len(grid[0]) if n > 0 else 0

    for i in range(n):
        for j in range(m):
            # Check if cell matches its 180-degree rotation
            if grid[i][j] != grid[n-1-i][m-1-j]:
                return False
    return True


def count_black_squares(grid: List[List[int]]) -> Tuple[int, float]:
    """Count black squares and return count and ratio"""
    total_squares = len(grid) * len(grid[0])
    black_count = sum(row.count(0) for row in grid)
    ratio = black_count / total_squares if total_squares > 0 else 0
    return black_count, ratio


def is_connected(grid: List[List[int]]) -> bool:
    """
    Check if all white squares are connected
    Uses flood fill algorithm
    """
    n = len(grid)
    if n == 0:
        return True
    m = len(grid[0])

    # Find first white square
    start_i, start_j = None, None
    white_count = 0
    for i in range(n):
        for j in range(m):
            if grid[i][j] == 1:
                white_count += 1
                if start_i is None:
                    start_i, start_j = i, j

    if white_count == 0:
        return True

    # Flood fill from first white square
    visited = [[False] * m for _ in range(n)]
    stack = [(start_i, start_j)]
    visited_count = 0

    while stack:
        i, j = stack.pop()
        if i < 0 or i >= n or j < 0 or j >= m or visited[i][j] or grid[i][j] == 0:
            continue

        visited[i][j] = True
        visited_count += 1

        # Add neighbors
        stack.extend([(i+1, j), (i-1, j), (i, j+1), (i, j-1)])

    return visited_count == white_count


def number_grid(grid: List[List[int]]) -> List[List[int]]:
    """
    Number the grid cells according to crossword conventions
    Returns grid with cell numbers (0 for unnumbered cells)
    """
    n = len(grid)
    if n == 0:
        return []
    m = len(grid[0])

    numbered_grid = [[0] * m for _ in range(n)]
    cell_number = 1

    for i in range(n):
        for j in range(m):
            if grid[i][j] == 0:  # Black square
                continue

            # Check if this is the start of an across or down word
            starts_across = (j == 0 or grid[i][j-1] == 0) and (j < m-1 and grid[i][j+1] == 1)
            starts_down = (i == 0 or grid[i-1][j] == 0) and (i < n-1 and grid[i+1][j] == 1)

            if starts_across or starts_down:
                numbered_grid[i][j] = cell_number
                cell_number += 1

    return numbered_grid


def extract_words_from_grid(
    grid: List[List[int]],
    numbered_grid: List[List[int]]
) -> Dict[str, List[Dict]]:
    """
    Extract all word positions from grid
    Returns dict with 'across' and 'down' word positions
    """
    n = len(grid)
    if n == 0:
        return {"across": [], "down": []}
    m = len(grid[0])

    words = {"across": [], "down": []}

    # Find across words
    for i in range(n):
        j = 0
        while j < m:
            if grid[i][j] == 1:
                start_j = j
                length = 0
                while j < m and grid[i][j] == 1:
                    length += 1
                    j += 1

                if length >= 3:  # Minimum word length
                    number = numbered_grid[i][start_j]
                    if number > 0:
                        words["across"].append({
                            "number": number,
                            "start_pos": [i, start_j],
                            "length": length,
                            "cells": [[i, start_j + k] for k in range(length)]
                        })
            else:
                j += 1

    # Find down words
    for j in range(m):
        i = 0
        while i < n:
            if grid[i][j] == 1:
                start_i = i
                length = 0
                while i < n and grid[i][j] == 1:
                    length += 1
                    i += 1

                if length >= 3:  # Minimum word length
                    number = numbered_grid[start_i][j]
                    if number > 0:
                        words["down"].append({
                            "number": number,
                            "start_pos": [start_i, j],
                            "length": length,
                            "cells": [[start_i + k, j] for k in range(length)]
                        })
            else:
                i += 1

    return words


class CrosswordDictionary:
    """
    Manages crossword word dictionary
    In a full implementation, this would load from a comprehensive word list
    """

    def __init__(self, dictionary_path: Optional[str] = None):
        self.words = set()
        if dictionary_path and Path(dictionary_path).exists():
            self.load_dictionary(dictionary_path)
        else:
            logger.warning("No dictionary loaded, using empty set")

    def load_dictionary(self, filepath: str) -> None:
        """Load dictionary from file (one word per line)"""
        with open(filepath, 'r') as f:
            for line in f:
                word = line.strip().upper()
                if word and len(word) >= 3:
                    self.words.add(word)
        logger.info(f"Loaded {len(self.words)} words from dictionary")

    def is_valid_word(self, word: str) -> bool:
        """Check if word exists in dictionary"""
        return word.upper() in self.words

    def get_words_by_length(self, length: int) -> List[str]:
        """Get all words of specific length"""
        return [w for w in self.words if len(w) == length]

    def get_words_matching_pattern(self, pattern: str) -> List[str]:
        """
        Get words matching pattern where '.' is wildcard
        Example: "A.PLE" matches "APPLE"
        """
        import re
        pattern_regex = pattern.replace('.', '.')
        regex = re.compile(f"^{pattern_regex}$")
        return [w for w in self.words if regex.match(w)]


def format_date_as_puzzle_id(date: datetime, source: str = "nyt") -> str:
    """Format date as puzzle ID"""
    return f"{source}_{date.strftime('%Y_%m_%d')}"


def get_day_of_week(date: datetime) -> str:
    """Get day of week name from date"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[date.weekday()]


def validate_puzzle_structure(puzzle: Dict) -> Tuple[bool, List[str]]:
    """
    Validate that puzzle has all required fields
    Returns (is_valid, list_of_errors)
    """
    errors = []

    required_fields = ["puzzle_id", "date", "size", "grid", "answers", "clues"]
    for field in required_fields:
        if field not in puzzle:
            errors.append(f"Missing required field: {field}")

    if "grid" in puzzle:
        if "layout" not in puzzle["grid"]:
            errors.append("Missing grid.layout")
        if "numbers" not in puzzle["grid"]:
            errors.append("Missing grid.numbers")

    if "answers" in puzzle:
        if "across" not in puzzle["answers"]:
            errors.append("Missing answers.across")
        if "down" not in puzzle["answers"]:
            errors.append("Missing answers.down")

    if "clues" in puzzle:
        if "across" not in puzzle["clues"]:
            errors.append("Missing clues.across")
        if "down" not in puzzle["clues"]:
            errors.append("Missing clues.down")

    return len(errors) == 0, errors


def calculate_puzzle_stats(puzzle: Dict) -> Dict[str, Any]:
    """Calculate statistics for a puzzle"""
    grid = puzzle.get("grid", {}).get("layout", [])
    answers = puzzle.get("answers", {})

    black_count, black_ratio = count_black_squares(grid)

    word_count = len(answers.get("across", [])) + len(answers.get("down", []))

    theme_answers = puzzle.get("theme_answers", [])

    return {
        "word_count": word_count,
        "black_square_count": black_count,
        "black_square_ratio": round(black_ratio, 3),
        "theme_answer_count": len(theme_answers),
        "has_symmetry": check_rotational_symmetry(grid),
        "is_connected": is_connected(grid)
    }
