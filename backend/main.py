"""
ASGI entrypoint for ProductShot FastAPI backend.
Works on Railway (persistent container) and any ASGI host.
"""
import os
import warnings

# Suppress ONNX telemetry write attempts (harmless but noisy)
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

# Prevent Numba from trying to lock /dev/shm
os.environ["NUMBA_THREADING_LAYER"] = "workqueue"
os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

warnings.filterwarnings("ignore", message="Could not obtain multiprocessing lock")

from app.main import app

__all__ = ["app"]
