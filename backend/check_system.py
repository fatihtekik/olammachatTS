import asyncio
import httpx
import json
import sys
import os

OLLAMA_API_URL = "http://localhost:11434"
BACKEND_API_URL = "http://localhost:8000"

# ANSI colors for console output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

async def check_ollama():
    print(f"\n{BOLD}{BLUE}===== Testing Ollama API at {OLLAMA_API_URL} ====={RESET}")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check version endpoint
            try:
                print(f"{BLUE}Checking Ollama version...{RESET}")
                response = await client.get(f"{OLLAMA_API_URL}/api/version")
                if response.status_code == 200:
                    data = response.json()
                    print(f"{GREEN}✓ Ollama is running. Version: {data.get('version')}{RESET}")
                else:
                    print(f"{RED}✗ Failed to get Ollama version. Status: {response.status_code}{RESET}")
                    return False
            except Exception as e:
                print(f"{RED}✗ Cannot connect to Ollama: {str(e)}{RESET}")
                print(f"{YELLOW}Make sure Ollama is running with 'ollama serve' command{RESET}")
                return False
                
            # Check available models
            try:
                print(f"{BLUE}Checking Ollama models...{RESET}")
                response = await client.get(f"{OLLAMA_API_URL}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    if models:
                        print(f"{GREEN}✓ Found {len(models)} models:{RESET}")
                        for model in models:
                            print(f"  - {model['name']}")
                    else:
                        print(f"{YELLOW}! No models found. Use 'ollama pull <model>' to download models{RESET}")
                else:
                    print(f"{RED}✗ Failed to get models. Status: {response.status_code}{RESET}")
            except Exception as e:
                print(f"{RED}✗ Error getting models: {str(e)}{RESET}")
                
    except Exception as e:
        print(f"{RED}✗ General error testing Ollama: {str(e)}{RESET}")
        return False
        
    return True
    
async def check_backend():
    print(f"\n{BOLD}{BLUE}===== Testing Backend API at {BACKEND_API_URL} ====={RESET}")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if backend is running
            try:
                print(f"{BLUE}Checking if backend is running...{RESET}")
                response = await client.get(f"{BACKEND_API_URL}/")
                if response.status_code == 200:
                    print(f"{GREEN}✓ Backend server is running{RESET}")
                else:
                    print(f"{RED}✗ Backend server returned status: {response.status_code}{RESET}")
                    return False
            except Exception as e:
                print(f"{RED}✗ Cannot connect to backend server: {str(e)}{RESET}")
                print(f"{YELLOW}Make sure the backend is running with 'python main.py'{RESET}")
                return False
                
            # Test status endpoint
            try:
                print(f"{BLUE}Testing /api/v1/ollama/status endpoint...{RESET}")
                response = await client.get(f"{BACKEND_API_URL}/api/v1/ollama/status")
                print(f"Status code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"{GREEN}✓ Status endpoint works! Response: {json.dumps(data)}{RESET}")
                else:
                    print(f"{RED}✗ Status endpoint returned error: {response.status_code}{RESET}")
                    print(f"{YELLOW}Response: {response.text}{RESET}")
            except Exception as e:
                print(f"{RED}✗ Error testing status endpoint: {str(e)}{RESET}")
                
    except Exception as e:
        print(f"{RED}✗ General error testing backend: {str(e)}{RESET}")
        return False
        
    return True

async def main():
    print(f"{BOLD}{BLUE}====== OLLAMA CONNECTION DIAGNOSTIC TOOL ======{RESET}")
    
    ollama_ok = await check_ollama()
    backend_ok = await check_backend()
    
    print(f"\n{BOLD}{BLUE}====== DIAGNOSTIC SUMMARY ======{RESET}")
    if ollama_ok:
        print(f"{GREEN}✓ Ollama API is accessible{RESET}")
    else:
        print(f"{RED}✗ Ollama API is NOT accessible{RESET}")
        
    if backend_ok:
        print(f"{GREEN}✓ Backend server is running{RESET}")
    else:
        print(f"{RED}✗ Backend server is NOT running or has issues{RESET}")
        
    # Provide next steps
    if not ollama_ok:
        print(f"\n{YELLOW}Next steps for Ollama:{RESET}")
        print("1. Make sure Ollama is installed (https://ollama.ai/download)")
        print("2. Run 'ollama serve' to start the service")
        print("3. Run 'ollama pull <model>' to download a model (e.g., 'ollama pull phi3')")
        
    if not backend_ok:
        print(f"\n{YELLOW}Next steps for backend:{RESET}")
        print("1. Make sure dependencies are installed: 'pip install -r requirements.txt'")
        print("2. Start the backend with: 'python main.py'")
        
    if ollama_ok and backend_ok:
        print(f"\n{GREEN}Everything seems to be working correctly!{RESET}")

if __name__ == "__main__":
    asyncio.run(main())
