# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash redmine

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage to both user locations for flexibility
COPY --from=builder /root/.local /home/redmine/.local
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ /app/src/
COPY output/ /app/output/

# Set environment variables for both root and non-root users
ENV PATH="/home/redmine/.local/bin:/root/.local/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Change ownership to non-root user (but keep root accessible for user switching)
RUN chown -R redmine:redmine /app /home/redmine/.local

# Default to non-root user (can be overridden by docker-compose)
USER redmine

# Create output directory with proper permissions
RUN mkdir -p /app/output

# Expose port for web interface and API access
EXPOSE 3003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:3003/health')" || exit 1

# Default command
CMD ["python", "-m", "src.main.python.core.main"]