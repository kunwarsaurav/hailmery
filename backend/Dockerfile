FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ONNX Runtime and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Pre-download the silueta model at build time so it's baked into the image
# Model is ~44MB and stored in /root/.u2net/
RUN python -c "from rembg import new_session; new_session('silueta'); print('Model baked into image.')"

# Expose port (Railway injects PORT env var)
EXPOSE 8000

# Start with uvicorn — single worker is enough (model loaded once in-process)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75"]

