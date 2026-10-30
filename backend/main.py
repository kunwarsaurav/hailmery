"""
Vercel / ASGI entrypoint for ProductShot FastAPI backend.
Re-exports the FastAPI app from app.main.
"""
import os
import warnings

# 1. Disable ONNX Runtime telemetry to prevent container hang in serverless
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

# 2. Prevent Numba from trying to lock /dev/shm (missing in Lambda/Vercel)
os.environ["NUMBA_THREADING_LAYER"] = "workqueue"
os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

warnings.filterwarnings("ignore", message="Could not obtain multiprocessing lock")

from app.main import app

__all__ = ["app"]
