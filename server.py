import os
import time
import uuid

import cloudscraper
import tiktoken
from fastmcp import FastMCP

# Create the FastMCP instance
mcp = FastMCP("CloudScraper MCP Server")

# Chunk storage with expiry (stores: chunk_id -> {chunks: list, expiry: timestamp})
chunk_cache = {}
CHUNK_EXPIRY_SECONDS = 120  # 2 minutes
MAX_TOKENS_PER_CHUNK = 10000

# Initialize tiktoken encoder
try:
    encoding = tiktoken.get_encoding("cl100k_base")
except Exception:
    # Fallback if tiktoken has issues
    encoding = None

# Initialize cloudscraper with browser settings
scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "desktop": True},
    delay=1,
    allow_brotli=True,
)


# Chunking helper functions
def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string using tiktoken."""
    if encoding is None:
        # Fallback: approximate 4 characters per token
        return len(text) // 4
    try:
        return len(encoding.encode(text))
    except Exception:
        # Fallback on error
        return len(text) // 4


def cleanup_expired_chunks():
    """Remove expired chunks from the cache."""
    current_time = time.time()
    expired_keys = [key for key, value in chunk_cache.items() if value["expiry"] < current_time]
    for key in expired_keys:
        del chunk_cache[key]


def split_content_into_chunks(content: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> list[str]:
    """Split content into chunks based on token count."""
    if encoding is None:
        # Fallback: split by character count (max_tokens * 4 chars per token)
        chunk_size = max_tokens * 4
        return [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

    # Encode the entire content
    tokens = encoding.encode(content)
    chunks = []

    # Split tokens into chunks
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i : i + max_tokens]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

    return chunks


def store_chunks(chunks: list[str]) -> str:
    """Store chunks in cache and return a unique chunk ID."""
    cleanup_expired_chunks()
    chunk_id = str(uuid.uuid4())
    chunk_cache[chunk_id] = {"chunks": chunks, "expiry": time.time() + CHUNK_EXPIRY_SECONDS}
    return chunk_id


def get_chunk(chunk_id: str, index: int) -> tuple[str | None, int]:
    """Retrieve a specific chunk by ID and index. Returns (chunk, total_chunks) or (None, 0)."""
    cleanup_expired_chunks()
    if chunk_id not in chunk_cache:
        return None, 0

    cache_entry = chunk_cache[chunk_id]
    chunks = cache_entry["chunks"]

    if index < 0 or index >= len(chunks):
        return None, 0

    return chunks[index], len(chunks)


# Hop-by-hop headers that should be removed
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def clean_headers(headers):
    """Remove hop-by-hop headers"""
    cleaned = {
        name: value
        for name, value in headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS
    }
    cleaned.pop("content-encoding", None)
    cleaned.pop("content-length", None)
    return cleaned


def set_user_agent(headers):
    """Set user agent to match Sec-Ch-Ua"""
    headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return headers


def set_security_headers(headers):
    """Set security headers to avoid bot detection"""
    headers["Sec-Ch-Ua"] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
    headers["Sec-Ch-Ua-Mobile"] = "?0"
    headers["Sec-Ch-Ua-Platform"] = '"Windows"'
    headers["Sec-Fetch-Dest"] = "empty"
    headers["Sec-Fetch-Mode"] = "cors"
    headers["Sec-Fetch-Site"] = "same-origin"
    return headers


def set_origin_and_ref(headers, origin, ref):
    """Set origin and referrer headers"""
    headers["Origin"] = origin
    headers["Referer"] = ref
    return headers


def generate_origin_and_ref(url, headers):
    """Generate origin and referrer from URL"""
    data = url.split("/")
    first = data[0]
    base = data[2]
    c_url = f"{first}//{base}/"
    return set_origin_and_ref(headers, c_url, c_url)


def get_headers():
    """Get default headers for requests"""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    return set_security_headers(set_user_agent(headers))


def clean_html_to_markdown(html_content):
    """Convert HTML content to clean markdown format"""
    try:
        from markdownify import markdownify as md

        # Convert HTML to markdown
        return md(html_content, heading_style="ATX")
    except Exception as e:
        print(f"Error converting HTML to markdown: {str(e)}")
        # Return original content if conversion fails
        return html_content


@mcp.tool()
def scrape_url(
    url: str, method: str = "GET", clean_content: bool = True, continuation_token: str = None
) -> str:
    """
    Scrape a URL and return raw content only.

    Args:
        url: The URL to scrape
        method: HTTP method to use (default: GET)
        clean_content: Whether to convert HTML to clean markdown (default: True)
        continuation_token: Token to retrieve next chunk of a previously scraped large response (format: "chunk_id:index")

    Returns:
        Raw content of the page. If content exceeds 10k tokens, it will be chunked and include instructions
        for retrieving remaining chunks using the continuation_token parameter.
    """
    # Handle continuation token for chunked responses
    if continuation_token:
        try:
            chunk_id, chunk_index_str = continuation_token.split(":", 1)
            chunk_index = int(chunk_index_str)

            chunk_content, total_chunks = get_chunk(chunk_id, chunk_index)

            if chunk_content is None:
                return "Error: Chunk not found or expired. Chunks expire after 2 minutes. Please re-scrape the original URL."

            # If there are more chunks, add continuation instructions
            if chunk_index + 1 < total_chunks:
                next_token = f"{chunk_id}:{chunk_index + 1}"
                instruction = f'\n\n--- CHUNK {chunk_index + 1} of {total_chunks} ---\nTo get the next chunk, call scrape_url again with continuation_token="{next_token}"'
                return chunk_content + instruction
            return chunk_content + f"\n\n--- FINAL CHUNK ({chunk_index + 1} of {total_chunks}) ---"

        except Exception as e:
            return f"Error processing continuation token: {str(e)}"

    # Normal scraping logic
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
        content_type = response.headers.get("content-type", "")

        if "text" in content_type or "html" in content_type:
            content = response.text
            # Clean HTML to markdown if requested
            if clean_content and "html" in content_type:
                content = clean_html_to_markdown(content)
        else:
            # For binary content, try to decode as UTF-8, fallback to error message
            try:
                content = response.content.decode("utf-8")
            except UnicodeDecodeError:
                return f"[Binary content - {len(response.content)} bytes]"

        # Check if content needs to be chunked
        token_count = count_tokens(content)

        if token_count > MAX_TOKENS_PER_CHUNK:
            # Split into chunks and store
            chunks = split_content_into_chunks(content, MAX_TOKENS_PER_CHUNK)
            chunk_id = store_chunks(chunks)

            # Return first chunk with instructions
            first_chunk = chunks[0]
            next_token = f"{chunk_id}:1"
            instruction = f'\n\n--- CHUNK 1 of {len(chunks)} ---\nThis response was chunked due to size ({token_count} tokens). To get the next chunk, call scrape_url again with continuation_token="{next_token}"'
            return first_chunk + instruction

        return content

    except Exception as e:
        print(f"Scraping Error: {str(e)}")
        return f"Error: {str(e)}"


@mcp.tool()
def scrape_url_raw(
    url: str, method: str = "GET", clean_content: bool = True, continuation_token: str = None
) -> dict:
    """
    Scrape a URL using cloudscraper to bypass Cloudflare protection.

    Args:
        url: The URL to scrape
        method: HTTP method to use (default: GET)
        clean_content: Whether to convert HTML to clean markdown (default: True)
        continuation_token: Token to retrieve next chunk of a previously scraped large response (format: "chunk_id:index")

    Returns:
        Dictionary containing status code, headers, and content. For large responses (>10k tokens),
        includes chunking metadata with continuation_token for retrieving additional chunks.
    """
    # Handle continuation token for chunked responses
    if continuation_token:
        try:
            chunk_id, chunk_index_str = continuation_token.split(":", 1)
            chunk_index = int(chunk_index_str)

            chunk_content, total_chunks = get_chunk(chunk_id, chunk_index)

            if chunk_content is None:
                return {
                    "error": "Chunk not found or expired. Chunks expire after 2 minutes. Please re-scrape the original URL.",
                    "status_code": 404,
                }

            # Build response with chunk metadata
            result = {
                "content": chunk_content,
                "chunked": True,
                "chunk_index": chunk_index + 1,  # 1-indexed for user display
                "total_chunks": total_chunks,
            }

            # If there are more chunks, add continuation token
            if chunk_index + 1 < total_chunks:
                result["continuation_token"] = f"{chunk_id}:{chunk_index + 1}"
                result["message"] = (
                    f"Chunk {chunk_index + 1} of {total_chunks}. Use continuation_token to get the next chunk."
                )
            else:
                result["message"] = f"Final chunk ({chunk_index + 1} of {total_chunks})."

            return result

        except Exception as e:
            return {"error": f"Error processing continuation token: {str(e)}", "status_code": 400}

    # Normal scraping logic
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
        content_type = response.headers.get("content-type", "")

        # Get the properly decompressed content
        if "text" in content_type or "html" in content_type:
            content = response.text
            # Clean HTML to markdown if requested
            if clean_content and "html" in content_type:
                content = clean_html_to_markdown(content)
        else:
            # For binary content, try to decode as UTF-8, fallback to base64 if needed
            try:
                content = response.content.decode("utf-8")
            except UnicodeDecodeError:
                import base64

                content = base64.b64encode(response.content).decode("utf-8")
                content_type = "application/base64"

        # Clean headers
        cleaned_headers = clean_headers(response.headers)

        # Check if content needs to be chunked
        token_count = count_tokens(content)

        if token_count > MAX_TOKENS_PER_CHUNK:
            # Split into chunks and store
            chunks = split_content_into_chunks(content, MAX_TOKENS_PER_CHUNK)
            chunk_id = store_chunks(chunks)

            # Return first chunk with metadata
            return {
                "status_code": response.status_code,
                "headers": dict(cleaned_headers),
                "content": chunks[0],
                "content_type": content_type,
                "response_time": elapsed,
                "chunked": True,
                "chunk_index": 1,
                "total_chunks": len(chunks),
                "continuation_token": f"{chunk_id}:1",
                "total_tokens": token_count,
                "message": f"Response chunked into {len(chunks)} parts due to size ({token_count} tokens). Use continuation_token to get the next chunk.",
            }

        return {
            "status_code": response.status_code,
            "headers": dict(cleaned_headers),
            "content": content,
            "content_type": content_type,
            "response_time": elapsed,
        }

    except Exception as e:
        print(f"Scraping Error: {str(e)}")
        return {"error": str(e), "status_code": 500}


@mcp.tool(
    description="Scrape a URL and save the raw response body to a file in your current workspace. Always provide the file_path from the project directory you are actively working in so the content lands in the correct location."
)
def scrape_url_to_file(
    url: str,
    file_path: str,
    method: str = "GET",
    clean_content: bool = False,
    overwrite: bool = False,
) -> dict:
    """
    Scrape a URL and save the entire response body to a file on disk.

    Args:
        url: The URL to scrape.
        file_path: The path (relative to your current workspace or absolute) where the response should be saved.
        method: HTTP method to use (default: GET).
        clean_content: Whether to convert HTML to clean markdown before saving (default: False).
        overwrite: Whether to overwrite an existing file at the target path (default: False).

    Returns:
        Dictionary containing status code, headers, response metadata, and resolved file path information.
    """
    if not file_path or not file_path.strip():
        return {
            "error": "file_path is required. Provide a path in your current workspace where the content should be saved.",
            "status_code": 400,
        }

    expanded_path = os.path.expanduser(file_path.strip())
    target_path = os.path.abspath(expanded_path)
    directory = os.path.dirname(target_path)

    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            return {
                "error": f"Unable to create directory '{directory}': {str(e)}",
                "status_code": 500,
            }

    if not overwrite and os.path.exists(target_path):
        return {
            "error": f"File already exists at {target_path}. Set overwrite=True to replace it.",
            "status_code": 409,
        }

    try:
        headers = get_headers()
        headers = generate_origin_and_ref(url, headers)

        start = time.time()
        if method.upper() == "GET":
            response = scraper.get(url, headers=headers, stream=False)
        else:
            response = scraper.post(url, headers=headers, stream=False)
        end = time.time()
        elapsed = end - start

        content_type = response.headers.get("content-type", "")
        cleaned_headers = clean_headers(response.headers)

        is_text_content = "text" in content_type or "html" in content_type or content_type == ""

        if is_text_content:
            content = response.text
            if clean_content and "html" in content_type:
                content = clean_html_to_markdown(content)
            write_mode = "w"
            write_kwargs = {"encoding": "utf-8"}
            bytes_length = len(content.encode("utf-8"))
        else:
            content = response.content
            write_mode = "wb"
            write_kwargs = {}
            bytes_length = len(content)

        with open(target_path, write_mode, **write_kwargs) as file_handle:
            file_handle.write(content)

        return {
            "status_code": response.status_code,
            "headers": dict(cleaned_headers),
            "content_type": content_type,
            "response_time": elapsed,
            "file_path": target_path,
            "bytes_written": bytes_length,
            "message": "Saved response body to file.",
        }

    except Exception as e:
        print(f"Scraping Error: {str(e)}")
        return {"error": str(e), "status_code": 500}


if __name__ == "__main__":
    # Check for transport mode from environment variable
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        # Run with HTTP transport
        # Intentional binding to all interfaces for Docker/container environments
        host = os.environ.get("MCP_HOST", "0.0.0.0")  # noqa: S104
        port = int(os.environ.get("MCP_PORT", 8000))
        print(f"Starting CloudScraper MCP Server with HTTP transport on {host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        # Run with stdio transport (default)
        print("Starting CloudScraper MCP Server with stdio transport")
        mcp.run()
