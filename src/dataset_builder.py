"""
Dataset builder for Vertex AI Gemini tuning

Transforms scraped crossword puzzles into three training datasets using GenerateContent format:
1. Grid Generator: Creates grid layout + theme answers
2. Fill Generator: Fills remaining words given constraints
3. Clue Generator: Writes clues for all answers

Format: Uses Gemini's GenerateContent format with "contents", "role" (user/model), and "parts"
"""
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from tqdm import tqdm

from utils import load_jsonl, save_jsonl, load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetBuilder:
    """
    Builds training datasets for the three fine-tuned models
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.training_config = self.config.get("training", {})
        self.train_split = self.training_config.get("train_split", 0.9)

        self.output_dir = Path("data/training")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_all_datasets(self, puzzles: List[Dict]) -> Dict[str, Dict]:
        """
        Build all three training datasets from puzzle collection

        Returns: Dict with dataset statistics
        """
        logger.info(f"Building training datasets from {len(puzzles)} puzzles...")

        # Build each dataset
        grid_dataset = self.build_grid_generation_dataset(puzzles)
        fill_dataset = self.build_fill_generation_dataset(puzzles)
        clue_dataset = self.build_clue_generation_dataset(puzzles)

        # Split and save each dataset
        stats = {}

        stats["grid"] = self._split_and_save_dataset(
            grid_dataset,
            "model1_grid",
            "Grid Generation"
        )

        stats["fill"] = self._split_and_save_dataset(
            fill_dataset,
            "model2_fill",
            "Fill Generation"
        )

        stats["clue"] = self._split_and_save_dataset(
            clue_dataset,
            "model3_clues",
            "Clue Generation"
        )

        # Save overall statistics
        self._save_statistics(stats)

        return stats

    def build_grid_generation_dataset(self, puzzles: List[Dict]) -> List[Dict]:
        """
        Build dataset for Model 1: Grid Generator

        Input: Theme, size, difficulty, randomness
        Output: Grid layout + theme answer positions
        """
        dataset = []

        for puzzle in tqdm(puzzles, desc="Building grid dataset"):
            # Create input prompt
            input_text = self._create_grid_input_prompt(puzzle)

            # Create output (grid structure with theme answers)
            output_data = self._create_grid_output(puzzle)

            # Format for Gemini tuning (GenerateContent format)
            dataset.append({
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": input_text}]
                    },
                    {
                        "role": "model",
                        "parts": [{"text": json.dumps(output_data, indent=2)}]
                    }
                ]
            })

        logger.info(f"Built {len(dataset)} grid generation examples")
        return dataset

    def build_fill_generation_dataset(self, puzzles: List[Dict]) -> List[Dict]:
        """
        Build dataset for Model 2: Fill Generator

        Input: Grid with theme answers already placed
        Output: All non-theme answers that complete the puzzle
        """
        dataset = []

        for puzzle in tqdm(puzzles, desc="Building fill dataset"):
            # Create input with partial grid (theme answers only)
            input_text = self._create_fill_input_prompt(puzzle)

            # Create output (all non-theme answers)
            output_data = self._create_fill_output(puzzle)

            # Format for Gemini tuning (GenerateContent format)
            dataset.append({
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": input_text}]
                    },
                    {
                        "role": "model",
                        "parts": [{"text": json.dumps(output_data, indent=2)}]
                    }
                ]
            })

        logger.info(f"Built {len(dataset)} fill generation examples")
        return dataset

    def build_clue_generation_dataset(self, puzzles: List[Dict]) -> List[Dict]:
        """
        Build dataset for Model 3: Clue Generator

        Input: Answer, length, difficulty, context
        Output: Clue text
        """
        dataset = []

        for puzzle in tqdm(puzzles, desc="Building clue dataset"):
            theme = puzzle.get("theme", "")
            difficulty = puzzle.get("day_of_week", "Wednesday")
            clues = puzzle.get("clues", {})

            # Process across clues
            for answer_info in puzzle.get("answers", {}).get("across", []):
                answer = answer_info.get("answer", "")
                number = str(answer_info.get("number", 0))
                is_theme = answer_info.get("is_theme", False)

                if number in clues.get("across", {}):
                    clue_text = clues["across"][number]

                    input_text = self._create_clue_input_prompt(
                        answer, difficulty, theme if is_theme else None
                    )

                    # Format for Gemini tuning (GenerateContent format)
                    dataset.append({
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": input_text}]
                            },
                            {
                                "role": "model",
                                "parts": [{"text": clue_text}]
                            }
                        ]
                    })

            # Process down clues
            for answer_info in puzzle.get("answers", {}).get("down", []):
                answer = answer_info.get("answer", "")
                number = str(answer_info.get("number", 0))
                is_theme = answer_info.get("is_theme", False)

                if number in clues.get("down", {}):
                    clue_text = clues["down"][number]

                    input_text = self._create_clue_input_prompt(
                        answer, difficulty, theme if is_theme else None
                    )

                    # Format for Gemini tuning (GenerateContent format)
                    dataset.append({
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": input_text}]
                            },
                            {
                                "role": "model",
                                "parts": [{"text": clue_text}]
                            }
                        ]
                    })

        logger.info(f"Built {len(dataset)} clue generation examples")
        return dataset

    def _create_grid_input_prompt(self, puzzle: Dict) -> str:
        """Create input prompt for grid generation"""
        theme = puzzle.get("theme", "General")
        size = puzzle.get("size", [15, 15])
        difficulty = puzzle.get("day_of_week", "Wednesday")
        randomness = random.uniform(0.5, 0.9)

        prompt = f"""Create a crossword grid:
Theme: {theme}
Size: {size[0]}x{size[1]}
Difficulty: {difficulty}
Randomness: {randomness:.2f}

Generate a crossword grid layout with theme answer placements."""

        return prompt

    def _create_grid_output(self, puzzle: Dict) -> Dict:
        """Create output data for grid generation"""
        grid = puzzle.get("grid", {})
        theme_answers = []

        # Extract theme answers with positions
        for answer_info in puzzle.get("answers", {}).get("across", []):
            if answer_info.get("is_theme", False):
                theme_answers.append({
                    "answer": answer_info["answer"],
                    "position": "across",
                    "start": answer_info["start_pos"],
                    "number": answer_info["number"],
                    "length": answer_info["length"]
                })

        for answer_info in puzzle.get("answers", {}).get("down", []):
            if answer_info.get("is_theme", False):
                theme_answers.append({
                    "answer": answer_info["answer"],
                    "position": "down",
                    "start": answer_info["start_pos"],
                    "number": answer_info["number"],
                    "length": answer_info["length"]
                })

        # Get black square positions
        black_squares = []
        grid_layout = grid.get("layout", [])
        for i, row in enumerate(grid_layout):
            for j, cell in enumerate(row):
                if cell == 0:
                    black_squares.append([i, j])

        return {
            "grid_layout": grid_layout,
            "theme_answers": theme_answers,
            "black_squares": black_squares
        }

    def _create_fill_input_prompt(self, puzzle: Dict) -> str:
        """Create input prompt for fill generation"""
        difficulty = puzzle.get("day_of_week", "Wednesday")
        size = puzzle.get("size", [15, 15])

        # Create partial grid with only theme answers
        grid_layout = puzzle.get("grid", {}).get("layout", [])
        theme_answers = []

        for answer_info in puzzle.get("answers", {}).get("across", []):
            if answer_info.get("is_theme", False):
                theme_answers.append({
                    "number": answer_info["number"],
                    "direction": "across",
                    "answer": answer_info["answer"],
                    "start_pos": answer_info["start_pos"],
                    "length": answer_info["length"]
                })

        for answer_info in puzzle.get("answers", {}).get("down", []):
            if answer_info.get("is_theme", False):
                theme_answers.append({
                    "number": answer_info["number"],
                    "direction": "down",
                    "answer": answer_info["answer"],
                    "start_pos": answer_info["start_pos"],
                    "length": answer_info["length"]
                })

        prompt = f"""Fill this crossword grid:
Size: {size[0]}x{size[1]}
Difficulty: {difficulty}

Grid layout:
{json.dumps(grid_layout, indent=2)}

Theme answers already placed:
{json.dumps(theme_answers, indent=2)}

Generate all remaining word fills to complete the puzzle."""

        return prompt

    def _create_fill_output(self, puzzle: Dict) -> Dict:
        """Create output data for fill generation"""
        filled_answers = []

        # Get all non-theme answers
        for answer_info in puzzle.get("answers", {}).get("across", []):
            if not answer_info.get("is_theme", False):
                filled_answers.append({
                    "number": answer_info["number"],
                    "direction": "across",
                    "answer": answer_info["answer"],
                    "start_pos": answer_info["start_pos"],
                    "length": answer_info["length"]
                })

        for answer_info in puzzle.get("answers", {}).get("down", []):
            if not answer_info.get("is_theme", False):
                filled_answers.append({
                    "number": answer_info["number"],
                    "direction": "down",
                    "answer": answer_info["answer"],
                    "start_pos": answer_info["start_pos"],
                    "length": answer_info["length"]
                })

        return {
            "filled_answers": filled_answers
        }

    def _create_clue_input_prompt(
        self,
        answer: str,
        difficulty: str,
        theme: str = None
    ) -> str:
        """Create input prompt for clue generation"""
        prompt = f"""Generate a crossword clue:
Answer: {answer}
Length: {len(answer)} letters
Difficulty: {difficulty}"""

        if theme:
            prompt += f"\nTheme: {theme}"

        prompt += "\n\nGenerate an appropriate crossword clue for this answer."

        return prompt

    def _split_and_save_dataset(
        self,
        dataset: List[Dict],
        model_name: str,
        description: str
    ) -> Dict:
        """
        Split dataset into train/validation and save to files
        Returns statistics
        """
        # Shuffle dataset
        random.shuffle(dataset)

        # Split
        split_idx = int(len(dataset) * self.train_split)
        train_data = dataset[:split_idx]
        val_data = dataset[split_idx:]

        # Create output directory
        output_path = self.output_dir / model_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Save datasets
        train_file = output_path / "train.jsonl"
        val_file = output_path / "val.jsonl"

        save_jsonl(train_data, str(train_file))
        save_jsonl(val_data, str(val_file))

        logger.info(f"\n{description} Dataset:")
        logger.info(f"  Train: {len(train_data)} examples -> {train_file}")
        logger.info(f"  Val:   {len(val_data)} examples -> {val_file}")

        return {
            "total": len(dataset),
            "train": len(train_data),
            "validation": len(val_data),
            "train_file": str(train_file),
            "val_file": str(val_file)
        }

    def _save_statistics(self, stats: Dict) -> None:
        """Save dataset statistics to file"""
        stats_file = self.output_dir / "dataset_statistics.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

        logger.info(f"\nDataset statistics saved to: {stats_file}")

        # Print summary
        logger.info("\n" + "="*60)
        logger.info("DATASET SUMMARY")
        logger.info("="*60)
        for model_name, model_stats in stats.items():
            logger.info(f"\n{model_name.upper()} Model:")
            logger.info(f"  Total examples: {model_stats['total']}")
            logger.info(f"  Training: {model_stats['train']}")
            logger.info(f"  Validation: {model_stats['validation']}")
        logger.info("="*60 + "\n")


def main():
    """Main entry point for dataset builder"""
    import argparse

    parser = argparse.ArgumentParser(description="Build training datasets")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to puzzles JSONL file"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    # Load puzzles
    logger.info(f"Loading puzzles from {args.input}...")
    puzzles = load_jsonl(args.input)
    logger.info(f"Loaded {len(puzzles)} puzzles")

    # Build datasets
    builder = DatasetBuilder(config_path=args.config)
    stats = builder.build_all_datasets(puzzles)

    logger.info("\nSuccess! Training datasets created.")
    logger.info("Next step: Run gcs_uploader.py to upload to Google Cloud Storage")


if __name__ == "__main__":
    main()
