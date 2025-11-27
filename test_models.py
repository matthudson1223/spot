#!/usr/bin/env python3
"""
Test script to verify fine-tuned models are accessible
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator import CrosswordOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_model_initialization():
    """Test that all three models can be initialized"""
    logger.info("="*70)
    logger.info("TESTING FINE-TUNED MODEL INITIALIZATION")
    logger.info("="*70)

    try:
        orchestrator = CrosswordOrchestrator()
        orchestrator.initialize_models()

        logger.info("\n✓ All models initialized successfully!")
        logger.info("\nModel endpoints:")
        logger.info(f"  Grid Generator: {orchestrator.grid_model.model_name}")
        logger.info(f"  Fill Generator: {orchestrator.fill_model.model_name}")
        logger.info(f"  Clue Generator: {orchestrator.clue_model.model_name}")

        return True

    except Exception as e:
        logger.error(f"\n✗ Model initialization failed: {e}", exc_info=True)
        return False


def test_simple_generation():
    """Test simple generation from each model"""
    logger.info("\n" + "="*70)
    logger.info("TESTING SIMPLE GENERATION")
    logger.info("="*70)

    try:
        orchestrator = CrosswordOrchestrator()
        orchestrator.initialize_models()

        # Test grid generator with a simple prompt
        logger.info("\n[1/3] Testing Grid Generator...")
        grid_prompt = """Create a crossword grid:
Theme: Space
Size: 15x15
Difficulty: Wednesday
Randomness: 0.70

Generate a crossword grid layout with theme answer placements.
Output format: JSON"""

        try:
            response = orchestrator.grid_model.generate(grid_prompt, temperature=0.7)
            logger.info(f"✓ Grid generator responded (length: {len(response)} chars)")
            logger.info(f"Response preview: {response[:200]}...")
        except Exception as e:
            logger.error(f"✗ Grid generator failed: {e}")
            return False

        # Test fill generator
        logger.info("\n[2/3] Testing Fill Generator...")
        fill_prompt = """Fill this crossword grid with words.
Theme: Space
Output format: JSON with word list"""

        try:
            response = orchestrator.fill_model.generate(fill_prompt, temperature=0.5)
            logger.info(f"✓ Fill generator responded (length: {len(response)} chars)")
        except Exception as e:
            logger.error(f"✗ Fill generator failed: {e}")
            return False

        # Test clue generator
        logger.info("\n[3/3] Testing Clue Generator...")
        clue_prompt = """Generate a crossword clue:
Answer: ROCKET
Length: 6 letters
Difficulty: Wednesday
Theme: Space"""

        try:
            response = orchestrator.clue_model.generate(clue_prompt, temperature=0.8)
            logger.info(f"✓ Clue generator responded: '{response.strip()}'")
        except Exception as e:
            logger.error(f"✗ Clue generator failed: {e}")
            return False

        logger.info("\n✓ All model tests passed!")
        return True

    except Exception as e:
        logger.error(f"\n✗ Testing failed: {e}", exc_info=True)
        return False


def main():
    """Main test runner"""
    logger.info("\nStarting fine-tuned model verification...\n")

    # Test 1: Initialization
    if not test_model_initialization():
        logger.error("\n❌ Model initialization test FAILED")
        return 1

    # Test 2: Simple generation
    if not test_simple_generation():
        logger.error("\n❌ Generation test FAILED")
        return 1

    logger.info("\n" + "="*70)
    logger.info("✅ ALL TESTS PASSED - Models are ready to use!")
    logger.info("="*70)
    logger.info("\nNext steps:")
    logger.info("  1. Test full puzzle generation: python src/orchestrator.py")
    logger.info("  2. Start web server: python run_server.py")
    logger.info("="*70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
