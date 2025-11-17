# AI Crossword Constructor with Vertex AI

A complete AI-powered system for generating crossword puzzles from scratch using Google Cloud's Vertex AI fine-tuned models.

## Overview

This system uses **three specialized fine-tuned AI models** to generate complete, valid crossword puzzles:

1. **Grid Generator** - Creates grid layouts with theme answer placements
2. **Fill Generator** - Fills remaining words given constraints
3. **Clue Generator** - Generates creative clues for all answers

The system accepts natural language prompts like "Create a 15x15 Wednesday crossword about space exploration" and outputs complete puzzles as both JSON and PDF.

## Features

- 🎯 **Natural Language Input** - Describe your puzzle in plain English
- 🤖 **AI-Powered Generation** - Three specialized fine-tuned models
- ✅ **Quality Validation** - Comprehensive validation checks
- 📄 **Professional PDF Output** - Publication-ready crossword PDFs
- 🌐 **Web Interface** - Easy-to-use web application
- 📊 **Training Pipeline** - Complete data collection and model training workflow

## Architecture

```
User Prompt → Grid Generator → Fill Generator → Clue Generator → Validated Puzzle
                    ↓               ↓                ↓
                Theme Grid      Complete Grid    Final Puzzle
```

### Why Three Models?

- **Simpler Training** - Each task is focused and easier to learn
- **Better Control** - Can validate and adjust at each stage
- **Modularity** - Can improve or replace individual components
- **Reliability** - Failures can be isolated and retried

## Project Structure

```
crossword-constructor/
├── data/                      # Data storage
│   ├── raw/                   # Raw scraped puzzles
│   ├── training/              # Training datasets
│   │   ├── model1_grid/      # Grid generation data
│   │   ├── model2_fill/      # Fill generation data
│   │   └── model3_clues/     # Clue generation data
│   └── structured/            # Processed puzzle data
├── src/                       # Core source code
│   ├── scraper.py            # Puzzle data collection
│   ├── dataset_builder.py    # Training data preparation
│   ├── gcs_uploader.py       # GCS upload utilities
│   ├── vertex_trainer.py     # Vertex AI training
│   ├── orchestrator.py       # Puzzle generation pipeline
│   ├── validators.py         # Quality validation
│   ├── json_formatter.py     # JSON output formatting
│   ├── pdf_generator.py      # PDF generation
│   └── utils.py              # Helper functions
├── web/                       # Web application
│   ├── app.py                # FastAPI server
│   └── templates/            # HTML templates
├── models/                    # Model configurations
├── outputs/                   # Generated puzzles
├── config.yaml               # Configuration file
├── requirements.txt          # Python dependencies
├── run_data_pipeline.py      # Data collection script
├── run_training.py           # Model training script
└── run_server.py             # Web server launcher
```

## Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Platform account (for training)
- Google Cloud SDK (gcloud CLI)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd spot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure the project**

Edit `config.yaml`:
```yaml
gcp:
  project_id: "your-gcp-project-id"
  location: "us-central1"
  bucket_name: "your-bucket-name"
```

### Running Without Training (Testing Mode)

You can test the system using base models without training:

```bash
# Start the web server
python run_server.py
```

Visit http://localhost:8000 to use the web interface.

### Full Training Pipeline

For production use with fine-tuned models:

#### Step 1: Collect and Prepare Data

```bash
# Run complete data pipeline
python run_data_pipeline.py
```

This will:
- Generate 1000 synthetic puzzles (or scrape real ones)
- Build three training datasets
- Upload to Google Cloud Storage

#### Step 2: Set Up Google Cloud

```bash
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
```

#### Step 3: Train Models

```bash
# Submit training jobs to Vertex AI
python run_training.py
```

This submits three fine-tuning jobs. Monitor progress in the [Vertex AI Console](https://console.cloud.google.com/vertex-ai/training).

Training typically takes:
- Grid Generator: 2-4 hours
- Fill Generator: 2-4 hours
- Clue Generator: 3-5 hours

#### Step 4: Update Model Endpoints

After training completes, update `src/orchestrator.py` with your fine-tuned model endpoints:

```python
self.grid_model = ModelClient(
    "projects/YOUR_PROJECT/locations/us-central1/endpoints/YOUR_ENDPOINT",
    self.project_id,
    self.location
)
```

#### Step 5: Run the Web Server

```bash
python run_server.py
```

## Usage

### Web Interface

1. Navigate to http://localhost:8000
2. Enter a puzzle description (e.g., "Create a crossword about space exploration")
3. Select difficulty and size
4. Adjust creativity level
5. Click "Generate Crossword"
6. Download as PDF or JSON

### API Usage

**Generate a puzzle:**

```bash
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a crossword about space exploration",
    "difficulty": "Wednesday",
    "size": "15x15",
    "randomness": 0.7
  }'
```

**Check status:**

```bash
curl "http://localhost:8000/api/status/{job_id}"
```

**Download puzzle:**

```bash
curl "http://localhost:8000/api/download/pdf/{filename}" -o puzzle.pdf
```

### Python API

```python
from src.orchestrator import CrosswordOrchestrator

orchestrator = CrosswordOrchestrator()

puzzle = orchestrator.generate_crossword(
    user_prompt="Create a crossword about space exploration",
    params={
        "difficulty": "Wednesday",
        "size": [15, 15],
        "randomness": 0.7
    }
)

# Save outputs
from src.json_formatter import JSONFormatter
from src.pdf_generator import PDFGenerator

JSONFormatter().save_formatted_puzzle(puzzle, "puzzle.json")
PDFGenerator().generate_pdf(puzzle, "puzzle.pdf")
```

## Configuration

### config.yaml

```yaml
gcp:
  project_id: "your-project-id"
  location: "us-central1"
  bucket_name: "your-bucket-name"

scraping:
  target_count: 1000          # Number of puzzles to collect
  test_mode: true             # Use small dataset for testing

training:
  base_model_grid: "gemini-1.5-flash-002"
  base_model_fill: "gemini-1.5-flash-002"
  base_model_clues: "gemini-1.5-pro-002"
  epochs: 5
  train_split: 0.9

generation:
  max_retries: 3
  quality_threshold: 7.0      # Minimum quality score (0-10)
  default_difficulty: "Wednesday"

validation:
  min_word_length: 3
  max_black_square_ratio: 0.20
  require_symmetry: true
```

## Validation

The system performs comprehensive validation:

### Grid Validation
- ✅ 180-degree rotational symmetry
- ✅ Connected white squares
- ✅ Appropriate black square ratio (≤20%)
- ✅ Minimum word length (≥3 letters)
- ✅ No unchecked squares

### Fill Validation
- ✅ Valid word crossings
- ✅ No duplicate words
- ✅ Dictionary validation
- ✅ Quality fill (no bad letter patterns)

### Overall Quality
- ✅ All answers have clues
- ✅ Theme coherence
- ✅ Puzzle solvability
- ✅ Quality score calculation (0-10)

## Data Sources

The system supports multiple data sources:

1. **Synthetic Generation** (default)
   - Generate training puzzles programmatically
   - Good for testing and initial development
   - Use: `--source synthetic`

2. **Public Archives** (to be implemented)
   - Crossword Nexus
   - Open-source puzzle repositories
   - Use: `--source public_archive`

3. **Custom Data**
   - Upload your own puzzle collections
   - Format: JSONL with required fields

## Cost Estimates

### Google Cloud Costs (approximate)

**Data Storage:**
- Cloud Storage: ~$0.02/GB/month
- Training data: ~100MB = $0.002/month

**Model Training (one-time):**
- Gemini 1.5 Flash tuning: ~$3-5 per model
- Total for 3 models: ~$9-15

**Inference:**
- Gemini 1.5 Flash: ~$0.00025 per 1K characters
- Gemini 1.5 Pro: ~$0.00125 per 1K characters
- Per puzzle: ~$0.01-0.05

**Total monthly cost (100 puzzles/month):** ~$5-10

## Troubleshooting

### "Failed to initialize GCS client"

```bash
# Re-authenticate
gcloud auth application-default login
```

### "Model endpoint not found"

- Ensure training jobs completed successfully
- Update endpoint IDs in `src/orchestrator.py`
- Check Vertex AI console for model status

### "Puzzle validation failed"

- Lower `quality_threshold` in config.yaml
- Increase `max_retries` for more attempts
- Check validation errors in logs

### "Generation takes too long"

- Use smaller grid size (13x13 instead of 15x15)
- Lower randomness value
- Check Vertex AI quotas and limits

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Adding New Features

The modular architecture makes it easy to:
- Replace data sources (modify `src/scraper.py`)
- Add new validators (extend `src/validators.py`)
- Customize PDF output (modify `src/pdf_generator.py`)
- Add new API endpoints (extend `web/app.py`)

## Roadmap

- [ ] Support for themed crosswords
- [ ] Multi-language support
- [ ] Interactive puzzle solver
- [ ] Puzzle difficulty analyzer
- [ ] Batch generation
- [ ] Puzzle database and search
- [ ] Mobile app

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Your License Here]

## Acknowledgments

- Google Cloud Vertex AI for model training
- ReportLab for PDF generation
- FastAPI for web framework

## Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review the API documentation at `/docs`

## Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Crossword Construction Guidelines](https://www.crosswordtournament.com/more/tips.html)
- [Google Cloud Pricing](https://cloud.google.com/pricing)

---

**Built with ❤️ using Google Cloud Vertex AI**
