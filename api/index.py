"""
Vercel Serverless Function entrypoint for Enterprise GenAI Strategy Engine.
Exposes the FastAPI application to Vercel's Python runtime.
"""
import sys
from pathlib import Path

# Add root directory to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app

# Export ASGI app for Vercel
__all__ = ["app"]
