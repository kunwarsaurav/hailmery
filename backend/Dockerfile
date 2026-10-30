FROM python:3.11-slim

# Hugging Face Spaces runs containers as non-root user (uid 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    U2NET_HOME=/home/user/.u2net

WORKDIR /home/user/app

# Install system dependencies for ONNX Runtime and image processing
# (must be done before USER switch — use sudo-equivalent via root layer)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*
USER user

# Copy and install Python dependencies first (layer caching)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . .

# Pre-download the silueta model at build time so it's baked into the image
# Stored at /home/user/.u2net/ (writable by non-root user)
RUN python -c "from rembg import new_session; new_session('silueta'); print('Model baked into image.')"

# Hugging Face Spaces uses port 7860; Railway/Fly uses $PORT (defaults to 8000)
EXPOSE 7860

# PORT env var is injected by the host (7860 for HF Spaces, custom for Railway/Fly)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1 --timeout-keep-alive 75"]

