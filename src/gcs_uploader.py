"""
Google Cloud Storage uploader for training datasets

Uploads training data to GCS for Vertex AI model training
"""
import os
from pathlib import Path
from typing import Dict, List
import logging

from google.cloud import storage
from google.api_core import exceptions

from utils import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GCSUploader:
    """
    Handles uploading training datasets to Google Cloud Storage
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.gcp_config = self.config.get("gcp", {})

        self.project_id = self.gcp_config.get("project_id")
        self.bucket_name = self.gcp_config.get("bucket_name")
        self.location = self.gcp_config.get("location", "us-central1")

        if not self.project_id or self.project_id == "your-project-id":
            raise ValueError(
                "Please set your GCP project_id in config.yaml"
            )

        if not self.bucket_name or self.bucket_name == "your-project-crossword-training":
            logger.warning(
                "Using default bucket name. Consider setting a custom bucket_name in config.yaml"
            )
            self.bucket_name = f"{self.project_id}-crossword-training"

        # Initialize GCS client
        try:
            self.storage_client = storage.Client(project=self.project_id)
            logger.info(f"Connected to GCP project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            logger.error("Make sure you have:")
            logger.error("  1. Installed gcloud CLI")
            logger.error("  2. Run: gcloud auth application-default login")
            logger.error("  3. Set correct project: gcloud config set project PROJECT_ID")
            raise

    def create_bucket_if_not_exists(self) -> storage.Bucket:
        """Create GCS bucket if it doesn't exist"""
        try:
            bucket = self.storage_client.get_bucket(self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
            return bucket
        except exceptions.NotFound:
            logger.info(f"Creating bucket: {self.bucket_name}")
            bucket = self.storage_client.create_bucket(
                self.bucket_name,
                location=self.location
            )
            logger.info(f"Created bucket: {self.bucket_name}")
            return bucket

    def upload_file(
        self,
        local_path: str,
        gcs_path: str,
        bucket: storage.Bucket = None
    ) -> str:
        """
        Upload a single file to GCS

        Returns: GCS URI (gs://bucket/path)
        """
        if bucket is None:
            bucket = self.storage_client.bucket(self.bucket_name)

        blob = bucket.blob(gcs_path)

        logger.info(f"Uploading {local_path} -> gs://{self.bucket_name}/{gcs_path}")
        blob.upload_from_filename(local_path)

        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded successfully: {gcs_uri}")

        return gcs_uri

    def upload_training_datasets(self) -> Dict[str, Dict[str, str]]:
        """
        Upload all training datasets to GCS

        Returns: Dictionary with GCS URIs for each dataset
        """
        logger.info("Starting upload of training datasets...")

        # Create bucket
        bucket = self.create_bucket_if_not_exists()

        training_dir = Path("data/training")
        if not training_dir.exists():
            raise ValueError(f"Training directory not found: {training_dir}")

        # Upload datasets for each model
        gcs_uris = {}

        models = ["model1_grid", "model2_fill", "model3_clues"]

        for model in models:
            model_dir = training_dir / model
            if not model_dir.exists():
                logger.warning(f"Model directory not found: {model_dir}")
                continue

            logger.info(f"\nUploading {model} datasets...")

            train_file = model_dir / "train.jsonl"
            val_file = model_dir / "val.jsonl"

            model_uris = {}

            # Upload training file
            if train_file.exists():
                gcs_path = f"training/{model}/train.jsonl"
                train_uri = self.upload_file(str(train_file), gcs_path, bucket)
                model_uris["train"] = train_uri
            else:
                logger.warning(f"Train file not found: {train_file}")

            # Upload validation file
            if val_file.exists():
                gcs_path = f"training/{model}/val.jsonl"
                val_uri = self.upload_file(str(val_file), gcs_path, bucket)
                model_uris["validation"] = val_uri
            else:
                logger.warning(f"Validation file not found: {val_file}")

            gcs_uris[model] = model_uris

        # Save GCS URIs to file
        self._save_gcs_uris(gcs_uris)

        return gcs_uris

    def _save_gcs_uris(self, uris: Dict[str, Dict[str, str]]) -> None:
        """Save GCS URIs to YAML file for reference"""
        import yaml

        output_file = Path("models/gcs_uris.yaml")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            yaml.dump(uris, f, default_flow_style=False)

        logger.info(f"\nGCS URIs saved to: {output_file}")

    def verify_uploads(self, gcs_uris: Dict[str, Dict[str, str]]) -> bool:
        """Verify that all files were uploaded successfully"""
        logger.info("\nVerifying uploads...")

        bucket = self.storage_client.bucket(self.bucket_name)
        all_verified = True

        for model, uris in gcs_uris.items():
            logger.info(f"\nVerifying {model}:")

            for dataset_type, uri in uris.items():
                # Extract blob path from URI
                blob_path = uri.replace(f"gs://{self.bucket_name}/", "")
                blob = bucket.blob(blob_path)

                if blob.exists():
                    size = blob.size
                    logger.info(f"  ✓ {dataset_type}: {uri} ({size:,} bytes)")
                else:
                    logger.error(f"  ✗ {dataset_type}: {uri} NOT FOUND")
                    all_verified = False

        return all_verified

    def print_upload_summary(self, gcs_uris: Dict[str, Dict[str, str]]) -> None:
        """Print summary of uploaded datasets"""
        logger.info("\n" + "="*70)
        logger.info("UPLOAD SUMMARY")
        logger.info("="*70)

        for model, uris in gcs_uris.items():
            logger.info(f"\n{model}:")
            for dataset_type, uri in uris.items():
                logger.info(f"  {dataset_type}: {uri}")

        logger.info("\n" + "="*70)
        logger.info("Next steps:")
        logger.info("1. Go to Google Cloud Console")
        logger.info("2. Navigate to Vertex AI > Training")
        logger.info("3. Use these GCS URIs to create fine-tuning jobs")
        logger.info("4. Or run: python src/vertex_trainer.py")
        logger.info("="*70 + "\n")


def main():
    """Main entry point for GCS uploader"""
    import argparse

    parser = argparse.ArgumentParser(description="Upload training datasets to GCS")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing uploads"
    )

    args = parser.parse_args()

    uploader = GCSUploader(config_path=args.config)

    if args.verify_only:
        # Load existing URIs and verify
        import yaml
        uris_file = Path("models/gcs_uris.yaml")
        if uris_file.exists():
            with open(uris_file, 'r') as f:
                gcs_uris = yaml.safe_load(f)
            uploader.verify_uploads(gcs_uris)
        else:
            logger.error(f"URIs file not found: {uris_file}")
    else:
        # Upload datasets
        gcs_uris = uploader.upload_training_datasets()

        # Verify uploads
        if uploader.verify_uploads(gcs_uris):
            logger.info("\n✓ All uploads verified successfully!")
        else:
            logger.error("\n✗ Some uploads failed verification")

        # Print summary
        uploader.print_upload_summary(gcs_uris)


if __name__ == "__main__":
    main()
