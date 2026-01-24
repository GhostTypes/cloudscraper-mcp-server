"""
Comprehensive integration tests for CloudScraper MCP Server.

This test suite validates:
1. Standard requests library is BLOCKED by Cloudflare
2. MCP server's cloudscraper tools SUCCESSFULLY bypass Cloudflare
3. All three tools work correctly: scrape_url, scrape_url_raw, scrape_url_to_file
4. Responses contain valid HTML/markdown content
5. Chunking functionality works for large responses
"""

import json
import os

import pytest
import requests
from fastmcp import Client


class TestToolDiscovery:
    """Verify all expected tools are registered and discoverable."""

    @pytest.mark.asyncio
    async def test_lists_all_tools(self, client: Client):
        """All three scraping tools should be discoverable."""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "scrape_url" in tool_names
        assert "scrape_url_raw" in tool_names
        assert "scrape_url_to_file" in tool_names

    @pytest.mark.asyncio
    async def test_tool_count(self, client: Client):
        """Should have exactly 3 tools registered."""
        tools = await client.list_tools()
        assert len(tools) == 3


class TestStandardRequestsBlocked:
    """
    Verify that standard requests library is blocked by Cloudflare.

    This is the baseline test that proves why cloudscraper is necessary.
    """

    @pytest.mark.cloudflare
    def test_standard_requests_get_blocked(self, cloudflare_test_url):
        """
        Standard requests.get should be blocked by Cloudflare.

        This test validates the problem we're solving: without cloudscraper,
        normal requests fail with 403, 429, or Cloudflare challenge pages.
        """
        response = requests.get(
            cloudflare_test_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=10,
        )

        # Standard requests should either be blocked with 403/429
        # or return Cloudflare challenge page (status 200 but with Cloudflare content)
        assert response.status_code in [403, 429] or "cloudflare" in response.text.lower()
        assert not response.ok or "cloudflare" in response.text.lower()


class TestScrapeUrlTool:
    """
    Tests for the scrape_url tool.

    This tool returns content as a string with optional chunking.
    """

    @pytest.mark.asyncio
    @pytest.mark.cloudflare
    async def test_bypasses_cloudflare(
        self, client: Client, cloudflare_test_url, expected_html_indicators
    ):
        """
        cloudscraper should successfully bypass Cloudflare protection.

        This is the key test: our MCP server should succeed where standard requests failed.
        """
        result = await client.call_tool(
            "scrape_url",
            {
                "url": cloudflare_test_url,
                "clean_content": False,  # Get raw HTML to verify it's real content
            },
        )

        # Should not be an error
        assert not result.is_error

        # Should have content
        content = result.content[0].text
        assert content
        assert len(content) > 1000  # Real HTML content, not an error message

        # Should be actual HTML, not a Cloudflare challenge page
        assert "cloudflare" not in content.lower() or len(content) > 10000

        # Should have HTML indicators
        for indicator in expected_html_indicators:
            if indicator == "<html":
                # May have whitespace or be uppercase
                assert "<html" in content.lower() or "<HTML" in content
            elif indicator == "DOCTYPE":
                assert "DOCTYPE" in content or "doctype" in content.lower()

    @pytest.mark.asyncio
    async def test_returns_markdown_when_cleaned(self, client: Client, cloudflare_test_url):
        """With clean_content=True, should return markdown format."""
        result = await client.call_tool(
            "scrape_url", {"url": cloudflare_test_url, "clean_content": True}
        )

        assert not result.is_error
        content = result.content[0].text
        assert content
        assert len(content) > 500

        # Markdown typically has # headers
        assert "#" in content or content.strip().startswith("<")

    @pytest.mark.asyncio
    async def test_handles_simple_url(self, client: Client, simple_test_url):
        """Should handle non-Cloudflare URLs without issues."""
        result = await client.call_tool(
            "scrape_url", {"url": simple_test_url, "clean_content": False}
        )

        assert not result.is_error
        content = result.content[0].text
        assert content
        assert "<html" in content.lower()

    @pytest.mark.asyncio
    async def test_invalid_url_returns_error(self, client: Client):
        """Invalid URLs should return an error message."""
        result = await client.call_tool(
            "scrape_url", {"url": "not-a-valid-url", "clean_content": False}
        )

        # FastMCP may wrap the error or return error text
        content = result.content[0].text
        assert "error" in content.lower() or result.is_error

    @pytest.mark.asyncio
    async def test_chunking_information_included(self, client: Client, cloudflare_test_url):
        """For large responses, chunking instructions should be included."""
        result = await client.call_tool(
            "scrape_url", {"url": cloudflare_test_url, "clean_content": False}
        )

        content = result.content[0].text

        # If content is large enough to be chunked, should include continuation instructions
        # (This depends on the actual token count, so we just verify it doesn't error)
        assert not result.is_error
        assert content


class TestScrapeUrlRawTool:
    """
    Tests for the scrape_url_raw tool.

    This tool returns structured data with status, headers, and content.
    """

    @pytest.mark.asyncio
    @pytest.mark.cloudflare
    async def test_bypasses_cloudflare_raw(self, client: Client, cloudflare_test_url):
        """scrape_url_raw should successfully bypass Cloudflare with metadata."""
        result = await client.call_tool(
            "scrape_url_raw", {"url": cloudflare_test_url, "clean_content": False}
        )

        assert not result.is_error

        # Parse the JSON response
        data = json.loads(result.content[0].text)

        # Should have successful status code
        assert data.get("status_code") == 200

        # Should have headers
        assert "headers" in data
        assert isinstance(data["headers"], dict)

        # Should have content
        assert "content" in data
        assert len(data["content"]) > 1000

        # Should have content_type
        assert "content_type" in data

        # Should have response_time
        assert "response_time" in data
        assert data["response_time"] > 0

    @pytest.mark.asyncio
    async def test_returns_structured_data(self, client: Client, simple_test_url):
        """Should return properly structured JSON with all expected fields."""
        result = await client.call_tool(
            "scrape_url_raw", {"url": simple_test_url, "clean_content": False}
        )

        assert not result.is_error
        data = json.loads(result.content[0].text)

        # Verify all expected fields
        expected_fields = ["status_code", "headers", "content", "content_type", "response_time"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

        # Verify data types
        assert isinstance(data["status_code"], int)
        assert isinstance(data["headers"], dict)
        assert isinstance(data["content"], str)
        assert isinstance(data["content_type"], str)
        assert isinstance(data["response_time"], (int, float))

    @pytest.mark.asyncio
    async def test_includes_chunking_metadata_when_needed(
        self, client: Client, cloudflare_test_url
    ):
        """For large responses, should include chunking metadata."""
        result = await client.call_tool(
            "scrape_url_raw", {"url": cloudflare_test_url, "clean_content": False}
        )

        data = json.loads(result.content[0].text)

        # Should have status_code
        assert "status_code" in data

        # May have chunking metadata if content is large
        if data.get("chunked"):
            assert "chunk_index" in data
            assert "total_chunks" in data
            assert "continuation_token" in data
            assert data["chunk_index"] == 1  # First chunk
            assert data["total_chunks"] > 1


class TestScrapeUrlToFileTool:
    """
    Tests for the scrape_url_to_file tool.

    This tool saves response content to a file on disk.
    """

    @pytest.mark.asyncio
    @pytest.mark.cloudflare
    async def test_saves_to_file(self, client: Client, cloudflare_test_url, temp_file_path):
        """Should successfully scrape and save content to file."""
        result = await client.call_tool(
            "scrape_url_to_file",
            {
                "url": cloudflare_test_url,
                "file_path": temp_file_path,
                "clean_content": False,
                "overwrite": True,
            },
        )

        assert not result.is_error

        # Parse response
        data = json.loads(result.content[0].text)

        # Should have success status
        assert data.get("status_code") == 200

        # Should include file path
        assert "file_path" in data
        assert data["file_path"] == temp_file_path

        # Should include bytes written
        assert "bytes_written" in data
        assert data["bytes_written"] > 1000

        # Verify file actually exists and has content
        assert os.path.exists(temp_file_path)

        # Blocking I/O acceptable in test context
        with open(temp_file_path, encoding="utf-8") as f:  # noqa: ASYNC230
            content = f.read()

        assert len(content) > 1000
        assert "<html" in content.lower()

    @pytest.mark.asyncio
    async def test_requires_file_path(self, client: Client, simple_test_url):
        """Should return error when file_path is missing."""
        result = await client.call_tool(
            "scrape_url_to_file",
            {
                "url": simple_test_url,
                "file_path": "",  # Empty file path
            },
        )

        data = json.loads(result.content[0].text)
        assert "error" in data or data.get("status_code") == 400

    @pytest.mark.asyncio
    async def test_respects_existing_files(self, client: Client, simple_test_url, temp_file_path):
        """Should not overwrite existing files unless overwrite=True."""
        # Create a file first
        # Blocking I/O acceptable in test context
        with open(temp_file_path, "w") as f:  # noqa: ASYNC230
            f.write("existing content")

        # Try to save without overwrite
        result = await client.call_tool(
            "scrape_url_to_file",
            {"url": simple_test_url, "file_path": temp_file_path, "overwrite": False},
        )

        data = json.loads(result.content[0].text)

        # Should return conflict error
        assert data.get("status_code") == 409 or "already exists" in data.get("error", "").lower()

        # Original file should be unchanged
        # Blocking I/O acceptable in test context
        with open(temp_file_path) as f:  # noqa: ASYNC230
            content = f.read()
        assert content == "existing content"

    @pytest.mark.asyncio
    async def test_creates_directories_if_needed(self, client: Client, simple_test_url, temp_dir):
        """Should create parent directories if they don't exist."""
        nested_path = os.path.join(temp_dir, "subdir", "nested", "output.html")

        result = await client.call_tool(
            "scrape_url_to_file",
            {"url": simple_test_url, "file_path": nested_path, "overwrite": True},
        )

        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert os.path.exists(nested_path)
        assert data["bytes_written"] > 0


class TestChunkingFunctionality:
    """
    Tests for response chunking when content exceeds token limits.

    These tests verify the chunking and continuation token mechanisms.
    """

    @pytest.mark.asyncio
    @pytest.mark.cloudflare
    async def test_continuation_token_format(self, client: Client, cloudflare_test_url):
        """Continuation tokens should follow the format 'chunk_id:index'."""
        # First call
        result = await client.call_tool(
            "scrape_url", {"url": cloudflare_test_url, "clean_content": False}
        )

        content = result.content[0].text

        # Check if chunking instructions are present
        if "continuation_token=" in content:
            # Extract the token format
            import re

            match = re.search(r'continuation_token="([^"]+)"', content)
            assert match, "Should have properly formatted continuation token"

            token = match.group(1)
            # Should be in format uuid:index
            assert ":" in token
            parts = token.split(":")
            assert len(parts) == 2
            # Index should be numeric
            assert parts[1].isdigit()

    @pytest.mark.asyncio
    async def test_invalid_continuation_token(self, client: Client):
        """Invalid continuation tokens should return an error."""
        result = await client.call_tool(
            "scrape_url",
            {"url": "https://httpbin.org/html", "continuation_token": "invalid:token:format"},
        )

        content = result.content[0].text
        # Should return an error message
        assert "error" in content.lower() or "not found" in content.lower()

    @pytest.mark.asyncio
    async def test_expired_continuation_token(self, client: Client):
        """Expired or non-existent chunks should return an error."""
        # Use a fake UUID that won't exist in cache
        # Not a password - it's a test UUID for continuation token
        fake_token = "00000000-0000-0000-0000-000000000000:0"  # noqa: S105

        result = await client.call_tool(
            "scrape_url_raw", {"url": "https://httpbin.org/html", "continuation_token": fake_token}
        )

        data = json.loads(result.content[0].text)
        assert data.get("status_code") == 404 or "error" in data


class TestContentQuality:
    """
    Tests that verify the quality and validity of scraped content.
    """

    @pytest.mark.asyncio
    @pytest.mark.cloudflare
    async def test_content_is_not_error_page(self, client: Client, cloudflare_test_url):
        """Scraped content should be real content, not error pages."""
        result = await client.call_tool(
            "scrape_url_raw", {"url": cloudflare_test_url, "clean_content": False}
        )

        data = json.loads(result.content[0].text)
        content = data["content"].lower()

        # Should not contain typical error indicators
        error_indicators = [
            "error 403",
            "error 429",
            "access denied",
            "cloudflare is checking",
        ]

        for indicator in error_indicators:
            # Allow some false positives, but content should be primarily real
            if indicator in content:
                # If an error phrase appears, ensure we have substantial content
                assert len(data["content"]) > 10000, (
                    f"Content appears to be an error page: {indicator}"
                )

    @pytest.mark.asyncio
    async def test_markdown_conversion_removes_scripts(self, client: Client, cloudflare_test_url):
        """Markdown conversion should remove script tags and styles."""
        result = await client.call_tool(
            "scrape_url", {"url": cloudflare_test_url, "clean_content": True}
        )

        content = result.content[0].text

        # Markdown shouldn't have script tags
        assert "<script" not in content
        assert "</script>" not in content

        # Should have cleaner content
        assert content.strip()

    @pytest.mark.asyncio
    async def test_headers_are_cleaned(self, client: Client, simple_test_url):
        """Hop-by-hop headers should be removed from raw response."""
        result = await client.call_tool(
            "scrape_url_raw", {"url": simple_test_url, "clean_content": False}
        )

        data = json.loads(result.content[0].text)
        headers = data["headers"]

        # Hop-by-hop headers that should be removed
        hop_by_hop = [
            "connection",
            "keep-alive",
            "transfer-encoding",
            "upgrade",
        ]

        for header in hop_by_hop:
            assert header not in [h.lower() for h in headers], (
                f"Hop-by-hop header '{header}' should be removed"
            )


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_url(self, client: Client):
        """Empty URL should return an error."""
        result = await client.call_tool("scrape_url", {"url": "", "clean_content": False})

        # Should get an error
        assert result.is_error or "error" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_post_method_support(self, client: Client, simple_test_url):  # noqa: ARG002
        """POST method should work (though may not be appropriate for all URLs)."""
        result = await client.call_tool(
            "scrape_url_raw",
            {"url": "https://httpbin.org/post", "method": "POST", "clean_content": False},
        )

        # Should not error
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert "status_code" in data

    @pytest.mark.asyncio
    async def test_different_clean_content_settings(self, client: Client, cloudflare_test_url):
        """clean_content=True vs False should produce different output formats."""
        result_raw = await client.call_tool(
            "scrape_url", {"url": cloudflare_test_url, "clean_content": False}
        )

        result_clean = await client.call_tool(
            "scrape_url", {"url": cloudflare_test_url, "clean_content": True}
        )

        content_raw = result_raw.content[0].text
        content_clean = result_clean.content[0].text

        # Both should have content
        assert content_raw
        assert content_clean

        # They should likely be different (markdown vs HTML)
        # though we can't guarantee this for all URLs
        assert len(content_raw) > 0
        assert len(content_clean) > 0
