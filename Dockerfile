FROM python:3.11-slim

LABEL maintainer="IBM QRadar Investigation Assistant Team"
LABEL description="QRadar MCP Server - Model Context Protocol integration for IBM QRadar SIEM"

WORKDIR /opt/app-root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code first (needed for setup)
# Using .dockerignore to exclude sensitive files and unnecessary directories
COPY . /opt/app-root/qradar-mcp/

# Install the package in editable mode and create non-root user
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /opt/app-root/qradar-mcp/ && \
    useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /opt/app-root && \
    mkdir -p /opt/app-root/logs && \
    chown -R appuser:appuser /opt/app-root/logs

USER appuser

# Set Python path to include qradar-mcp directory
ENV PYTHONPATH=/opt/app-root/qradar-mcp

# Expose MCP server port
EXPOSE 5000

# Set working directory to qradar-mcp
WORKDIR /opt/app-root/qradar-mcp

# Run server directly
CMD ["python", "server.py"]