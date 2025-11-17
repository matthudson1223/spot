"""
Vertex AI model trainer

Submits fine-tuning jobs to Vertex AI for all three crossword models
"""
import time
import yaml
from pathlib import Path
from typing import Dict, Optional
import logging

from google.cloud import aiplatform
from google.api_core import exceptions

from utils import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VertexAITrainer:
    """
    Handles Vertex AI model fine-tuning jobs
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.gcp_config = self.config.get("gcp", {})
        self.training_config = self.config.get("training", {})

        self.project_id = self.gcp_config.get("project_id")
        self.location = self.gcp_config.get("location", "us-central1")
        self.bucket_name = self.gcp_config.get("bucket_name")

        if not self.project_id or self.project_id == "your-project-id":
            raise ValueError("Please set your GCP project_id in config.yaml")

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        logger.info(f"Initialized Vertex AI: {self.project_id} ({self.location})")

        # Load GCS URIs
        self.gcs_uris = self._load_gcs_uris()

    def _load_gcs_uris(self) -> Dict:
        """Load GCS URIs from saved file"""
        uris_file = Path("models/gcs_uris.yaml")
        if not uris_file.exists():
            raise ValueError(
                f"GCS URIs file not found: {uris_file}\n"
                "Please run gcs_uploader.py first"
            )

        with open(uris_file, 'r') as f:
            return yaml.safe_load(f)

    def submit_training_job(
        self,
        model_name: str,
        display_name: str,
        training_data_uri: str,
        validation_data_uri: str,
        base_model: str,
        epochs: int = 5,
        learning_rate_multiplier: float = 1.0
    ) -> aiplatform.Model:
        """
        Submit a fine-tuning job to Vertex AI

        Args:
            model_name: Internal model name (e.g., "model1_grid")
            display_name: Display name for the model
            training_data_uri: GCS URI for training data
            validation_data_uri: GCS URI for validation data
            base_model: Base model to fine-tune
            epochs: Number of training epochs
            learning_rate_multiplier: Learning rate adjustment

        Returns:
            Trained model object
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"Submitting training job: {display_name}")
        logger.info(f"{'='*70}")
        logger.info(f"Base model: {base_model}")
        logger.info(f"Training data: {training_data_uri}")
        logger.info(f"Validation data: {validation_data_uri}")
        logger.info(f"Epochs: {epochs}")
        logger.info(f"Learning rate multiplier: {learning_rate_multiplier}")

        try:
            # Create tuning job
            # Note: The exact API may vary based on Vertex AI version
            # This is a template - adjust based on current Vertex AI SDK

            logger.info("\nCreating tuning job...")

            # For Gemini models, use the PipelineJob approach
            tuning_job = aiplatform.PipelineJob(
                display_name=display_name,
                template_path="https://us-kfp.pkg.dev/ml-pipeline/\
large-language-model-pipelines/tune-large-model/v2.0.0",
                parameter_values={
                    "project": self.project_id,
                    "location": self.location,
                    "large_model_reference": base_model,
                    "train_steps": epochs * 100,  # Adjust as needed
                    "learning_rate_multiplier": learning_rate_multiplier,
                    "dataset_uri": training_data_uri,
                    "evaluation_data_uri": validation_data_uri,
                    "model_display_name": display_name,
                },
                enable_caching=False,
            )

            logger.info("Submitting job to Vertex AI...")
            tuning_job.submit()

            logger.info(f"\n✓ Training job submitted!")
            logger.info(f"Job name: {tuning_job.resource_name}")
            logger.info(f"Job state: {tuning_job.state}")
            logger.info(f"\nMonitor job at:")
            logger.info(f"https://console.cloud.google.com/vertex-ai/training/\
training-pipelines?project={self.project_id}")

            return tuning_job

        except Exception as e:
            logger.error(f"Failed to submit training job: {e}")
            logger.error("\nTroubleshooting:")
            logger.error("1. Check that Vertex AI API is enabled")
            logger.error("2. Verify your GCS URIs are correct")
            logger.error("3. Ensure you have proper IAM permissions")
            logger.error("4. Check that the base model name is valid")
            raise

    def train_all_models(self, wait_for_completion: bool = False) -> Dict[str, any]:
        """
        Submit training jobs for all three models

        Args:
            wait_for_completion: If True, wait for all jobs to complete

        Returns:
            Dictionary with job information
        """
        logger.info("\n" + "="*70)
        logger.info("TRAINING ALL CROSSWORD MODELS")
        logger.info("="*70)

        jobs = {}

        # Model 1: Grid Generator
        logger.info("\n[1/3] Training Grid Generator...")
        try:
            grid_job = self.submit_training_job(
                model_name="model1_grid",
                display_name="crossword-grid-generator",
                training_data_uri=self.gcs_uris["model1_grid"]["train"],
                validation_data_uri=self.gcs_uris["model1_grid"]["validation"],
                base_model=self.training_config.get("base_model_grid", "gemini-1.5-flash-002"),
                epochs=self.training_config.get("epochs", 5),
                learning_rate_multiplier=self.training_config.get("learning_rate_multiplier", 1.0)
            )
            jobs["grid_generator"] = grid_job
            logger.info("✓ Grid generator job submitted")
        except Exception as e:
            logger.error(f"✗ Grid generator job failed: {e}")
            jobs["grid_generator"] = None

        # Small delay between submissions
        time.sleep(5)

        # Model 2: Fill Generator
        logger.info("\n[2/3] Training Fill Generator...")
        try:
            fill_job = self.submit_training_job(
                model_name="model2_fill",
                display_name="crossword-fill-generator",
                training_data_uri=self.gcs_uris["model2_fill"]["train"],
                validation_data_uri=self.gcs_uris["model2_fill"]["validation"],
                base_model=self.training_config.get("base_model_fill", "gemini-1.5-flash-002"),
                epochs=self.training_config.get("epochs", 5),
                learning_rate_multiplier=self.training_config.get("learning_rate_multiplier", 1.0)
            )
            jobs["fill_generator"] = fill_job
            logger.info("✓ Fill generator job submitted")
        except Exception as e:
            logger.error(f"✗ Fill generator job failed: {e}")
            jobs["fill_generator"] = None

        # Small delay between submissions
        time.sleep(5)

        # Model 3: Clue Generator
        logger.info("\n[3/3] Training Clue Generator...")
        try:
            clue_job = self.submit_training_job(
                model_name="model3_clues",
                display_name="crossword-clue-generator",
                training_data_uri=self.gcs_uris["model3_clues"]["train"],
                validation_data_uri=self.gcs_uris["model3_clues"]["validation"],
                base_model=self.training_config.get("base_model_clues", "gemini-1.5-pro-002"),
                epochs=self.training_config.get("epochs", 3),
                learning_rate_multiplier=self.training_config.get("learning_rate_multiplier", 1.0)
            )
            jobs["clue_generator"] = clue_job
            logger.info("✓ Clue generator job submitted")
        except Exception as e:
            logger.error(f"✗ Clue generator job failed: {e}")
            jobs["clue_generator"] = None

        # Print summary
        self._print_jobs_summary(jobs)

        # Optionally wait for completion
        if wait_for_completion:
            self._wait_for_jobs(jobs)

        # Save job information
        self._save_job_info(jobs)

        return jobs

    def _wait_for_jobs(self, jobs: Dict) -> None:
        """Wait for all training jobs to complete"""
        logger.info("\nWaiting for all jobs to complete...")
        logger.info("This may take several hours. You can safely exit and check status later.")

        for job_name, job in jobs.items():
            if job is None:
                continue

            logger.info(f"\nWaiting for {job_name}...")
            try:
                job.wait()
                logger.info(f"✓ {job_name} completed: {job.state}")
            except Exception as e:
                logger.error(f"✗ {job_name} failed: {e}")

    def _print_jobs_summary(self, jobs: Dict) -> None:
        """Print summary of submitted jobs"""
        logger.info("\n" + "="*70)
        logger.info("TRAINING JOBS SUMMARY")
        logger.info("="*70)

        for job_name, job in jobs.items():
            if job:
                logger.info(f"\n{job_name}:")
                logger.info(f"  Status: Submitted")
                logger.info(f"  Job: {job.resource_name}")
            else:
                logger.info(f"\n{job_name}:")
                logger.info(f"  Status: Failed to submit")

        logger.info("\n" + "="*70)
        logger.info("Monitor all jobs at:")
        logger.info(f"https://console.cloud.google.com/vertex-ai/training/\
training-pipelines?project={self.project_id}")
        logger.info("="*70 + "\n")

    def _save_job_info(self, jobs: Dict) -> None:
        """Save job information to file"""
        output_file = Path("models/training_jobs.yaml")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        job_info = {}
        for job_name, job in jobs.items():
            if job:
                job_info[job_name] = {
                    "resource_name": job.resource_name,
                    "display_name": job.display_name,
                    "state": str(job.state),
                    "created_time": str(job.create_time) if hasattr(job, 'create_time') else None
                }

        with open(output_file, 'w') as f:
            yaml.dump(job_info, f, default_flow_style=False)

        logger.info(f"Job information saved to: {output_file}")

    def check_job_status(self, job_resource_name: str) -> str:
        """Check status of a training job"""
        try:
            job = aiplatform.PipelineJob.get(job_resource_name)
            return job.state
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return "UNKNOWN"


def main():
    """Main entry point for Vertex AI trainer"""
    import argparse

    parser = argparse.ArgumentParser(description="Train models on Vertex AI")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for all jobs to complete"
    )

    args = parser.parse_args()

    trainer = VertexAITrainer(config_path=args.config)
    jobs = trainer.train_all_models(wait_for_completion=args.wait)

    logger.info("\nTraining jobs submitted successfully!")
    logger.info("Check the Vertex AI console for progress.")


if __name__ == "__main__":
    main()
