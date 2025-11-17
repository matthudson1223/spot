#!/usr/bin/env python3
"""
Model training script

Submits fine-tuning jobs to Vertex AI for all three models
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vertex_trainer import VertexAITrainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Submit training jobs to Vertex AI"""
    logger.info("="*70)
    logger.info("VERTEX AI MODEL TRAINING")
    logger.info("="*70)

    try:
        trainer = VertexAITrainer()
        jobs = trainer.train_all_models(wait_for_completion=False)

        logger.info("\n" + "="*70)
        logger.info("TRAINING JOBS SUBMITTED!")
        logger.info("="*70)
        logger.info("\nNext steps:")
        logger.info("  1. Monitor training in Vertex AI console")
        logger.info("  2. Wait for all jobs to complete (may take hours)")
        logger.info("  3. Update endpoints in config.yaml")
        logger.info("  4. Run: python run_server.py (to start web interface)")
        logger.info("="*70 + "\n")

        return 0

    except ValueError as e:
        logger.error(f"\n{e}")
        logger.info("\nMake sure you have:")
        logger.info("  1. Run the data pipeline first: python run_data_pipeline.py")
        logger.info("  2. Configured your GCP project in config.yaml")
        logger.info("  3. Set up authentication: gcloud auth application-default login")
        return 1

    except Exception as e:
        logger.error(f"Training submission failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
