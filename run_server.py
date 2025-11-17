#!/usr/bin/env python3
"""
Web server launcher

Starts the FastAPI web application
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn
from utils import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start web server"""
    logger.info("="*70)
    logger.info("AI CROSSWORD GENERATOR - WEB SERVER")
    logger.info("="*70)

    try:
        config = load_config("config.yaml")
        web_config = config.get("web", {})

        host = web_config.get("host", "0.0.0.0")
        port = web_config.get("port", 8000)
        debug = web_config.get("debug", True)

        logger.info(f"\nStarting server...")
        logger.info(f"  URL: http://{host}:{port}")
        logger.info(f"  API Docs: http://{host}:{port}/docs")
        logger.info(f"  Debug mode: {debug}")
        logger.info("\n" + "="*70 + "\n")

        uvicorn.run(
            "web.app:app",
            host=host,
            port=port,
            reload=debug
        )

    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
