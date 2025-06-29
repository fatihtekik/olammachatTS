"""Test script to check Backend API routes"""
import asyncio
import httpx
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                  handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# Backend API URL
BACKEND_API_URL = "http://localhost:8000"

async def test_backend_routes():
    """Test backend API routes"""
    try:
        logger.info(f"Testing backend API at {BACKEND_API_URL}")
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test root endpoint
            root_url = f"{BACKEND_API_URL}/"
            logger.info(f"Requesting root endpoint: {root_url}")
            try:
                response = await client.get(root_url)
                logger.info(f"Root response status: {response.status_code}")
                logger.info(f"Root response content: {response.text}")
                
                if response.status_code == 200:
                    logger.info("✅ Backend root endpoint is accessible!")
                else:
                    logger.error(f"❌ Backend root endpoint returned error: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to backend root endpoint: {str(e)}")
                return False
            
            # Test Ollama status endpoint
            status_url = f"{BACKEND_API_URL}/api/v1/ollama/status"
            logger.info(f"Requesting Ollama status endpoint: {status_url}")
            try:
                response = await client.get(status_url)
                logger.info(f"Status response code: {response.status_code}")
                logger.info(f"Status response content: {response.text}")
                
                if response.status_code == 200:
                    logger.info("✅ Ollama status endpoint is accessible!")
                else:
                    logger.error(f"❌ Ollama status endpoint returned error: {response.status_code}")
                    logger.error("This suggests an issue with the API route registration.")
            except Exception as e:
                logger.error(f"❌ Failed to connect to backend Ollama status endpoint: {str(e)}")
                return False
            
            # List all API routes for debugging
            logger.info("\nTesting other API endpoints for comparison...")
            test_endpoints = [
                "/api/v1/auth/profile",
                "/api/v1/chat-sessions/",
                "/api/v1/ollama/models"
            ]
            
            for endpoint in test_endpoints:
                try:
                    url = f"{BACKEND_API_URL}{endpoint}"
                    logger.info(f"Requesting: {url}")
                    response = await client.get(url)
                    logger.info(f"Response status: {response.status_code}")
                except Exception as e:
                    logger.error(f"Error with endpoint {endpoint}: {str(e)}")
    
    except Exception as error:
        logger.error(f"❌ General error testing backend routes: {error}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_backend_routes())
