#!/usr/bin/env python3
"""
Data collection and preparation pipeline

Runs the complete data pipeline:
1. Scrape/generate puzzles
2. Build training datasets
3. Upload to GCS
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper import CrosswordScraper
from dataset_builder import DatasetBuilder
from gcs_uploader import GCSUploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run complete data pipeline"""
    logger.info("="*70)
    logger.info("CROSSWORD AI DATA PIPELINE")
    logger.info("="*70)

    # Step 1: Scrape/Generate Puzzles
    logger.info("\n[STEP 1/3] Collecting puzzle data...")
    logger.info("-" * 70)

    scraper = CrosswordScraper()
    puzzles_file = scraper.scrape_and_save(source="synthetic")

    if not puzzles_file:
        logger.error("Failed to collect puzzles. Exiting.")
        return 1

    # Step 2: Build Training Datasets
    logger.info("\n[STEP 2/3] Building training datasets...")
    logger.info("-" * 70)

    puzzles = scraper.load_puzzles(puzzles_file)
    builder = DatasetBuilder()
    stats = builder.build_all_datasets(puzzles)

    logger.info(f"Built {sum(s['total'] for s in stats.values())} training examples")

    # Step 3: Upload to GCS
    logger.info("\n[STEP 3/3] Uploading to Google Cloud Storage...")
    logger.info("-" * 70)

    try:
        uploader = GCSUploader()
        gcs_uris = uploader.upload_training_datasets()

        if uploader.verify_uploads(gcs_uris):
            logger.info("\n✓ All uploads verified successfully!")
        else:
            logger.error("\n✗ Some uploads failed verification")
            return 1

        uploader.print_upload_summary(gcs_uris)

    except Exception as e:
        logger.error(f"GCS upload failed: {e}")
        logger.info("\nYou can skip this step for local testing.")
        logger.info("To use GCS, make sure to:")
        logger.info("  1. Set up GCP project in config.yaml")
        logger.info("  2. Run: gcloud auth application-default login")
        return 1

    logger.info("\n" + "="*70)
    logger.info("DATA PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("="*70)
    logger.info("\nNext steps:")
    logger.info("  1. Review the datasets in data/training/")
    logger.info("  2. Run: python run_training.py (to train models on Vertex AI)")
    logger.info("  3. Or skip training and test locally with base models")
    logger.info("="*70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
