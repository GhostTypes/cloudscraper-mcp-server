# Docker Deployment

This document provides comprehensive instructions for deploying the CloudScraper MCP Server using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for orchestrated deployment)

**Note**: For local development without Docker, see the [Installation section](README.md#installation) in the main README for setting up with uv.

## Building the Docker Image

Build the Docker image from the project root directory:

```bash
docker build -t cloudscraper-mcp-server .
```

## Running the Container

### Basic HTTP Mode

Run the container with default HTTP transport settings:

```bash
docker run -p 8000:8000 cloudscraper-mcp-server
```

The server will be accessible at `http://localhost:8000/mcp`.

### Custom Configuration

Customize the server behavior using environment variables:

```bash
docker run -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  cloudscraper-mcp-server
```

### Environment Variables

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `MCP_TRANSPORT` | Transport protocol | `http` | Use `http` for Docker deployments |
| `MCP_HOST` | Host to bind to | `0.0.0.0` | Required for container networking |
| `MCP_PORT` | Port to listen on | `8000` | Must match container port mapping |

**Note**: Docker deployments should use HTTP transport mode. Stdio transport is not suitable for containerized environments.

## Docker Compose Deployment

For production or development environments, use Docker Compose for easier management.

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  cloudscraper-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      MCP_TRANSPORT: http
      MCP_HOST: 0.0.0.0
      MCP_PORT: 8000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Deploy with Docker Compose:

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Health Monitoring

The container includes a health check endpoint that verifies the server is running properly. The health check makes a request to the server to ensure it's responsive.

You can manually check the health status:

```bash
# Check container health
docker ps

# Manual health check
curl http://localhost:8000/health
```

## Connecting to the Server

Once the container is running, MCP clients can connect to:

```
http://localhost:8000/mcp
```

For remote deployments, replace `localhost` with your Docker host's IP address or domain name.

## Troubleshooting

### Common Issues

1. **Port conflicts**: If port 8000 is already in use, change the host port mapping:
   ```bash
   docker run -p 8080:8000 cloudscraper-mcp-server
   ```

2. **Container not accessible**: Ensure the `MCP_HOST` is set to `0.0.0.0` for container networking.

3. **Health check failures**: Verify the server is properly starting by checking container logs:
   ```bash
   docker logs cloudscraper-mcp-server
   ```

### Debugging

To run the container interactively for debugging:

```bash
docker run -it --rm -p 8000:8000 cloudscraper-mcp-server /bin/bash
```