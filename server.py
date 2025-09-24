import cloudscraper
import time
import os
from urllib.parse import unquote
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

@mcp.tool()
def scrape_url(url: str, method: str = "GET") -> str:
    """
    Scrape a URL and return its content as clean markdown.
    
    Args:
        url: The URL to scrape
        method: HTTP method to use (default: GET)
        
    Returns:
        The content of the page, converted to markdown.
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
            return content
        else:
            # For binary content, try to decode as UTF-8, fallback to error message
            try:
                return response.content.decode('utf-8')
            except UnicodeDecodeError:
                return f"[Binary content - {len(response.content)} bytes]"
        
    except Exception as e:
        print(f"Scraping Error: {str(e)}")
        return f"Error: {str(e)}"

@mcp.tool()
def scrape_url_raw(url: str, method: str = "GET") -> dict:
    """
    Scrape a URL and return the raw, unmodified content.
    
    Args:
        url: The URL to scrape
        method: HTTP method to use (default: GET)
        
    Returns:
        A dictionary containing the status code, headers, and raw content of the page.
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
        
        return {
            "status_code": response.status_code,
            "headers": dict(cleaned_headers),
            "content": content,
            "content_type": content_type,
            "response_time": elapsed
        }
        
    except Exception as e:
        print(f"Scraping Error: {str(e)}")
        return {
            "error": str(e),
            "status_code": 500
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
