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

# Install pinned dependencies, then install the local package without resolving
# looser pyproject dependency ranges again.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /opt/app-root/qradar-mcp/requirements.txt && \
    pip install --no-cache-dir --no-deps -e /opt/app-root/qradar-mcp/ && \
    useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /opt/app-root && \
    mkdir -p /opt/app-root/logs && \
    chown -R appuser:appuser /opt/app-root/logs

USER appuser

# Set Python path and container bind defaults
ENV PYTHONPATH=/opt/app-root/qradar-mcp \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=5000

# Expose MCP server port
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${MCP_PORT:-5000}/healthz" || exit 1

# Set working directory to qradar-mcp
WORKDIR /opt/app-root/qradar-mcp

# Run server directly
CMD ["python", "server.py"]
