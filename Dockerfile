FROM python:3.10-alpine

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.cargo/bin/uv /usr/local/bin/

# Copy project files
COPY . .

# Install project dependencies using uv
RUN uv sync --frozen

# Set environment variables for HTTP transport
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001

# Expose port for HTTP server
EXPOSE 8001

# Health check to ensure server is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8001/mcp || exit 1

# Start the MCP server in HTTP mode
CMD ["uv", "run", "server.py"]