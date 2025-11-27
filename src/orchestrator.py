"""
Crossword puzzle generation orchestrator

Coordinates the three fine-tuned models to generate complete puzzles
"""
import json
import time
from typing import Dict, List, Optional
import logging

from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
import vertexai

from utils import load_config, number_grid
from validators import CompletePuzzleValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelClient:
    """Client for interacting with fine-tuned Vertex AI models"""

    def __init__(self, model_name: str, endpoint_name: str, project_id: str, location: str):
        self.model_name = model_name
        self.endpoint_name = endpoint_name
        self.project_id = project_id
        self.location = location
        self.model = None

        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=location)
        vertexai.init(project=project_id, location=location)

    def load_model(self):
        """Load the fine-tuned Gemini model"""
        try:
            # For Gemini tuned models, use GenerativeModel with the endpoint resource
            logger.info(f"Loading tuned Gemini model from endpoint: {self.endpoint_name}")

            # Use the endpoint resource name directly with GenerativeModel
            # Gemini tuned models are accessed via GenerativeModel, not Predict API
            self.model = GenerativeModel(self.endpoint_name)
            logger.info(f"✓ Loaded tuned Gemini model successfully")

        except Exception as e:
            logger.error(f"Failed to load model from endpoint {self.endpoint_name}: {e}")
            raise

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate response from tuned Gemini model"""
        if not self.model:
            self.load_model()

        try:
            # For Gemini tuned models, use generate_content() without generation config
            # The model uses the parameters it was tuned with
            logger.debug(f"Generating with prompt length: {len(prompt)}")
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            logger.error(f"Model endpoint: {self.endpoint_name}")
            logger.error(f"Prompt length: {len(prompt)} chars")
            raise


class CrosswordOrchestrator:
    """
    Main orchestrator for crossword puzzle generation

    Coordinates three models:
    1. Grid Generator - Creates grid layout and theme answers
    2. Fill Generator - Fills remaining words
    3. Clue Generator - Generates clues for all answers
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.gcp_config = self.config.get("gcp", {})
        self.generation_config = self.config.get("generation", {})

        self.project_id = self.gcp_config.get("project_id")
        self.location = self.gcp_config.get("location", "us-central1")

        # Initialize validator
        self.validator = CompletePuzzleValidator(self.config)

        # Initialize model clients (will load endpoints after training)
        self.grid_model = None
        self.fill_model = None
        self.clue_model = None

        self.max_retries = self.generation_config.get("max_retries", 3)
        self.quality_threshold = self.generation_config.get("quality_threshold", 7.0)

    def initialize_models(self):
        """Initialize all three model clients"""
        logger.info("Initializing models...")

        # Use fine-tuned Gemini models
        # Actual model and endpoint resource names from Vertex AI tuning jobs
        # Grid generator: tuning job 228650641361207296
        #   Model: projects/922813767018/locations/us-central1/models/1942114667140743168@1
        #   Endpoint: projects/922813767018/locations/us-central1/endpoints/7494226174944477184
        # Fill generator: tuning job 4152974766661173248
        #   Model: projects/922813767018/locations/us-central1/models/3297698154979262464@1
        #   Endpoint: projects/922813767018/locations/us-central1/endpoints/5408637335006871552
        # Clue generator: tuning job 167852046391705600
        #   Model: projects/922813767018/locations/us-central1/models/5004562413752680448@1
        #   Endpoint: projects/922813767018/locations/us-central1/endpoints/6741702824708538368

        # Note: Using project number (922813767018) not project ID
        project_number = "922813767018"

        self.grid_model = ModelClient(
            model_name=f"projects/{project_number}/locations/{self.location}/models/1942114667140743168@1",
            endpoint_name=f"projects/{project_number}/locations/{self.location}/endpoints/7494226174944477184",
            project_id=self.project_id,
            location=self.location
        )

        self.fill_model = ModelClient(
            model_name=f"projects/{project_number}/locations/{self.location}/models/3297698154979262464@1",
            endpoint_name=f"projects/{project_number}/locations/{self.location}/endpoints/5408637335006871552",
            project_id=self.project_id,
            location=self.location
        )

        self.clue_model = ModelClient(
            model_name=f"projects/{project_number}/locations/{self.location}/models/5004562413752680448@1",
            endpoint_name=f"projects/{project_number}/locations/{self.location}/endpoints/6741702824708538368",
            project_id=self.project_id,
            location=self.location
        )

        logger.info("Fine-tuned models initialized successfully")

    def generate_crossword(
        self,
        user_prompt: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Generate a complete crossword puzzle

        Args:
            user_prompt: Natural language description of desired puzzle
            params: Optional parameters (theme, size, difficulty, etc.)

        Returns:
            Complete puzzle dictionary
        """
        if not self.grid_model:
            self.initialize_models()

        # Parse parameters
        params = params or {}
        theme = params.get("theme", self._extract_theme_from_prompt(user_prompt))
        size = params.get("size", self.generation_config.get("default_size", [15, 15]))
        difficulty = params.get("difficulty", self.generation_config.get("default_difficulty", "Wednesday"))
        randomness = params.get("randomness", self.generation_config.get("default_randomness", 0.7))
        required_words = params.get("required_words", [])

        logger.info(f"\nGenerating crossword puzzle:")
        logger.info(f"  Theme: {theme}")
        logger.info(f"  Size: {size[0]}x{size[1]}")
        logger.info(f"  Difficulty: {difficulty}")
        logger.info(f"  Randomness: {randomness}")

        start_time = time.time()

        # Step 1: Generate grid and theme answers
        logger.info("\n[Step 1/4] Generating grid and theme answers...")
        grid_data = self._generate_grid(
            theme=theme,
            size=size,
            difficulty=difficulty,
            randomness=randomness,
            required_words=required_words
        )

        # Step 2: Validate grid
        logger.info("\n[Step 2/4] Validating grid...")
        if not self._validate_grid(grid_data):
            logger.warning("Grid validation failed, regenerating...")
            grid_data = self._generate_grid(theme, size, difficulty, randomness, required_words)

        # Step 3: Fill remaining words
        logger.info("\n[Step 3/4] Filling remaining words...")
        complete_puzzle = self._fill_puzzle(grid_data, difficulty)

        # Step 4: Generate clues
        logger.info("\n[Step 4/4] Generating clues...")
        complete_puzzle = self._generate_clues(complete_puzzle, theme, difficulty)

        # Final validation
        logger.info("\nPerforming final validation...")
        validation_result = self.validator.validate(complete_puzzle)

        if not validation_result.is_valid:
            logger.error("Puzzle failed final validation!")
            logger.error(str(validation_result))
            raise ValueError("Generated puzzle is invalid")

        # Calculate quality score
        quality_score = validation_result.score
        complete_puzzle["quality_score"] = quality_score

        generation_time = time.time() - start_time
        complete_puzzle["generation_time"] = round(generation_time, 2)

        logger.info(f"\n✓ Puzzle generated successfully!")
        logger.info(f"  Quality score: {quality_score:.1f}/10")
        logger.info(f"  Generation time: {generation_time:.1f}s")

        return complete_puzzle

    def _generate_grid(
        self,
        theme: str,
        size: List[int],
        difficulty: str,
        randomness: float,
        required_words: List[str]
    ) -> Dict:
        """Generate grid layout with theme answers"""
        prompt = f"""Create a crossword grid:
Theme: {theme}
Size: {size[0]}x{size[1]}
Difficulty: {difficulty}
Randomness: {randomness:.2f}

Generate a crossword grid layout with theme answer placements.
The output should be valid JSON with this structure:
{{
    "grid_layout": [[1,1,0,1,...], ...],
    "theme_answers": [
        {{"answer": "WORD", "position": "across", "start": [row, col], "number": N, "length": L}}
    ],
    "black_squares": [[row, col], ...]
}}

Ensure 180-degree rotational symmetry and valid crossword structure."""

        if required_words:
            prompt += f"\n\nRequired theme words: {', '.join(required_words)}"

        response = self.grid_model.generate(prompt, temperature=randomness)

        try:
            grid_data = json.loads(self._extract_json(response))

            # Add metadata
            grid_data["theme"] = theme
            grid_data["size"] = size
            grid_data["difficulty"] = difficulty

            # Number the grid
            grid_layout = grid_data.get("grid_layout", [])
            grid_numbers = number_grid(grid_layout)

            grid_data["grid"] = {
                "layout": grid_layout,
                "numbers": grid_numbers
            }

            return grid_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse grid response: {e}")
            logger.error(f"Response: {response}")
            raise

    def _fill_puzzle(self, grid_data: Dict, difficulty: str) -> Dict:
        """Fill puzzle with remaining words"""
        prompt = f"""Fill this crossword grid:
Size: {grid_data['size'][0]}x{grid_data['size'][1]}
Difficulty: {difficulty}

Grid layout:
{json.dumps(grid_data['grid']['layout'], indent=2)}

Theme answers already placed:
{json.dumps(grid_data.get('theme_answers', []), indent=2)}

Generate all remaining word fills to complete the puzzle.
Output should be valid JSON:
{{
    "filled_answers": [
        {{"number": N, "direction": "across/down", "answer": "WORD", "start_pos": [row, col], "length": L}}
    ]
}}"""

        response = self.fill_model.generate(prompt, temperature=0.5)

        try:
            fill_data = json.loads(self._extract_json(response))

            # Combine theme answers and filled answers
            all_answers = {"across": [], "down": []}

            # Add theme answers
            for theme_ans in grid_data.get("theme_answers", []):
                direction = theme_ans["position"]
                all_answers[direction].append({
                    "number": theme_ans["number"],
                    "answer": theme_ans["answer"],
                    "start_pos": theme_ans["start"],
                    "length": theme_ans["length"],
                    "is_theme": True
                })

            # Add filled answers
            for filled_ans in fill_data.get("filled_answers", []):
                direction = filled_ans["direction"]
                all_answers[direction].append({
                    "number": filled_ans["number"],
                    "answer": filled_ans["answer"],
                    "start_pos": filled_ans["start_pos"],
                    "length": filled_ans["length"],
                    "is_theme": False
                })

            # Create complete puzzle structure
            complete_puzzle = {
                "puzzle_id": f"generated_{int(time.time())}",
                "date": time.strftime("%Y-%m-%d"),
                "day_of_week": difficulty,
                "size": grid_data["size"],
                "theme": grid_data["theme"],
                "grid": grid_data["grid"],
                "answers": all_answers,
                "theme_answers": [ans["answer"] for ans in grid_data.get("theme_answers", [])]
            }

            return complete_puzzle

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse fill response: {e}")
            raise

    def _generate_clues(self, puzzle: Dict, theme: str, difficulty: str) -> Dict:
        """Generate clues for all answers"""
        clues = {"across": {}, "down": {}}

        all_answers = []
        all_answers.extend([(ans, "across") for ans in puzzle["answers"]["across"]])
        all_answers.extend([(ans, "down") for ans in puzzle["answers"]["down"]])

        for answer_info, direction in all_answers:
            answer = answer_info["answer"]
            number = answer_info["number"]
            is_theme = answer_info.get("is_theme", False)

            prompt = f"""Generate a crossword clue:
Answer: {answer}
Length: {len(answer)} letters
Difficulty: {difficulty}"""

            if is_theme:
                prompt += f"\nTheme: {theme}"

            prompt += "\n\nGenerate an appropriate crossword clue for this answer."

            clue = self.clue_model.generate(prompt, temperature=0.8).strip()

            clues[direction][str(number)] = clue

        puzzle["clues"] = clues
        return puzzle

    def _validate_grid(self, grid_data: Dict) -> bool:
        """Validate generated grid"""
        from validators import GridValidator

        validator = GridValidator(self.config.get("validation", {}))
        result = validator.validate({"grid": grid_data.get("grid", {})})

        if not result.is_valid:
            logger.warning(f"Grid validation failed: {result}")
            return False

        return True

    def _extract_theme_from_prompt(self, prompt: str) -> str:
        """Extract theme from user prompt using simple heuristics"""
        # Simple extraction - in production, could use NLP
        if "about" in prompt.lower():
            parts = prompt.lower().split("about")
            if len(parts) > 1:
                theme = parts[1].strip().strip(".")
                return theme.title()

        return "General Knowledge"

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text"""
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1

        if start >= 0 and end > start:
            return text[start:end]

        return text


def main():
    """Test orchestrator"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate crossword puzzle")
    parser.add_argument(
        "--prompt",
        default="Create a crossword about space exploration",
        help="Puzzle generation prompt"
    )
    parser.add_argument(
        "--difficulty",
        default="Wednesday",
        choices=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        help="Puzzle difficulty"
    )
    parser.add_argument(
        "--size",
        default="15x15",
        help="Grid size (e.g., 15x15 or 21x21)"
    )

    args = parser.parse_args()

    # Parse size
    size_parts = args.size.split("x")
    size = [int(size_parts[0]), int(size_parts[1])]

    orchestrator = CrosswordOrchestrator()

    params = {
        "difficulty": args.difficulty,
        "size": size
    }

    puzzle = orchestrator.generate_crossword(args.prompt, params)

    # Save puzzle
    from utils import save_json
    output_file = f"data/generated_{int(time.time())}.json"
    save_json(puzzle, output_file)

    logger.info(f"\nPuzzle saved to: {output_file}")


if __name__ == "__main__":
    main()
