# CloudScraper MCP Server

A Model Context Protocol (MCP) server that provides web scraping capabilities with built-in Cloudflare bypass functionality for AI applications.

## Overview

This MCP server enables AI assistants and applications to scrape web content from sites protected by Cloudflare and other bot protection mechanisms. It provides a clean, structured interface for accessing web content that would otherwise be blocked.

## Features

- **Cloudflare Bypass**: Automatically handles Cloudflare protection and other anti-bot measures
- **Multiple Transport Protocols**: Supports both stdio and HTTP transport for different use cases
- **Clean Content Extraction**: Returns structured, LLM-friendly content
- **Docker Ready**: Easy deployment with included Docker configuration
- **Flexible Response Options**: Choose between detailed responses or raw content only

## Available Tools

### `scrape_url`

Scrapes a URL and returns comprehensive response data including headers and metadata.

**Parameters:**
- `url` (string): The URL to scrape
- `method` (string, optional): HTTP method to use (default: "GET")

**Returns:**
- `status_code` (integer): HTTP response status code
- `headers` (object): Response headers
- `content` (string): Extracted page content
- `response_time` (number): Request duration in seconds

### `scrape_url_raw`

Scrapes a URL and returns only the raw page content for simplified processing.

**Parameters:**
- `url` (string): The URL to scrape
- `method` (string, optional): HTTP method to use (default: "GET")

**Returns:**
- `content` (string): Raw page content

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cloudscraper-mcp-server.git
cd cloudscraper-mcp-server
```

2. Install dependencies using uv:
```bash
uv sync
```

## Configuration

The server supports two transport protocols depending on your use case:

### Stdio Transport

Use stdio transport for direct integration with AI tools like Claude Code and VSCode:

```bash
uv run server.py
```

This is the default mode and works best for:
- Claude Code integration
- VSCode with MCP extensions
- Direct AI assistant communication
- Command-line usage

#### Claude Code Configuration

Add the server to Claude Code using the CLI:

```bash
claude mcp add cloudscraper-mcp \
  --type stdio \
  --command "uv" \
  --args "run" "server.py" \
  --directory "/path/to/cloudscraper-mcp-server"
```

#### VSCode/IDE Configuration

Add this configuration to your MCP settings file:

```json
{
  "mcpServers": {
    "cloudscraper-mcp": {
      "type": "stdio",
      "command": "/path/to/cloudscraper-mcp-server/.venv/Scripts/python.exe",
      "args": [
        "/path/to/cloudscraper-mcp-server/server.py"
      ]
    }
  }
}
```

**Note**: Adjust the paths according to your system. On Windows, use the `.venv/Scripts/python.exe` path; on macOS/Linux, use `.venv/bin/python`.

### HTTP Transport

Use HTTP transport for web-based integrations and automation platforms:

```bash
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 uv run server.py
```

This mode is ideal for:
- n8n workflow automation
- Web-based AI applications
- API integrations
- Remote access scenarios

### Environment Variables

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `MCP_TRANSPORT` | Transport protocol | `stdio` | `stdio`, `http` |
| `MCP_HOST` | Host to bind to (HTTP mode only) | `0.0.0.0` | Any valid IP |
| `MCP_PORT` | Port to listen on (HTTP mode only) | `8000` | Any valid port |

## Docker Deployment

For containerized deployment, see [DOCKER.md](DOCKER.md) for complete Docker setup instructions including building, running, and using Docker Compose.