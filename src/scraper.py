"""
Crossword puzzle scraper with multiple data sources

IMPORTANT: This scraper includes multiple strategies:
1. Synthetic data generation (for testing and demonstration)
2. Public crossword archives (where permitted)
3. User-uploaded puzzles

Always respect website terms of service and robots.txt
"""
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from tqdm import tqdm

import requests
from bs4 import BeautifulSoup

from utils import (
    load_config,
    save_jsonl,
    format_date_as_puzzle_id,
    get_day_of_week,
    validate_puzzle_structure,
    check_rotational_symmetry,
    number_grid,
    extract_words_from_grid
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyntheticPuzzleGenerator:
    """
    Generates synthetic crossword puzzles for training data
    This is useful for testing and when real puzzle data is limited
    """

    def __init__(self):
        # Sample word lists by difficulty
        self.word_pools = {
            "Monday": self._get_easy_words(),
            "Tuesday": self._get_easy_words() + self._get_medium_words(),
            "Wednesday": self._get_medium_words(),
            "Thursday": self._get_medium_words() + self._get_hard_words(),
            "Friday": self._get_hard_words(),
            "Saturday": self._get_hard_words(),
            "Sunday": self._get_medium_words() + self._get_hard_words()
        }

        # Sample themes
        self.themes = [
            "Space exploration", "Ocean life", "Music genres", "World capitals",
            "Food and cooking", "Sports", "Technology", "Literature",
            "Movies", "Science", "History", "Geography", "Animals",
            "Transportation", "Weather", "Art", "Mathematics"
        ]

    def _get_easy_words(self) -> List[str]:
        """Common, easy words"""
        return [
            "CAT", "DOG", "RUN", "WALK", "TREE", "HOUSE", "BLUE", "RED",
            "APPLE", "ORANGE", "WATER", "FIRE", "EARTH", "SMILE", "HAPPY",
            "BIRD", "FISH", "BOOK", "PLAY", "SING", "DANCE", "SUNNY",
            "MOON", "STAR", "RIVER", "BEACH", "GARDEN", "FLOWER", "MUSIC"
        ]

    def _get_medium_words(self) -> List[str]:
        """Medium difficulty words"""
        return [
            "APOLLO", "GALAXY", "ORBIT", "PLASMA", "QUASAR", "NEBULA",
            "ECLIPSE", "COMET", "ASTEROID", "METEOR", "PLANET", "ROCKET",
            "SATELLITE", "TELESCOPE", "CRATER", "LUNAR", "SOLAR", "COSMIC",
            "ZENITH", "EQUINOX", "SOLSTICE", "GRAVITY", "VELOCITY"
        ]

    def _get_hard_words(self) -> List[str]:
        """Hard words"""
        return [
            "QUIXOTIC", "EPHEMERAL", "ESOTERIC", "UBIQUITOUS", "PARADIGM",
            "SERENDIPITY", "PETRICHOR", "ELOQUENT", "AESTHETIC", "ANOMALY",
            "SYMBIOSIS", "CATALYST", "DICHOTOMY", "ENTROPY", "HYPOTHESIS"
        ]

    def generate_simple_grid(self, size: Tuple[int, int] = (15, 15)) -> List[List[int]]:
        """
        Generate a simple crossword grid with rotational symmetry
        1 = white square, 0 = black square
        """
        n, m = size
        grid = [[1] * m for _ in range(n)]

        # Add black squares with symmetry
        num_black_squares = int(n * m * 0.15)  # ~15% black squares
        placed = 0

        while placed < num_black_squares // 2:
            i = random.randint(0, n - 1)
            j = random.randint(0, m - 1)

            # Don't place in corners or if already black
            if grid[i][j] == 0:
                continue

            # Place black square and its symmetric counterpart
            grid[i][j] = 0
            grid[n-1-i][m-1-j] = 0
            placed += 1

        return grid

    def generate_puzzle(
        self,
        puzzle_id: str,
        date: datetime,
        size: Tuple[int, int] = (15, 15),
        difficulty: Optional[str] = None
    ) -> Dict:
        """Generate a complete synthetic puzzle"""

        if difficulty is None:
            difficulty = get_day_of_week(date)

        # Generate grid
        grid_layout = self.generate_simple_grid(size)
        grid_numbers = number_grid(grid_layout)

        # Extract word positions
        word_positions = extract_words_from_grid(grid_layout, grid_numbers)

        # Generate theme
        theme = random.choice(self.themes)

        # Get word pool for difficulty
        word_pool = self.word_pools.get(difficulty, self.word_pools["Wednesday"])

        # Fill in answers
        answers = {"across": [], "down": []}
        clues = {"across": {}, "down": {}}
        theme_answers = []

        # Across words
        for word_info in word_positions["across"]:
            length = word_info["length"]
            # Find word of matching length
            matching_words = [w for w in word_pool if len(w) == length]
            if not matching_words:
                # Fallback to generating random word
                answer = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=length))
            else:
                answer = random.choice(matching_words)

            is_theme = random.random() < 0.2  # 20% chance of being theme answer

            answers["across"].append({
                "number": word_info["number"],
                "answer": answer,
                "start_pos": word_info["start_pos"],
                "length": length,
                "is_theme": is_theme
            })

            clues["across"][str(word_info["number"])] = self._generate_clue(
                answer, difficulty, theme if is_theme else None
            )

            if is_theme:
                theme_answers.append(answer)

        # Down words
        for word_info in word_positions["down"]:
            length = word_info["length"]
            matching_words = [w for w in word_pool if len(w) == length]
            if not matching_words:
                answer = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=length))
            else:
                answer = random.choice(matching_words)

            is_theme = random.random() < 0.15  # 15% chance

            answers["down"].append({
                "number": word_info["number"],
                "answer": answer,
                "start_pos": word_info["start_pos"],
                "length": length,
                "is_theme": is_theme
            })

            clues["down"][str(word_info["number"])] = self._generate_clue(
                answer, difficulty, theme if is_theme else None
            )

            if is_theme:
                theme_answers.append(answer)

        # Construct puzzle
        puzzle = {
            "puzzle_id": puzzle_id,
            "date": date.strftime("%Y-%m-%d"),
            "day_of_week": difficulty,
            "size": list(size),
            "theme": theme,
            "grid": {
                "layout": grid_layout,
                "numbers": grid_numbers
            },
            "answers": answers,
            "clues": clues,
            "theme_answers": theme_answers[:3],  # Keep top 3 theme answers
            "stats": {
                "word_count": len(answers["across"]) + len(answers["down"]),
                "black_square_count": sum(row.count(0) for row in grid_layout),
                "has_symmetry": check_rotational_symmetry(grid_layout)
            },
            "source": "synthetic"
        }

        return puzzle

    def _generate_clue(self, answer: str, difficulty: str, theme: Optional[str] = None) -> str:
        """Generate a simple clue for an answer"""
        # This is simplified - in real implementation, clues would be more sophisticated
        if theme:
            return f"{answer} ({theme} related)"

        # Generic clues based on difficulty
        if difficulty in ["Monday", "Tuesday"]:
            return f"{answer} (definition)"
        elif difficulty in ["Wednesday", "Thursday"]:
            return f"Synonym for {answer}"
        else:
            return f"Cryptic: {answer}"


class CrosswordScraper:
    """
    Main scraper class that coordinates different data sources
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.scraping_config = self.config.get("scraping", {})
        self.output_dir = Path("data/raw")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.synthetic_generator = SyntheticPuzzleGenerator()
        self.scraped_puzzles = []

    def scrape_puzzles(self, source: str = "synthetic") -> List[Dict]:
        """
        Main scraping function

        Args:
            source: Data source - "synthetic", "public_archive", or "custom"
        """
        if source == "synthetic":
            return self._scrape_synthetic()
        elif source == "public_archive":
            return self._scrape_public_archive()
        else:
            logger.error(f"Unknown source: {source}")
            return []

    def _scrape_synthetic(self) -> List[Dict]:
        """Generate synthetic puzzles for training"""
        logger.info("Generating synthetic puzzles...")

        target_count = self.scraping_config.get("target_count", 1000)
        if self.scraping_config.get("test_mode", True):
            target_count = self.scraping_config.get("test_count", 10)

        start_date = datetime.strptime(
            self.scraping_config.get("start_date", "2020-01-01"),
            "%Y-%m-%d"
        )

        puzzles = []

        for i in tqdm(range(target_count), desc="Generating puzzles"):
            # Generate puzzle for sequential dates
            puzzle_date = start_date + timedelta(days=i)
            puzzle_id = format_date_as_puzzle_id(puzzle_date, "synthetic")

            # Alternate between sizes
            size = (15, 15) if i % 3 != 0 else (21, 21)

            puzzle = self.synthetic_generator.generate_puzzle(
                puzzle_id=puzzle_id,
                date=puzzle_date,
                size=size
            )

            # Validate puzzle structure
            is_valid, errors = validate_puzzle_structure(puzzle)
            if not is_valid:
                logger.warning(f"Invalid puzzle {puzzle_id}: {errors}")
                continue

            puzzles.append(puzzle)

        logger.info(f"Generated {len(puzzles)} synthetic puzzles")
        return puzzles

    def _scrape_public_archive(self) -> List[Dict]:
        """
        Scrape from public crossword archives

        NOTE: This is a placeholder. You should:
        1. Identify public, legal crossword sources
        2. Check their robots.txt and terms of service
        3. Implement respectful scraping with delays
        4. Consider using APIs if available
        """
        logger.warning("Public archive scraping not yet implemented")
        logger.info("Consider using:")
        logger.info("  - Crossword Nexus (crosswordnexus.com)")
        logger.info("  - Open-source puzzle repositories")
        logger.info("  - APIs from puzzle providers")
        return []

    def save_puzzles(self, puzzles: List[Dict], filename: str = "puzzles.jsonl") -> None:
        """Save scraped puzzles to JSONL file"""
        output_path = self.output_dir / filename
        save_jsonl(puzzles, str(output_path))
        logger.info(f"Saved {len(puzzles)} puzzles to {output_path}")

    def load_puzzles(self, filename: str = "puzzles.jsonl") -> List[Dict]:
        """Load puzzles from JSONL file"""
        from utils import load_jsonl
        input_path = self.output_dir / filename
        if not input_path.exists():
            logger.error(f"File not found: {input_path}")
            return []
        return load_jsonl(str(input_path))

    def scrape_and_save(self, source: str = "synthetic") -> str:
        """Scrape puzzles and save to file"""
        puzzles = self.scrape_puzzles(source)

        if not puzzles:
            logger.error("No puzzles scraped")
            return ""

        filename = f"puzzles_{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.save_puzzles(puzzles, filename)

        # Print statistics
        self._print_statistics(puzzles)

        return filename

    def _print_statistics(self, puzzles: List[Dict]) -> None:
        """Print statistics about scraped puzzles"""
        logger.info("\n" + "="*50)
        logger.info("PUZZLE COLLECTION STATISTICS")
        logger.info("="*50)
        logger.info(f"Total puzzles: {len(puzzles)}")

        # Count by day of week
        day_counts = {}
        size_counts = {}
        for puzzle in puzzles:
            day = puzzle.get("day_of_week", "Unknown")
            day_counts[day] = day_counts.get(day, 0) + 1

            size = tuple(puzzle.get("size", []))
            size_counts[size] = size_counts.get(size, 0) + 1

        logger.info("\nPuzzles by day:")
        for day, count in sorted(day_counts.items()):
            logger.info(f"  {day}: {count}")

        logger.info("\nPuzzles by size:")
        for size, count in sorted(size_counts.items()):
            logger.info(f"  {size}: {count}")

        # Average stats
        avg_words = sum(p["stats"]["word_count"] for p in puzzles) / len(puzzles)
        logger.info(f"\nAverage word count: {avg_words:.1f}")

        logger.info("="*50 + "\n")


def main():
    """Main entry point for scraper"""
    import argparse

    parser = argparse.ArgumentParser(description="Crossword puzzle scraper")
    parser.add_argument(
        "--source",
        choices=["synthetic", "public_archive"],
        default="synthetic",
        help="Data source to scrape from"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    scraper = CrosswordScraper(config_path=args.config)
    filename = scraper.scrape_and_save(source=args.source)

    if filename:
        logger.info(f"\nSuccess! Puzzles saved to: data/raw/{filename}")
        logger.info("Next step: Run dataset_builder.py to prepare training data")


if __name__ == "__main__":
    main()
