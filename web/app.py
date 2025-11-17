"""
FastAPI web application for crossword puzzle generation

Provides web interface and REST API for generating crossword puzzles
"""
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json
import time
import uuid
from typing import Optional, Dict
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator import CrosswordOrchestrator
from json_formatter import JSONFormatter
from pdf_generator import PDFGenerator
from utils import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Crossword Generator",
    description="Generate crossword puzzles using AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Output directories
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_DIR = OUTPUT_DIR / "pdfs"
PDF_DIR.mkdir(exist_ok=True)
JSON_DIR = OUTPUT_DIR / "json"
JSON_DIR.mkdir(exist_ok=True)

# Initialize components
config = load_config("config.yaml")
orchestrator = CrosswordOrchestrator()
json_formatter = JSONFormatter()
pdf_generator = PDFGenerator()

# Job storage (in production, use Redis or database)
jobs = {}


class GenerateRequest(BaseModel):
    """Request model for puzzle generation"""
    prompt: str
    difficulty: str = "Wednesday"
    size: str = "15x15"
    randomness: float = 0.7
    required_words: Optional[list] = None


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0-100
    message: str
    puzzle_json_url: Optional[str] = None
    pdf_download_url: Optional[str] = None
    quality_score: Optional[float] = None
    generation_time: Optional[float] = None


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve main HTML page"""
    html_path = Path(__file__).parent / "templates" / "index.html"

    if html_path.exists():
        with open(html_path, 'r') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>AI Crossword Generator</title></head>
            <body>
                <h1>AI Crossword Generator</h1>
                <p>API is running. Access the API documentation at <a href="/docs">/docs</a></p>
            </body>
        </html>
        """)


@app.post("/api/generate", response_model=JobStatus)
async def generate_crossword(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate a crossword puzzle

    Returns a job ID for tracking progress
    """
    # Create job
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Job queued",
        "created_at": time.time()
    }

    # Parse parameters
    size_parts = request.size.split("x")
    size = [int(size_parts[0]), int(size_parts[1])]

    params = {
        "difficulty": request.difficulty,
        "size": size,
        "randomness": request.randomness,
        "required_words": request.required_words or []
    }

    # Start generation in background
    background_tasks.add_task(
        generate_puzzle_task,
        job_id,
        request.prompt,
        params
    )

    logger.info(f"Created job {job_id} for prompt: {request.prompt}")

    return JobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        message="Puzzle generation started"
    )


async def generate_puzzle_task(job_id: str, prompt: str, params: Dict):
    """Background task for puzzle generation"""
    try:
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Initializing models..."

        # Generate puzzle
        jobs[job_id]["progress"] = 20
        jobs[job_id]["message"] = "Generating grid..."

        puzzle = orchestrator.generate_crossword(prompt, params)

        jobs[job_id]["progress"] = 80
        jobs[job_id]["message"] = "Creating outputs..."

        # Save JSON
        json_filename = f"puzzle_{job_id}.json"
        json_path = JSON_DIR / json_filename
        json_formatter.save_formatted_puzzle(puzzle, str(json_path))

        # Generate PDF
        pdf_filename = f"puzzle_{job_id}.pdf"
        pdf_path = PDF_DIR / pdf_filename
        pdf_generator.generate_pdf(puzzle, str(pdf_path), include_solution=True)

        # Update job with results
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Puzzle generated successfully!"
        jobs[job_id]["puzzle_json_url"] = f"/api/download/json/{json_filename}"
        jobs[job_id]["pdf_download_url"] = f"/api/download/pdf/{pdf_filename}"
        jobs[job_id]["quality_score"] = puzzle.get("quality_score", 0.0)
        jobs[job_id]["generation_time"] = puzzle.get("generation_time", 0.0)
        jobs[job_id]["puzzle_data"] = json_formatter.format_puzzle(puzzle)

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["progress"] = 0
        jobs[job_id]["message"] = f"Generation failed: {str(e)}"


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a generation job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        puzzle_json_url=job.get("puzzle_json_url"),
        pdf_download_url=job.get("pdf_download_url"),
        quality_score=job.get("quality_score"),
        generation_time=job.get("generation_time")
    )


@app.get("/api/puzzle/{job_id}")
async def get_puzzle_data(job_id: str):
    """Get puzzle data as JSON"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Puzzle not ready yet")

    return JSONResponse(content=job.get("puzzle_data", {}))


@app.get("/api/download/json/{filename}")
async def download_json(filename: str):
    """Download puzzle JSON file"""
    file_path = JSON_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/json"
    )


@app.get("/api/download/pdf/{filename}")
async def download_pdf(filename: str):
    """Download puzzle PDF file"""
    file_path = PDF_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/api/info")
async def get_info():
    """Get API information"""
    return {
        "app": "AI Crossword Generator",
        "version": "1.0.0",
        "status": "running",
        "features": {
            "puzzle_generation": True,
            "pdf_export": True,
            "json_export": True
        }
    }


if __name__ == "__main__":
    import uvicorn

    web_config = config.get("web", {})
    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8000)
    debug = web_config.get("debug", True)

    logger.info(f"Starting AI Crossword Generator API...")
    logger.info(f"Server: http://{host}:{port}")
    logger.info(f"API Docs: http://{host}:{port}/docs")

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=debug
    )
