"""
Crossword puzzle validators

Validates grid structure, fill quality, and overall puzzle solvability
"""
from typing import Dict, List, Tuple, Set
import logging

from utils import (
    check_rotational_symmetry,
    count_black_squares,
    is_connected,
    validate_puzzle_structure
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationResult:
    """Container for validation results"""

    def __init__(self, is_valid: bool = True):
        self.is_valid = is_valid
        self.errors = []
        self.warnings = []
        self.score = 10.0

    def add_error(self, message: str, score_penalty: float = 1.0):
        """Add an error and reduce score"""
        self.errors.append(message)
        self.is_valid = False
        self.score = max(0, self.score - score_penalty)

    def add_warning(self, message: str, score_penalty: float = 0.5):
        """Add a warning and slightly reduce score"""
        self.warnings.append(message)
        self.score = max(0, self.score - score_penalty)

    def __str__(self) -> str:
        result = f"Valid: {self.is_valid}, Score: {self.score:.1f}/10.0\n"
        if self.errors:
            result += f"Errors ({len(self.errors)}):\n"
            for error in self.errors:
                result += f"  - {error}\n"
        if self.warnings:
            result += f"Warnings ({len(self.warnings)}):\n"
            for warning in self.warnings:
                result += f"  - {warning}\n"
        return result


class GridValidator:
    """Validates crossword grid structure"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_word_length = self.config.get("min_word_length", 3)
        self.max_black_ratio = self.config.get("max_black_square_ratio", 0.20)
        self.require_symmetry = self.config.get("require_symmetry", True)
        self.require_connectivity = self.config.get("require_connectivity", True)

    def validate(self, grid_data: Dict) -> ValidationResult:
        """
        Validate grid structure

        Checks:
        - Rotational symmetry
        - Black square ratio
        - Connectivity of white squares
        - Minimum word lengths
        - No unchecked squares
        """
        result = ValidationResult()

        grid_layout = grid_data.get("grid", {}).get("layout", [])
        if not grid_layout:
            result.add_error("Empty grid layout")
            return result

        # Check symmetry
        if self.require_symmetry:
            if not check_rotational_symmetry(grid_layout):
                result.add_error("Grid lacks 180-degree rotational symmetry", 2.0)

        # Check black square ratio
        black_count, black_ratio = count_black_squares(grid_layout)
        if black_ratio > self.max_black_ratio:
            result.add_error(
                f"Too many black squares: {black_ratio:.1%} (max: {self.max_black_ratio:.1%})",
                1.5
            )

        # Check connectivity
        if self.require_connectivity:
            if not is_connected(grid_layout):
                result.add_error("White squares are not all connected", 3.0)

        # Check minimum word lengths
        word_lengths = self._get_all_word_lengths(grid_layout)
        short_words = [length for length in word_lengths if length < self.min_word_length]
        if short_words:
            result.add_error(
                f"Found {len(short_words)} words shorter than {self.min_word_length} letters",
                1.0
            )

        # Check for unchecked squares
        unchecked = self._find_unchecked_squares(grid_layout)
        if unchecked:
            result.add_warning(
                f"Found {len(unchecked)} unchecked squares (letters not in crossings)",
                0.5
            )

        # Check grid quality
        self._check_grid_quality(grid_layout, result)

        return result

    def _get_all_word_lengths(self, grid: List[List[int]]) -> List[int]:
        """Get lengths of all words in grid"""
        n = len(grid)
        if n == 0:
            return []
        m = len(grid[0])

        word_lengths = []

        # Across words
        for i in range(n):
            j = 0
            while j < m:
                if grid[i][j] == 1:
                    length = 0
                    while j < m and grid[i][j] == 1:
                        length += 1
                        j += 1
                    if length > 1:  # Don't count single letters
                        word_lengths.append(length)
                else:
                    j += 1

        # Down words
        for j in range(m):
            i = 0
            while i < n:
                if grid[i][j] == 1:
                    length = 0
                    while i < n and grid[i][j] == 1:
                        length += 1
                        i += 1
                    if length > 1:
                        word_lengths.append(length)
                else:
                    i += 1

        return word_lengths

    def _find_unchecked_squares(self, grid: List[List[int]]) -> List[Tuple[int, int]]:
        """Find squares that appear in only one word (not crossed)"""
        n = len(grid)
        if n == 0:
            return []
        m = len(grid[0])

        # Track which cells are part of across/down words
        in_across = [[False] * m for _ in range(n)]
        in_down = [[False] * m for _ in range(n)]

        # Mark across words
        for i in range(n):
            j = 0
            while j < m:
                if grid[i][j] == 1:
                    start_j = j
                    while j < m and grid[i][j] == 1:
                        j += 1
                    if j - start_j > 1:  # Word length > 1
                        for k in range(start_j, j):
                            in_across[i][k] = True
                else:
                    j += 1

        # Mark down words
        for j in range(m):
            i = 0
            while i < n:
                if grid[i][j] == 1:
                    start_i = i
                    while i < n and grid[i][j] == 1:
                        i += 1
                    if i - start_i > 1:  # Word length > 1
                        for k in range(start_i, i):
                            in_down[k][j] = True
                else:
                    i += 1

        # Find unchecked (appears in only one direction)
        unchecked = []
        for i in range(n):
            for j in range(m):
                if grid[i][j] == 1:
                    if in_across[i][j] != in_down[i][j]:  # XOR: only in one direction
                        unchecked.append((i, j))

        return unchecked

    def _check_grid_quality(self, grid: List[List[int]], result: ValidationResult):
        """Check overall grid quality factors"""
        n = len(grid)
        m = len(grid[0]) if n > 0 else 0

        # Check for blocks of black squares (3x3 or larger)
        for i in range(n - 2):
            for j in range(m - 2):
                if all(grid[i+di][j+dj] == 0 for di in range(3) for dj in range(3)):
                    result.add_warning("Found 3x3 block of black squares", 0.3)

        # Check for isolated regions
        # (In a well-designed puzzle, all regions should be accessible)


class FillValidator:
    """Validates word fill quality"""

    def __init__(self, config: Dict = None, dictionary: Set[str] = None):
        self.config = config or {}
        self.dictionary = dictionary or set()

    def validate(self, puzzle_data: Dict) -> ValidationResult:
        """
        Validate fill quality

        Checks:
        - All words exist in dictionary
        - All crossings are valid (letters match)
        - No duplicate words
        - Appropriate difficulty
        """
        result = ValidationResult()

        answers = puzzle_data.get("answers", {})
        grid = puzzle_data.get("grid", {}).get("layout", [])

        # Collect all answers
        all_answers = []
        all_answers.extend(answers.get("across", []))
        all_answers.extend(answers.get("down", []))

        # Check for duplicates
        answer_words = [ans.get("answer", "").upper() for ans in all_answers]
        duplicates = [word for word in set(answer_words) if answer_words.count(word) > 1]
        if duplicates:
            result.add_error(f"Duplicate words found: {', '.join(duplicates)}", 2.0)

        # Validate each answer
        for answer_info in all_answers:
            answer = answer_info.get("answer", "").upper()

            # Check dictionary (if provided)
            if self.dictionary and answer not in self.dictionary:
                result.add_warning(f"Word not in dictionary: {answer}", 0.3)

            # Check for fill quality issues
            if self._is_bad_fill(answer):
                result.add_warning(f"Low-quality fill: {answer}", 0.5)

        # Verify crossings
        crossing_errors = self._verify_crossings(puzzle_data)
        for error in crossing_errors:
            result.add_error(error, 2.0)

        return result

    def _is_bad_fill(self, word: str) -> bool:
        """Check if word is considered bad fill"""
        # Very short words
        if len(word) <= 2:
            return True

        # Too many vowels in a row
        vowel_runs = 0
        consonant_runs = 0
        for char in word:
            if char in "AEIOU":
                vowel_runs += 1
                consonant_runs = 0
            else:
                consonant_runs += 1
                vowel_runs = 0

            if vowel_runs >= 4 or consonant_runs >= 5:
                return True

        return False

    def _verify_crossings(self, puzzle_data: Dict) -> List[str]:
        """Verify all letter crossings match"""
        errors = []

        grid_layout = puzzle_data.get("grid", {}).get("layout", [])
        n = len(grid_layout)
        if n == 0:
            return ["Empty grid"]
        m = len(grid_layout[0])

        # Create letter grid
        letter_grid = [["" for _ in range(m)] for _ in range(n)]

        # Fill in across answers
        for answer_info in puzzle_data.get("answers", {}).get("across", []):
            answer = answer_info.get("answer", "")
            start_pos = answer_info.get("start_pos", [0, 0])
            i, j = start_pos

            for k, letter in enumerate(answer):
                if j + k < m:
                    if letter_grid[i][j + k] and letter_grid[i][j + k] != letter:
                        errors.append(
                            f"Crossing mismatch at ({i}, {j+k}): "
                            f"{letter_grid[i][j+k]} vs {letter}"
                        )
                    letter_grid[i][j + k] = letter

        # Fill in down answers and check crossings
        for answer_info in puzzle_data.get("answers", {}).get("down", []):
            answer = answer_info.get("answer", "")
            start_pos = answer_info.get("start_pos", [0, 0])
            i, j = start_pos

            for k, letter in enumerate(answer):
                if i + k < n:
                    if letter_grid[i + k][j] and letter_grid[i + k][j] != letter:
                        errors.append(
                            f"Crossing mismatch at ({i+k}, {j}): "
                            f"{letter_grid[i+k][j]} vs {letter}"
                        )
                    letter_grid[i + k][j] = letter

        return errors


class SolvabilityChecker:
    """Checks if puzzle is solvable with given clues"""

    def validate(self, puzzle_data: Dict) -> ValidationResult:
        """
        Check puzzle solvability

        Checks:
        - All answers have clues
        - Theme is coherent
        - No contradictions
        """
        result = ValidationResult()

        answers = puzzle_data.get("answers", {})
        clues = puzzle_data.get("clues", {})

        # Check that all answers have clues
        for answer_info in answers.get("across", []):
            number = str(answer_info.get("number", 0))
            if number not in clues.get("across", {}):
                result.add_error(f"Missing clue for {number} Across", 1.0)

        for answer_info in answers.get("down", []):
            number = str(answer_info.get("number", 0))
            if number not in clues.get("down", {}):
                result.add_error(f"Missing clue for {number} Down", 1.0)

        # Check theme coherence
        theme_answers = puzzle_data.get("theme_answers", [])
        if theme_answers:
            if len(theme_answers) < 2:
                result.add_warning("Theme has fewer than 2 theme answers", 0.5)

        return result


class CompletePuzzleValidator:
    """Validates complete puzzle including all aspects"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.grid_validator = GridValidator(config.get("validation", {}))
        self.fill_validator = FillValidator(config.get("validation", {}))
        self.solvability_checker = SolvabilityChecker()

    def validate(self, puzzle_data: Dict) -> ValidationResult:
        """
        Perform complete validation of puzzle

        Returns overall validation result
        """
        # First check basic structure
        is_valid, errors = validate_puzzle_structure(puzzle_data)
        if not is_valid:
            result = ValidationResult(is_valid=False)
            for error in errors:
                result.add_error(error, 1.0)
            return result

        # Validate grid
        grid_result = self.grid_validator.validate(puzzle_data)

        # Validate fill
        fill_result = self.fill_validator.validate(puzzle_data)

        # Check solvability
        solvability_result = self.solvability_checker.validate(puzzle_data)

        # Combine results
        combined = ValidationResult()
        combined.is_valid = (
            grid_result.is_valid and
            fill_result.is_valid and
            solvability_result.is_valid
        )

        # Combine errors and warnings
        combined.errors.extend(grid_result.errors)
        combined.errors.extend(fill_result.errors)
        combined.errors.extend(solvability_result.errors)

        combined.warnings.extend(grid_result.warnings)
        combined.warnings.extend(fill_result.warnings)
        combined.warnings.extend(solvability_result.warnings)

        # Calculate combined score (weighted average)
        combined.score = (
            grid_result.score * 0.4 +  # Grid is 40% of score
            fill_result.score * 0.4 +   # Fill is 40% of score
            solvability_result.score * 0.2  # Solvability is 20% of score
        )

        return combined

    def calculate_quality_score(self, puzzle_data: Dict) -> float:
        """
        Calculate overall quality score (0-10)

        Returns: Quality score
        """
        result = self.validate(puzzle_data)
        return result.score
