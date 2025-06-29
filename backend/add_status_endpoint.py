"""
Fix for status endpoint to ensure it's publicly accessible
"""

from fastapi import FastAPI
import sys
import os
from typing import Dict, Any
import logging

# Configure the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import necessary modules
from app.services.ollama_service import test_connection

# Create logger
logger = logging.getLogger(__name__)

def add_status_endpoint(app: FastAPI) -> None:
    """
    Add the /api/v1/ollama/status endpoint directly to the application
    This ensures it's available without authentication
    """
    @app.get("/api/v1/ollama/status", status_code=200, tags=["ollama"])
    async def check_ollama_status():
        """
        Check the status of the connection to Ollama.
        This endpoint is accessible without authentication.
        """
        try:
            logger.info("Checking Ollama connection status...")
            is_connected = await test_connection()
            logger.info(f"Ollama connection status: {'connected' if is_connected else 'disconnected'}")
            return {"status": "connected" if is_connected else "disconnected"}
        except Exception as e:
            logger.error(f"Error checking Ollama status: {e}")
            return {"status": "disconnected", "error": str(e)}

if __name__ == "__main__":
    print("This is a module to be imported, not run directly")
