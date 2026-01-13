FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Copy application files
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY checkpoint-4089/ ./checkpoint-4089/

# Create directories
RUN mkdir -p \
    /app/backend/data/uploads \
    /app/backend/data/exports \
    /app/backend/data/chroma \
    /app/backend/data/sqlite \
    /root/.cache/huggingface \
    /root/.cache/torch \
    /root/.cache/sentence-transformers && \
    chmod -R 777 /root/.cache

# Set environment variables
ENV MODEL_PATH=/app/checkpoint-4089
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface
ENV HF_HOME=/root/.cache/huggingface
ENV TORCH_HOME=/root/.cache/torch
ENV SENTENCE_TRANSFORMERS_HOME=/root/.cache/sentence-transformers
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run backend directly (no supervisor, no nginx)
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
