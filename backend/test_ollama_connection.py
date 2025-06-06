"""Test script to check Ollama connectivity"""
import asyncio
import httpx
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                  handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# Ollama API URL - make sure this matches your config.py
OLLAMA_API_URL = "http://localhost:11434"

async def test_connection():
    """Test basic connectivity to Ollama"""
    try:
        logger.info(f"Testing connection to Ollama API at {OLLAMA_API_URL}")
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test API version endpoint
            version_url = f"{OLLAMA_API_URL}/api/version"
            logger.info(f"Requesting: {version_url}")
            try:
                response = await client.get(version_url)
                logger.info(f"Version response status: {response.status_code}")
                logger.info(f"Version response content: {response.text}")
                
                if response.status_code == 200:
                    logger.info("✅ Ollama API is accessible!")
                else:
                    logger.error(f"❌ Ollama API returned error status: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Ollama API version endpoint: {str(e)}")
                return False
            
            # Test models/tags endpoint
            tags_url = f"{OLLAMA_API_URL}/api/tags"
            logger.info(f"Requesting: {tags_url}")
            try:
                response = await client.get(tags_url)
                logger.info(f"Tags response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    logger.info(f"Models found: {len(models)}")
                    for model in models:
                        logger.info(f"Found model: {model['name']}")
                    
                    if not models:
                        logger.warning("⚠️ No models found in Ollama. Have you pulled any models?")
                    else:
                        logger.info("✅ Models found in Ollama!")
                else:
                    logger.error(f"❌ Failed to get models list: {response.status_code}")
                    logger.error(f"Response content: {response.text}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Ollama API tags endpoint: {str(e)}")
                return False
    
    except Exception as error:
        logger.error(f"❌ General error testing Ollama connection: {error}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_connection())
