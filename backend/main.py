"""
Vercel / ASGI entrypoint for ProductShot FastAPI backend.
Re-exports the FastAPI app from app.main.
"""
from app.main import app

__all__ = ["app"]
