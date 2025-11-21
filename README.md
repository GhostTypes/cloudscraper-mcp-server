<div align="center">

# CloudScraper MCP Server

### A Model Context Protocol server that enables AI agents to bypass Cloudflare protection and scrape web content

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0%2B-green.svg)](https://github.com/jlowin/fastmcp)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](DOCKER.md)

</div>

---

<div align="center">

## Core Features

</div>

<div align="center">

| Feature | Description |
|---------|-------------|
| **Cloudflare Bypass** | Automatically handles Cloudflare protection using cloudscraper library |
| **Multiple Transports** | Supports both stdio and HTTP transport protocols |
| **Content Cleaning** | Converts HTML to clean, LLM-friendly Markdown format |
| **Smart Chunking** | Automatically splits large responses into 10k token chunks |
| **Docker Support** | Production-ready containerized deployment |
| **Multiple Methods** | Supports GET and POST HTTP methods |
| **Binary Handling** | Base64 encoding for non-text content |
| **File Export** | Save scraped content directly to disk |

</div>

---

<div align="center">

## Available MCP Tools

</div>

<div align="center">

### Tool Comparison

| Tool | Return Type | Use Case | Chunking Support | File Output |
|------|-------------|----------|------------------|-------------|
| **scrape_url** | String (content only) | Quick content retrieval for AI processing | Yes | No |
| **scrape_url_raw** | Dictionary (metadata + content) | Full response details with headers and timing | Yes | No |
| **scrape_url_to_file** | Dictionary (save confirmation) | Export content to workspace files | No | Yes |

</div>

---

<div align="center">

### Shared Parameters

</div>

<div align="center">

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Target URL to scrape |
| `method` | string | No | "GET" | HTTP method (GET or POST) |
| `clean_content` | boolean | No | true | Convert HTML to Markdown |
| `continuation_token` | string | No | null | Token for retrieving next chunk |

</div>

---

<div align="center">

### scrape_url Response Fields

</div>

<div align="center">

| Field | Type | Description |
|-------|------|-------------|
| Response | string | Page content with chunk instructions if applicable |

**Note:** When content exceeds 10k tokens, response includes continuation instructions embedded in the text.

</div>

---

<div align="center">

### scrape_url_raw Response Fields

</div>

<div align="center">

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `status_code` | integer | Yes | HTTP response status code |
| `headers` | object | Yes | Response headers (hop-by-hop headers removed) |
| `content` | string | Yes | Page content or current chunk |
| `content_type` | string | Yes | MIME type of response |
| `response_time` | number | Yes | Request duration in seconds |
| `chunked` | boolean | When chunked | Indicates response was split |
| `chunk_index` | integer | When chunked | Current chunk number (1-based) |
| `total_chunks` | integer | When chunked | Total number of chunks |
| `continuation_token` | string | When more chunks | Token for next chunk retrieval |
| `total_tokens` | integer | When chunked | Total tokens in full response |
| `message` | string | When chunked | Human-readable chunk status |
| `error` | string | On failure | Error description |

</div>

---

<div align="center">

### scrape_url_to_file Parameters

</div>

<div align="center">

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Target URL to scrape |
| `file_path` | string | Yes | - | Path where content should be saved |
| `method` | string | No | "GET" | HTTP method (GET or POST) |
| `clean_content` | boolean | No | false | Convert HTML to Markdown before saving |
| `overwrite` | boolean | No | false | Replace file if it exists |

</div>

---

<div align="center">

### scrape_url_to_file Response Fields

</div>

<div align="center">

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `status_code` | integer | Yes | HTTP response status code |
| `headers` | object | Yes | Response headers (hop-by-hop headers removed) |
| `content_type` | string | Yes | MIME type of saved content |
| `response_time` | number | Yes | Request duration in seconds |
| `file_path` | string | On success | Absolute path to saved file |
| `bytes_written` | integer | On success | Number of bytes written to disk |
| `message` | string | On success | Confirmation message |
| `error` | string | On failure | Error description |

</div>

---

<div align="center">

## Installation

</div>

<div align="center">

### Prerequisites

</div>

<div align="center">

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.10+ | Runtime environment |
| uv | Latest | Dependency management |
| Git | Any | Repository cloning |

</div>

<div align="center">

### Setup Steps

</div>

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/cloudscraper-mcp-server.git
cd cloudscraper-mcp-server
uv sync
```

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
| **http** | n8n, Web apps, API integrations, Remote access | Requires MCP_TRANSPORT=http |

</div>

---

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

---

<div align="center">

## Usage Examples

</div>

<div align="center">

### Running with Stdio Transport (Default)

</div>

```bash
uv run server.py
```

<div align="center">

### Running with HTTP Transport

</div>

```bash
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 uv run server.py
```

<div align="center">

### Claude Code Integration

</div>

```bash
claude mcp add cloudscraper-mcp \
  --type stdio \
  --command "uv" \
  --args "run" "server.py" \
  --directory "/path/to/cloudscraper-mcp-server"
```

<div align="center">

### VSCode/IDE Configuration

</div>

```json
{
  "mcpServers": {
    "cloudscraper-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "server.py"
      ],
      "cwd": "/path/to/cloudscraper-mcp-server"
    }
  }
}
```

---

<div align="center">

## Docker Deployment

</div>

<div align="center">

For containerized deployment instructions, see [DOCKER.md](DOCKER.md)

</div>

---

<div align="center">

## Technical Stack

</div>

<div align="center">

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Protocol** | FastMCP 2.0+ | Model Context Protocol implementation |
| **Scraping** | cloudscraper 1.2.71+ | Cloudflare bypass engine |
| **Compression** | brotli 1.0.9+ | Response decompression |
| **Parsing** | beautifulsoup4 4.10.0+ | HTML parsing |
| **Conversion** | markdownify 0.11.6+ | HTML to Markdown transformation |
| **Tokenization** | tiktoken 0.5.0+ | Token counting for chunking |

</div>

---

<div align="center">

## Advanced Features

</div>

<div align="center">

### Response Chunking System

</div>

<div align="center">

| Feature | Value | Description |
|---------|-------|-------------|
| **Max Tokens Per Chunk** | 10,000 | Maximum tokens in a single response |
| **Chunk Expiry** | 2 minutes | Cache lifetime for chunk retrieval |
| **Token Encoding** | cl100k_base | tiktoken encoding model |
| **Continuation Pattern** | chunk_id:index | Token format for sequential retrieval |

</div>

---

<div align="center">

### Security Headers

</div>

<div align="center">

| Header | Value | Purpose |
|--------|-------|---------|
| User-Agent | Chrome 120 | Browser impersonation |
| Sec-Ch-Ua | Chrome/Chromium | Client hints |
| Sec-Fetch-* | cors/same-origin | Fetch metadata |
| Origin/Referer | Auto-generated | Request legitimacy |

</div>

---

<div align="center">

Made with CloudScraper and FastMCP

</div>
