# CloudScraper MCP Server

A Model Context Protocol (MCP) server that enables AI Agents to scrape information from various pages


## Features

- **Cloudflare Bypass**: Automatically handles Cloudflare protection, utilizing [cloudscraper](https://github.com/VeNoMouS/cloudscraper)
- **Multiple Transport Protocols**: Supports both stdio and HTTP transport for different use cases
- **Clean Content Extraction**: Returns structured, LLM-friendly content
- **Docker Ready**: Easy deployment with included Docker configuration
- **Flexible Response Options**: Choose between detailed responses or raw content only
- **Built-in Chunking**: Automatically splits responses that exceed 10k tokens and provides guidance for retrieving the remaining chunks

## Available Tools

### `scrape_url`

Scrapes a URL and returns cleaned text (Markdown for HTML pages) along with chunk metadata.

**Parameters:**
- `url` (string): The URL to scrape
- `method` (string, optional): HTTP method to use (default: "GET")

**Returns:** Object with the following keys:
- `content` (string): The first chunk of the cleaned content
- `chunked` (boolean): Indicates whether the payload exceeded 10k tokens and was chunked
- `chunk_id` (string | null): Identifier to request additional chunks via `get_scrape_chunk`
- `chunk_index` (integer): Index of the current chunk (1-based)
- `total_chunks` (integer): Total number of chunks generated for this response
- `token_count` (integer): Token estimate for the full response
- `instructions` (string | null): Guidance on how to retrieve any remaining chunks
- `format` (string): Either `markdown`, `text`, or `binary`
- `response_time` (number): Request duration in seconds
- `url` (string): The scraped URL

### `scrape_url_raw`

Scrapes a URL and returns the raw response body, headers, and chunk metadata.

**Parameters:**
- `url` (string): The URL to scrape
- `method` (string, optional): HTTP method to use (default: "GET")

**Returns:** Object with the following keys:
- `content` (string): The first chunk of the raw content (base64 encoded for binary payloads)
- `chunked` (boolean): Indicates whether the payload exceeded 10k tokens and was chunked
- `chunk_id` (string | null): Identifier to request additional chunks via `get_scrape_chunk`
- `chunk_index` (integer): Index of the current chunk (1-based)
- `total_chunks` (integer): Total number of chunks generated for this response
- `token_count` (integer): Token estimate for the full response
- `instructions` (string | null): Guidance on how to retrieve any remaining chunks
- `status_code` (integer): HTTP response status code
- `headers` (object): Cleaned response headers
- `content_type` (string): MIME type (or `application/base64` when base64 encoded)
- `response_time` (number): Request duration in seconds
- `url` (string): The scraped URL

### `get_scrape_chunk`

Retrieves any subsequent chunk for a previously chunked response from either scraping tool.

**Parameters:**
- `chunk_id` (string): Identifier returned by `scrape_url` or `scrape_url_raw`
- `chunk_index` (integer): 1-based index of the chunk to fetch

**Returns:** Object mirroring the original scraper response with the requested chunk and updated instructions.

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
      "command": "uv",
      "args": [
        "run",
        "server.py",
      ]
      "cwd":  "/path/to/cloudscraper-mcp-server/server.py"
    }
  }
}
```

### HTTP Transport

Use HTTP transport for web-based integrations and automation platforms:

```bash
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8000
uv run server.py
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
