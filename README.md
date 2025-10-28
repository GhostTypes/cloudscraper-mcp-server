# CloudScraper MCP Server

A Model Context Protocol (MCP) server that enables AI Agents to scrape information from various pages


## Features

- **Cloudflare Bypass**: Automatically handles Cloudflare protection, utilizing [cloudscraper](https://github.com/VeNoMouS/cloudscraper)
- **Multiple Transport Protocols**: Supports both stdio and HTTP transport for different use cases
- **Clean Content Extraction**: Returns structured, LLM-friendly content
- **Docker Ready**: Easy deployment with included Docker configuration
- **Flexible Response Options**: Choose between detailed responses or raw content only

## Available Tools

### Shared request parameters (`scrape_url`, `scrape_url_raw`)

Both tools accept the following arguments:

- `url` (string): Target URL to fetch.
- `method` (string, optional): HTTP method to use (default: `"GET"`).
- `clean_content` (boolean, optional): Convert HTML responses to clean Markdown before returning content (default: `true`).
- `continuation_token` (string, optional): Token generated from a prior chunked response to request the next chunk (`"chunk_id:index"`).

### `scrape_url`

Scrapes a URL and returns only the response body as a string. When the result exceeds 10k tokens it is chunked and the returned text contains instructions for retrieving the remaining chunks with `continuation_token`.

**Parameters:**
- All arguments listed in [Shared request parameters](#shared-request-parameters-scrape_url-scrape_url_raw).

**Returns:**
- Raw or cleaned page content as a string. Chunked responses embed continuation guidance directly in the text, and errors are returned as human-readable strings.

### `scrape_url_raw`

Scrapes a URL and returns structured metadata with the response content. Supports chunked retrieval for large pages and base64-encodes binary payloads.

**Parameters:**
- All arguments listed in [Shared request parameters](#shared-request-parameters-scrape_url-scrape_url_raw).

**Returns:**
- `status_code` (integer): HTTP response status code.
- `headers` (object): Response headers with hop-by-hop headers removed.
- `content` (string): Raw or cleaned page content, or the current chunk when chunked. Binary responses are returned as base64 strings with `content_type` set to `"application/base64"`.
- `content_type` (string): MIME type of the response body.
- `response_time` (number): Request duration in seconds.
- `chunked` (boolean, optional): Present when the response was chunked due to size.
- `chunk_index` (integer, optional): 1-based index of the current chunk when chunked.
- `total_chunks` (integer, optional): Total number of available chunks when chunked.
- `continuation_token` (string, optional): Token to request the next chunk when more data remains.
- `total_tokens` (integer, optional): Token count of the full response when chunked.
- `message` (string, optional): Human-readable status about chunk progress.
- `error` (string, optional): Error description when the request fails or a continuation token is invalid.

### `scrape_url_to_file`

Scrapes a URL and saves the response body to a file on disk in the current workspace. Directories are created as needed and existing files are protected unless `overwrite` is set.

**Parameters:**
- `url` (string): Target URL to fetch.
- `file_path` (string): Relative or absolute path where the response body should be saved.
- `method` (string, optional): HTTP method to use (default: `"GET"`).
- `clean_content` (boolean, optional): Convert HTML responses to clean Markdown before writing (default: `false`).
- `overwrite` (boolean, optional): Replace the file if it already exists (default: `false`).

**Returns:**
- `status_code` (integer): HTTP response status code.
- `headers` (object): Response headers with hop-by-hop headers removed.
- `content_type` (string): MIME type of the saved response.
- `response_time` (number): Request duration in seconds.
- `file_path` (string): Absolute path to the saved file.
- `bytes_written` (integer): Number of bytes written to disk.
- `message` (string): Confirmation that the response was saved.
- `error` (string, optional): Error description when the request fails or the file cannot be written.

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
