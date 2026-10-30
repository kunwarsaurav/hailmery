FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ONNX Runtime and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Bake the silueta model into the image at build time (~44MB)
# This means cold starts never need to download — just load from disk
ENV U2NET_HOME=/app/.u2net
RUN python -c "from rembg import new_session; new_session('silueta'); print('Model baked into image.')"

# Cloud Run injects PORT (default 8080); also works on Railway/Fly with their $PORT
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 75"]

