import os
import time
import uuid
from typing import Any, Dict, List, Optional

import cloudscraper
import tiktoken
from fastmcp import FastMCP

# Create the FastMCP instance
mcp = FastMCP("CloudScraper MCP Server")

# Initialize cloudscraper with browser settings
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    },
    delay=1,
    allow_brotli=True
)

# Hop-by-hop headers that should be removed
HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
}

CHUNK_TOKEN_LIMIT = 10_000
CHUNK_CACHE_TTL = 60 * 2  # 2 minutes

_tokenizer = tiktoken.get_encoding("cl100k_base")

_chunk_cache: Dict[str, Dict[str, Any]] = {}

def clean_headers(headers):
    """Remove hop-by-hop headers"""
    cleaned = {}
    for name, value in headers.items():
        if name.lower() not in HOP_BY_HOP_HEADERS:
            cleaned[name] = value
    cleaned.pop('content-encoding', None)
    cleaned.pop('content-length', None)
    return cleaned

def set_user_agent(headers):
    """Set user agent to match Sec-Ch-Ua"""
    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    return headers

def set_security_headers(headers):
    """Set security headers to avoid bot detection"""
    headers['Sec-Ch-Ua'] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
    headers['Sec-Ch-Ua-Mobile'] = '?0'
    headers['Sec-Ch-Ua-Platform'] = '"Windows"'
    headers['Sec-Fetch-Dest'] = 'empty'
    headers['Sec-Fetch-Mode'] = 'cors'
    headers['Sec-Fetch-Site'] = 'same-origin'
    return headers

def set_origin_and_ref(headers, origin, ref):
    """Set origin and referrer headers"""
    headers['Origin'] = origin
    headers['Referer'] = ref
    return headers

def generate_origin_and_ref(url, headers):
    """Generate origin and referrer from URL"""
    data = url.split('/')
    first = data[0]
    base = data[2]
    c_url = f"{first}//{base}/"
    headers = set_origin_and_ref(headers, c_url, c_url)
    return headers

def get_headers():
    """Get default headers for requests"""
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    }
    headers = set_user_agent(headers)
    headers = set_security_headers(headers)
    return headers

def clean_html_to_markdown(html_content):
    """Convert HTML content to clean markdown format"""
    try:
        from markdownify import markdownify as md
        # Convert HTML to markdown
        markdown_content = md(html_content, heading_style="ATX")
        return markdown_content
    except Exception as e:
        print(f"Error converting HTML to markdown: {str(e)}")
        # Return original content if conversion fails
        return html_content


def _cleanup_chunk_cache() -> None:
    """Remove expired chunk cache entries."""
    now = time.time()
    expired_ids = [
        chunk_id
        for chunk_id, entry in list(_chunk_cache.items())
        if now - entry["created_at"] > CHUNK_CACHE_TTL
    ]
    for chunk_id in expired_ids:
        _chunk_cache.pop(chunk_id, None)


def _count_tokens(text: str) -> int:
    """Estimate the number of tokens in the supplied text."""
    if not text:
        return 0

    return len(_tokenizer.encode(text))


def _chunk_text(text: str, token_limit: int = CHUNK_TOKEN_LIMIT) -> List[str]:
    """Split text into chunks that respect the token limit."""
    if not text:
        return [""]

    tokens = _tokenizer.encode(text)
    return [
        _tokenizer.decode(tokens[i:i + token_limit])
        for i in range(0, len(tokens), token_limit)
    ]


def _store_chunks(chunks: List[str], metadata: Optional[Dict[str, Any]] = None, *, token_count: int) -> str:
    """Store chunked content and return a chunk identifier."""
    _cleanup_chunk_cache()
    chunk_id = str(uuid.uuid4())
    _chunk_cache[chunk_id] = {
        "chunks": chunks,
        "metadata": dict(metadata) if metadata else {},
        "token_count": token_count,
        "created_at": time.time(),
    }
    return chunk_id


def _build_chunk_instructions(chunk_id: str, chunk_index: int, total_chunks: int) -> str:
    if chunk_index < total_chunks:
        next_index = chunk_index + 1
        return (
            f"This payload is chunk {chunk_index} of {total_chunks} (10,000-token limit). "
            f"Call `get_scrape_chunk` with chunk_id `{chunk_id}` and chunk_index {next_index} "
            "to retrieve the next chunk."
        )
    return (
        f"This payload is chunk {chunk_index} of {total_chunks} (10,000-token limit). "
        "All chunks have been delivered."
    )


def _prepare_chunked_response(
    content: str,
    base_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a payload augmented with chunk metadata."""
    base_payload = base_payload or {}
    token_count = _count_tokens(content)

    if token_count <= CHUNK_TOKEN_LIMIT:
        return {
            **base_payload,
            "content": content,
            "chunked": False,
            "chunk_id": None,
            "chunk_index": 1,
            "total_chunks": 1,
            "token_count": token_count,
            "instructions": None,
        }

    chunks = _chunk_text(content, CHUNK_TOKEN_LIMIT)
    chunk_id = _store_chunks(chunks, metadata=base_payload, token_count=token_count)
    total_chunks = len(chunks)
    instructions = _build_chunk_instructions(chunk_id, 1, total_chunks)

    return {
        **base_payload,
        "content": chunks[0],
        "chunked": True,
        "chunk_id": chunk_id,
        "chunk_index": 1,
        "total_chunks": total_chunks,
        "token_count": token_count,
        "instructions": instructions,
    }

@mcp.tool()
def scrape_url(url: str, method: str = "GET") -> Dict[str, Any]:
    """
    Scrape a URL and return its content as clean markdown.
    
    Args:
        url: The URL to scrape
        method: HTTP method to use (default: GET)
        
    Returns:
        A dictionary containing the first chunk of content plus chunk metadata and request context.
    """
    try:
        # Prepare headers
        headers = get_headers()
        headers = generate_origin_and_ref(url, headers)
        
        # Make the request with stream=False to ensure proper decompression
        start = time.time()
        if method.upper() == "GET":
            response = scraper.get(url, headers=headers, stream=False)
        else:
            response = scraper.post(url, headers=headers, stream=False)
        end = time.time()
        elapsed = end - start
        
        print(f"Scraped {url} in {elapsed:.6f} seconds")
        
        # Return raw content - cloudscraper should handle decompression automatically
        content_type = response.headers.get('content-type', '')

        if 'text' in content_type or 'html' in content_type:
            content = response.text
            # Convert HTML to markdown
            if 'html' in content_type:
                content = clean_html_to_markdown(content)
            base_payload = {
                "url": url,
                "format": "markdown" if 'html' in content_type else "text",
                "response_time": elapsed,
            }
            return _prepare_chunked_response(content, base_payload)
        else:
            # For binary content, try to decode as UTF-8, fallback to error message
            try:
                content = response.content.decode('utf-8')
            except UnicodeDecodeError:
                content = f"[Binary content - {len(response.content)} bytes]"
            base_payload = {
                "url": url,
                "format": "binary",
                "response_time": elapsed,
            }
            return _prepare_chunked_response(content, base_payload)

    except Exception as e:
        print(f"Scraping Error: {str(e)}")
        return {
            "error": str(e),
            "chunked": False,
            "chunk_id": None,
            "chunk_index": 0,
            "total_chunks": 0,
            "token_count": 0,
            "instructions": None,
        }

@mcp.tool()
def scrape_url_raw(url: str, method: str = "GET") -> dict:
    """
    Scrape a URL and return the raw, unmodified content.
    
    Args:
        url: The URL to scrape
        method: HTTP method to use (default: GET)
        
    Returns:
        A dictionary containing response metadata and chunk-aware raw content.
    """
    try:
        # Prepare headers
        headers = get_headers()
        headers = generate_origin_and_ref(url, headers)
        
        # Make the request
        start = time.time()
        if method.upper() == "GET":
            response = scraper.get(url, headers=headers, stream=False)
        else:
            response = scraper.post(url, headers=headers, stream=False)
        end = time.time()
        elapsed = end - start
        
        print(f"Scraped {url} in {elapsed:.6f} seconds")
        
        # Get the properly decompressed content
        content_type = response.headers.get('content-type', '')
        
        # Get the properly decompressed content
        if 'text' in content_type or 'html' in content_type:
            content = response.text
        else:
            # For binary content, try to decode as UTF-8, fallback to base64 if needed
            try:
                content = response.content.decode('utf-8')
            except UnicodeDecodeError:
                import base64
                content = base64.b64encode(response.content).decode('utf-8')
                content_type = "application/base64"
        
        # Clean headers
        cleaned_headers = clean_headers(response.headers)

        base_payload = {
            "status_code": response.status_code,
            "headers": dict(cleaned_headers),
            "content_type": content_type,
            "response_time": elapsed,
            "url": url,
        }

        return _prepare_chunked_response(content, base_payload)
        
    except Exception as e:
        print(f"Scraping Error: {str(e)}")
        return {
            "error": str(e),
            "status_code": 500,
            "chunked": False,
            "chunk_id": None,
            "chunk_index": 0,
            "total_chunks": 0,
            "token_count": 0,
            "instructions": None,
        }


@mcp.tool()
def get_scrape_chunk(chunk_id: str, chunk_index: int) -> Dict[str, Any]:
    """Retrieve a specific chunk from a previously chunked response."""
    _cleanup_chunk_cache()
    entry = _chunk_cache.get(chunk_id)

    if entry is None:
        return {
            "error": "Chunk not found or has expired.",
            "chunked": False,
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "total_chunks": 0,
            "token_count": 0,
            "instructions": None,
        }

    total_chunks = len(entry["chunks"])
    if chunk_index < 1 or chunk_index > total_chunks:
        return {
            **entry.get("metadata", {}),
            "error": f"chunk_index must be between 1 and {total_chunks}.",
            "chunked": True,
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "token_count": entry.get("token_count", 0),
            "instructions": _build_chunk_instructions(chunk_id, min(max(chunk_index, 1), total_chunks), total_chunks),
        }

    entry["created_at"] = time.time()
    chunk_content = entry["chunks"][chunk_index - 1]
    instructions = _build_chunk_instructions(chunk_id, chunk_index, total_chunks)

    return {
        **entry.get("metadata", {}),
        "content": chunk_content,
        "chunked": True,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "token_count": entry.get("token_count", 0),
        "instructions": instructions,
    }

if __name__ == "__main__":
    # Check for transport mode from environment variable
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport == "http":
        # Run with HTTP transport
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", 8000))
        print(f"Starting CloudScraper MCP Server with HTTP transport on {host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        # Run with stdio transport (default)
        print("Starting CloudScraper MCP Server with stdio transport")
        mcp.run()
