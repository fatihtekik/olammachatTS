"""Script to debug FastAPI routes"""
from fastapi import FastAPI
from fastapi.routing import APIRouter
import importlib
import sys
import os

# Add the parent directory to the system path to allow importing from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the application
from main import app

def print_routes(app_or_router, prefix=''):
    """Recursively print all routes registered in the application"""
    for route in app_or_router.routes:
        if isinstance(route, APIRouter):
            print_routes(route, prefix=f"{prefix}{route.prefix}")
        else:
            methods = route.methods or {'GET'}
            print(f"{', '.join(methods):<10} {prefix}{route.path}")

if __name__ == "__main__":
    print("\n=== All Registered Routes ===")
    print_routes(app)
    print("\n=== End of Routes ===")
