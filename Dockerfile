# -------- BASE IMAGE (Python 3.11 with dependencies) ----------------------------
FROM python:3.11-slim

# -------- Runtime setup ----------------------------------------------------
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for layer-cache
COPY requirements.txt pyproject.toml* ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Cache buster - force rebuild with timestamp
ARG CACHE_BUST=1
RUN echo "Cache bust: $CACHE_BUST"

# Copy application source
COPY . .

# Create logs directory
RUN mkdir -p logs

# -------- Environment ------------------------------------------------------
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV HOST=0.0.0.0
ENV LOG_LEVEL=info
ENV DEBUG=false
ENV MCP_API_KEY=your-secret-api-key-here

# -------- Health check -----------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import httpx, os, sys; r=httpx.get(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/health'); sys.exit(0 if r.status_code==200 else 1)"

EXPOSE 8000

# -------- Entrypoint -------------------------------------------------------
CMD ["python3", "mevzuat_mcp_web_server.py"]
