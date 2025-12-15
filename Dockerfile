# ============================================================================
# Dockerfile
# ============================================================================

# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Add metadata labels
LABEL maintainer="esunayana@gmail.com"
LABEL description="Prometheus metrics simulator with on-demand metric generation"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/esunayana/prometheus-metrics-app"
LABEL org.opencontainers.image.description="Prometheus metrics simulator with all metric types"
LABEL org.opencontainers.image.licenses="MIT"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY prommetricsgenerate.py .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the metrics port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run the application
CMD ["python", "prommetricsgenerate.py"]