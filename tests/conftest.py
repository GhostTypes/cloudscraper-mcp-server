"""
Shared pytest fixtures for CloudScraper MCP Server integration tests.

This module provides common fixtures for testing the MCP server, including
the FastMCP client connection and test data.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastmcp import Client

# Add parent directory to path so we can import server.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import mcp


@pytest.fixture
async def client():
    """
    Provide a connected MCP client for tests.

    The client is automatically connected before the test
    and disconnected after, even if the test fails.

    This uses FastMCP's in-memory client, which is faster and more
    reliable than subprocess-based testing.
    """
    async with Client(mcp) as client:
        yield client


@pytest.fixture
def cloudflare_test_url():
    """URL protected by Cloudflare for testing bypass functionality."""
    return "https://namemc.com/profile/GhostTypes.2"


@pytest.fixture
def simple_test_url():
    """Simple URL without Cloudflare protection for basic testing."""
    return "https://httpbin.org/html"


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file_path(temp_dir):
    """Provide a temporary file path for testing file operations."""
    return os.path.join(temp_dir, "test_output.html")


@pytest.fixture
def expected_html_indicators():
    """Return list of HTML indicators that should appear in valid responses."""
    return [
        "<html",  # HTML opening tag
        "DOCTYPE",  # DOCTYPE declaration
    ]


@pytest.fixture
def expected_markdown_indicators():
    """Return list of indicators that suggest markdown conversion worked."""
    return [
        "#",  # Markdown headers
    ]
