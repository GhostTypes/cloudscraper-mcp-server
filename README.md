<div align="center">

# CloudScraper MCP Server

### A Model Context Protocol server that enables AI agents to bypass Cloudflare protection and scrape web content

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](DOCKER.md)

</div>

---

<div align="center">

## Quick Start

</div>

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/cloudscraper-mcp-server.git
cd cloudscraper-mcp-server
uv sync
```

Add to Claude Code:

```bash
claude mcp add cloudscraper-mcp \
  --type stdio \
  --command "uv" \
  --args "run" "server.py" \
  --directory "/path/to/cloudscraper-mcp-server"
```

Add to VSCode / any MCP-compatible IDE:

```json
{
  "mcpServers": {
    "cloudscraper-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/cloudscraper-mcp-server"
    }
  }
}
```

---

<div align="center">

## Features

</div>

- **Cloudflare Bypass** — Automatically handles Cloudflare protection so AI agents can reach pages that block standard requests
- **Content Cleaning** — Converts HTML to clean, LLM-friendly Markdown
- **Smart Chunking** — Automatically splits large responses into 10k-token chunks with continuation tokens
- **Binary Handling** — Base64-encodes non-text content so agents can handle images and downloads
- **File Export** — Save scraped content directly to disk via `scrape_url_to_file`
- **Docker Support** — Containerized deployment via [DOCKER.md](DOCKER.md)

Three tools are available: `scrape_url` (returns content as a string), `scrape_url_raw` (returns content plus response metadata), and `scrape_url_to_file` (saves content to disk).

---

<div align="center">

## Configuration

</div>

<div align="center">

### Transport Protocols

</div>

<div align="center">

| Transport | Best For | Configuration |
|-----------|----------|---------------|
| **stdio** | Claude Code, VSCode, Direct AI integration | Default mode, no environment variables needed |
| **http** | n8n, Web apps, API integrations, Remote access | Requires `MCP_TRANSPORT=http` |

</div>

Run with HTTP transport:

```bash
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 uv run server.py
```

<div align="center">

### Environment Variables

</div>

<div align="center">

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `MCP_TRANSPORT` | stdio | stdio, http | Transport protocol selection |
| `MCP_HOST` | 0.0.0.0 | Any valid IP | Host binding for HTTP mode |
| `MCP_PORT` | 8000 | Any valid port | Port for HTTP mode |

</div>
