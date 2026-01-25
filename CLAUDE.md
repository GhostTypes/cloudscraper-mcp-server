# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CloudScraper MCP Server is a Model Context Protocol server that enables AI agents to bypass Cloudflare protection and scrape web content. It uses the cloudscraper library to handle Cloudflare anti-bot challenges and FastMCP 3.0 for MCP protocol implementation.

**Core value proposition**: Standard HTTP requests are blocked by Cloudflare (403/429 errors). This server successfully bypasses those protections and returns clean, LLM-friendly markdown content.

## Architecture

### Single-File Design

The entire server implementation is in `server.py` (~500 lines). This is intentional - the server is simple enough that splitting into modules would add complexity without benefit.

**Key architectural sections:**

1. **Global state** (lines 10-29):
   - FastMCP instance (`mcp`)
   - Chunk cache with 2-minute expiry (`chunk_cache`, `CHUNK_EXPIRY_SECONDS`)
   - tiktoken encoder for token counting (`encoding`)
   - cloudscraper browser instance (`scraper`)

2. **Chunking system** (lines 32-93):
   - `count_tokens()` - Token counting using tiktoken cl100k_base encoding
   - `cleanup_expired_chunks()` - Removes chunks older than 120 seconds
   - `split_content_into_chunks()` - Splits content into 10k token chunks
   - `store_chunks()` - Stores chunks in cache, returns UUID chunk_id
   - `get_chunk()` - Retrieves chunk by ID and index

3. **Header management** (lines 96-166):
   - `HOP_BY_HOP_HEADERS` - Headers removed before returning to client
   - `clean_headers()` - Filters hop-by-hop headers
   - `generate_origin_and_ref()` - Creates Origin/Referer from URL
   - `set_user_agent()` - Sets Chrome 120 user agent
   - `set_security_headers()` - Adds Sec-Ch-Ua, Sec-Fetch-* headers
   - `get_headers()` - Combines all header functions

4. **Content processing** (lines 168-172):
   - `clean_html_to_markdown()` - Converts HTML to markdown using markdownify

5. **MCP Tools** (lines 174-448):
   - `@mcp.tool()` decorator defines MCP endpoints
   - Three tools: `scrape_url`, `scrape_url_raw`, `scrape_url_to_file`
   - Each tool handles URL validation, scraping, chunking, and response formatting

### Transport Modes

The server supports two transport protocols, selected via `MCP_TRANSPORT` environment variable:

- **stdio** (default): Used by Claude Code, VSCode, direct AI integrations
- **http**: Used by n8n, web apps, API integrations, remote access
  - Requires `MCP_HOST` (default: 0.0.0.0) and `MCP_PORT` (default: 8000)

Transport selection is in `if __name__ == "__main__":` block (lines 488-502).

### Chunking Strategy

Large responses (>10k tokens) are automatically chunked:

1. Content is tokenized using tiktoken cl100k_base
2. Split into chunks of max 10,000 tokens each
3. Chunks stored in memory cache with 120-second expiry
4. Client receives first chunk with continuation instructions
5. Client calls tool again with `continuation_token` to get next chunk

**Continuation token format**: `{uuid}:{index}` (e.g., "a08f9287-e337-4d06-b2d7-a8cfa1340b9a:1")

### Cloudflare Bypass

The cloudscraper library is configured with Chrome browser settings (lines 24-29):
- Browser: Chrome on Windows
- Delay: 1 second between requests
- Brotli compression: enabled
- User-Agent: Chrome 120

Additional security headers (Sec-Ch-Ua, Sec-Fetch-*, Origin, Referer) are auto-generated from the target URL to appear more legitimate.

## Development Commands

### Setup

```bash
# Install dependencies (including dev tools for testing)
uv sync --group dev

# Or install with pip
pip install -e ".[dev]"
```

### Running the Server

```bash
# Stdio mode (for Claude Code, VSCode)
uv run server.py

# HTTP mode (for n8n, web apps)
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 uv run server.py
```

### Testing

```bash
# Run all integration tests
uv run pytest tests/ -v

# Run specific test class
uv run pytest tests/test_cloudscraper_mcp.py::TestScrapeUrlTool -v

# Run specific test
uv run pytest tests/test_cloudscraper_mcp.py::TestScrapeUrlTool::test_bypasses_cloudflare -v

# Run tests with markers
uv run pytest -m cloudflare  # Only Cloudflare tests
uv run pytest -m "not slow"  # Skip slow tests
```

### Code Quality

```bash
# Check ruff issues
python -m ruff check server.py tests/

# Auto-fix ruff issues
python -m ruff check --fix server.py tests/

# Format code
python -m ruff format server.py tests/

# Check and format in one command
python -m ruff check --fix server.py tests/ && python -m ruff format server.py tests/
```

### Local MCP Testing

Create `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "cloudscraper": {
      "command": "python",
      "args": ["C:\\Users\\Cope\\Documents\\GitHub\\cloudscraper-mcp-server\\server.py"],
      "env": {}
    }
  }
}
```

Restart Claude Code to load the server, then test with MCP tools.

## MCP Tools Reference

### scrape_url

**Purpose**: Quick content retrieval, returns string content only

**Parameters**:
- `url` (required): Target URL
- `method` (optional, default "GET"): HTTP method
- `clean_content` (optional, default true): Convert HTML to markdown
- `continuation_token` (optional): Token for retrieving next chunk

**Returns**: String with content, includes chunk instructions if >10k tokens

**Best for**: AI processing when you don't need metadata

### scrape_url_raw

**Purpose**: Full response details with headers, timing, and metadata

**Parameters**: Same as `scrape_url`

**Returns**: Dictionary with:
- `status_code`: HTTP status
- `headers`: Response headers (hop-by-hop removed)
- `content`: Page content or current chunk
- `content_type`: MIME type
- `response_time`: Request duration in seconds
- `chunked`, `chunk_index`, `total_chunks`, `continuation_token`, `total_tokens`, `message`: When chunked
- `error`: On failure

**Best for**: Debugging, performance analysis, when you need response metadata

### scrape_url_to_file

**Purpose**: Save content to disk

**Parameters**:
- `url` (required): Target URL
- `file_path` (required): Where to save content
- `method` (optional, default "GET"): HTTP method
- `clean_content` (optional, default false): Convert HTML to markdown
- `overwrite` (optional, default false): Replace existing file

**Returns**: Dictionary with:
- `status_code`, `headers`, `content_type`, `response_time`
- `file_path`: Absolute path to saved file
- `bytes_written`: Number of bytes written
- `message`: Success confirmation
- `error`: On failure

**Best for**: Exporting content for archival, processing by other tools

## Testing Strategy

The test suite (`tests/test_cloudscraper_mcp.py`) validates:

1. **Cloudflare bypass works** - Uses https://namemc.com/profile/GhostTypes.2
2. **Standard requests are blocked** - Confirms the problem being solved
3. **All three tools work correctly**
4. **Chunking system functions** - Tests token-based splitting
5. **File operations work safely** - Tests overwrite protection, directory creation
6. **Content quality is high** - Validates scripts removed, headers cleaned

**Key test URLs:**
- Cloudflare-protected: `https://namemc.com/profile/GhostTypes.2`
- Simple (no Cloudflare): `https://httpbin.org/html`

## Code Quality Standards

This project uses **ruff** for linting and formatting with production-quality rules:

**Enabled rule categories:**
- E, W - pycodestyle errors and warnings
- F - pyflakes
- I - isort (import sorting)
- B - flake8-bugbear
- C4 - flake8-comprehensions
- UP - pyupgrade
- ARG - flake8-unused-arguments
- SIM - flake8-simplify
- S - flake8-bandit (security)
- ASYNC - flake8-async
- PERF - perflint
- RET - flake8-return

**Key ignores:**
- E501: Line length (handled by formatter)
- B008: Function calls in defaults (FastMCP @mcp.tool() needs this)
- S101: Assert allowed (used in tests)
- S113: No timeout required (user-controlled URLs)
- W191: Tabs (not used)

**Test file exceptions** (tests/*.py):
- ARG001: Unused arguments allowed (pytest fixtures)

## Common Patterns

### Adding New MCP Tools

1. Define function with `@mcp.tool()` decorator
2. Add docstring with parameter descriptions
3. Validate inputs (URL format, file paths, etc.)
4. Call scraper with custom headers via `get_headers()`
5. Handle chunking if content may be large
6. Return structured response with error handling

Example structure:
```python
@mcp.tool()
def my_tool(url: str, param: str = "default") -> dict:
    """Tool description.

    Args:
        url: The URL to process
        param: Parameter description
    """
    try:
        # Validate inputs
        if not url or not url.strip():
            return {"error": "URL is required", "status_code": 400}

        # Make request with security headers
        response = scraper.get(url, headers=get_headers(), timeout=30)

        # Process response
        content = process_response(response)

        # Return structured response
        return {"status_code": response.status_code, "data": content}
    except Exception as e:
        return {"error": str(e), "status_code": 500}
```

### Handling Chunking in Tools

For tools that may return large content:

```python
# After getting content
token_count = count_tokens(content)

if token_count > MAX_TOKENS_PER_CHUNK:
    chunks = split_content_into_chunks(content)
    chunk_id = store_chunks(chunks)

    # Return first chunk with metadata
    return {
        "content": chunks[0] + f"\n\n--- CHUNK 1 of {len(chunks)} ---",
        "continuation_token": f"{chunk_id}:1",
        "total_chunks": len(chunks),
        "chunk_index": 1,
        "total_tokens": token_count
    }
```

### Security Considerations

When working with user-provided URLs and file paths:

1. **URL validation**: Check URL is not empty before processing
2. **File path safety**: Use `os.path.abspath()` and `os.path.expanduser()` to prevent directory traversal
3. **Overwrite protection**: Require explicit `overwrite=true` for existing files
4. **Header sanitization**: Remove hop-by-hop headers (connection, keep-alive, etc.)
5. **S104 ignore**: The 0.0.0.0 binding for HTTP mode is intentional for Docker - documented with inline ignore

### Inline Ignore Pattern

When ruff rules need to be bypassed, always document why:

```python
# Intentional binding to all interfaces for Docker/container environments
host = os.environ.get("MCP_HOST", "0.0.0.0")  # noqa: S104

# Blocking I/O acceptable in test context
with open(temp_file_path, encoding="utf-8") as f:  # noqa: ASYNC230
```

## Troubleshooting

### Tests Failing with Cloudflare

If `https://namemc.com/profile/GhostTypes.2` tests fail:
- Cloudflare may have changed their protection
- Verify cloudscraper is up to date: `uv pip install --upgrade cloudscraper`
- Check if the site is actually accessible in a browser

### Chunk Cache Issues

If chunking tests fail:
- Check `CHUNK_EXPIRY_SECONDS` hasn't been changed
- Verify `cleanup_expired_chunks()` is being called
- Ensure continuation token format is correct: `{uuid}:{index}`

### MCP Server Not Loading

If Claude Code doesn't load the server:
- Verify `.mcp.json` is in project root
- Check path to `server.py` is absolute
- Restart Claude Code after changing `.mcp.json`
- Use `/mcp` command to verify server is loaded

## Project-Specific Agents

This repository includes specialized Claude Code agents:

- **ruff-code-quality**: Fixes ruff violations and improves Python code quality
- **code-quality**: General code review and best practices
- **integration-tester**: Builds integration test suites for MCP servers

Use these agents when appropriate to maintain code quality standards.
