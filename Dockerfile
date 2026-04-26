# =====================================================================
# Multi-stage Dockerfile for AETERNA Application
# Production-grade build with optimized layers
# =====================================================================

# ---- Build Stage ----
FROM python:3.11-slim as builder

WORKDIR /build

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create wheels from requirements
RUN pip install --user --no-cache-dir --no-warn-script-location \
    -r requirements.txt

# ---- Runtime Stage ----
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Copy startup script explicitly so it is always present in the image,
# regardless of broader context-copy changes.
COPY --chown=appuser:appuser start.sh /app/start.sh

# Copy application code
COPY --chown=appuser:appuser . .

# Normalize line endings and verify the script exists for older process configs
RUN sed -i 's/\r//g' /app/start.sh && chmod +x /app/start.sh && test -f /app/start.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE ${PORT}

# Default container command for local/docker runs.
# Fly process groups override this with their own direct Python commands.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
