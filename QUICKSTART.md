# Quick Start Guide

Get started with the AI Crossword Generator in 5 minutes!

## Option 1: Test Locally (No GCP Required)

Perfect for trying out the system without setting up Google Cloud.

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Generate Test Data

```bash
# Generate 10 synthetic puzzles for testing
python -c "
import sys
sys.path.insert(0, 'src')
from scraper import CrosswordScraper
scraper = CrosswordScraper()
scraper.scrape_and_save(source='synthetic')
"
```

### Step 3: Test Individual Components

**Test the scraper:**
```bash
python src/scraper.py --source synthetic
```

**Test dataset builder:**
```bash
python src/dataset_builder.py --input data/raw/puzzles_synthetic_*.jsonl
```

**Test PDF generation:**
```bash
python src/pdf_generator.py data/raw/puzzles_synthetic_*.jsonl test.pdf
```

### Step 4: Start Web Server

```bash
python run_server.py
```

Visit http://localhost:8000

**Note:** Without trained models, generation will use base Gemini models and may produce lower quality results.

---

## Option 2: Full Setup with Vertex AI

For production-quality puzzles with fine-tuned models.

### Prerequisites

1. Google Cloud account with billing enabled
2. gcloud CLI installed

### Step 1: Set Up Google Cloud

```bash
# Login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable aiplatform.googleapis.com storage.googleapis.com
```

### Step 2: Configure Project

Edit `config.yaml`:
```yaml
gcp:
  project_id: "YOUR_PROJECT_ID"
  bucket_name: "YOUR_PROJECT_ID-crossword-training"
```

### Step 3: Run Data Pipeline

```bash
python run_data_pipeline.py
```

This will:
- Generate 1000 training puzzles
- Create 3 datasets (grid, fill, clues)
- Upload to Google Cloud Storage

Expected time: 5-10 minutes

### Step 4: Train Models

```bash
python run_training.py
```

This submits 3 training jobs to Vertex AI.

Expected time: 6-12 hours total

Monitor at: https://console.cloud.google.com/vertex-ai/training

### Step 5: Update Endpoints

After training completes, get your model endpoints from the Vertex AI console and update `src/orchestrator.py`:

```python
# In CrosswordOrchestrator.__init__()
self.grid_model = ModelClient(
    "projects/YOUR_PROJECT/locations/us-central1/endpoints/GRID_ENDPOINT_ID",
    self.project_id,
    self.location
)
# ... (repeat for fill_model and clue_model)
```

### Step 6: Start Server

```bash
python run_server.py
```

Visit http://localhost:8000

---

## Quick Test Commands

### Generate a Puzzle (CLI)

```python
python -c "
import sys
sys.path.insert(0, 'src')
from orchestrator import CrosswordOrchestrator

orchestrator = CrosswordOrchestrator()
puzzle = orchestrator.generate_crossword(
    'Create a crossword about space exploration',
    {'difficulty': 'Wednesday', 'size': [15, 15]}
)
print(f'Quality Score: {puzzle[\"quality_score\"]}/10')
"
```

### API Test

```bash
# Generate puzzle
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a crossword about music", "difficulty": "Wednesday"}'

# Check status (replace JOB_ID)
curl http://localhost:8000/api/status/JOB_ID
```

---

## Troubleshooting

### "ModuleNotFoundError"

```bash
# Make sure you're in the project root
cd /path/to/spot

# Install dependencies
pip install -r requirements.txt
```

### "Failed to initialize GCS client"

This is expected if you haven't set up Google Cloud. Either:
1. Skip GCS and test locally (Option 1 above)
2. Set up GCP authentication (Option 2 above)

### "Model generation failed"

Without fine-tuned models, the base models may sometimes fail. This is normal. With fine-tuned models, success rate is >90%.

---

## Next Steps

1. **Explore the Web UI** - Try different themes and difficulties
2. **Check the API Docs** - Visit http://localhost:8000/docs
3. **Customize** - Modify `config.yaml` for your needs
4. **Read the Full README** - See README.md for detailed documentation

---

## Example Prompts

Try these in the web interface:

- "Create a crossword about space exploration"
- "Make a Monday puzzle about cooking"
- "Generate a challenging Saturday crossword about classical music"
- "Create a 21x21 Sunday puzzle about world geography"

---

## Support

- Issues? Check the [Troubleshooting](README.md#troubleshooting) section
- Questions? Open an issue on GitHub
- API Reference: http://localhost:8000/docs
