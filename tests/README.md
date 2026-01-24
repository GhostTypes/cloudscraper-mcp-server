# CloudScraper MCP Server Integration Tests

Comprehensive test suite for the CloudScraper MCP Server that validates Cloudflare bypass functionality and all server tools.

## Test Overview

This test suite contains **24 integration tests** organized into 7 test classes:

### Test Classes

#### 1. `TestToolDiscovery` (2 tests)
- Validates all 3 MCP tools are properly registered
- Ensures tool discovery works correctly

#### 2. `TestStandardRequestsBlocked` (1 test)
- **KEY TEST**: Proves that standard `requests.get()` is BLOCKED by Cloudflare
- Validates the problem we're solving with cloudscraper

#### 3. `TestScrapeUrlTool` (6 tests)
- **KEY TEST**: Validates cloudscraper successfully bypasses Cloudflare
- Tests markdown conversion (`clean_content` parameter)
- Tests with simple (non-Cloudflare) URLs
- Tests error handling for invalid URLs
- Validates chunking functionality

#### 4. `TestScrapeUrlRawTool` (3 tests)
- **KEY TEST**: Validates Cloudflare bypass with structured response
- Tests response structure (status, headers, content, timing)
- Validates chunking metadata for large responses

#### 5. `TestScrapeUrlToFileTool` (4 tests)
- Tests saving responses to disk
- Tests file path validation
- Tests overwrite protection
- Tests automatic directory creation

#### 6. `TestChunkingFunctionality` (3 tests)
- Tests continuation token format
- Tests invalid continuation token handling
- Tests expired chunk handling

#### 7. `TestContentQuality` (3 tests)
- **KEY TEST**: Validates content is real, not error pages
- Tests markdown conversion removes scripts/styles
- Tests hop-by-hop headers are properly cleaned

#### 8. `TestEdgeCases` (3 tests)
- Tests empty URL handling
- Tests POST method support
- Tests different `clean_content` settings

## Key Test URLs

- **Cloudflare-protected URL**: `https://namemc.com/profile/GhostTypes.2`
  - Used to validate Cloudflare bypass functionality
  - Standard requests library will fail (403/429)
  - cloudscraper should succeed

- **Simple test URL**: `https://httpbin.org/html`
  - Used for basic functionality tests
  - No Cloudflare protection
  - Reliable and fast

## Running Tests

### Install Dependencies

```bash
# Install project with test dependencies
pip install -e ".[dev]"

# Or install pytest directly
pip install pytest pytest-asyncio
```

### Run All Tests

```bash
# Basic run
pytest

# Verbose output
pytest -v

# With detailed tracebacks
pytest -v --tb=short

# Run only Cloudflare tests (marked)
pytest -m cloudflare

# Skip slow tests
pytest -m "not slow"
```

### Run Specific Tests

```bash
# Run specific test class
pytest tests/test_cloudscraper_mcp.py::TestScrapeUrlTool

# Run specific test
pytest tests/test_cloudscraper_mcp.py::TestScrapeUrlTool::test_bypasses_cloudflare

# Run with coverage
pip install pytest-cov
pytest --cov=server --cov-report=html
```

## Test Architecture

### Framework
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **FastMCP Client**: In-memory MCP client for testing

### Fixtures (`conftest.py`)

- `client`: Provides connected MCP client for tests
- `cloudflare_test_url`: Cloudflare-protected URL
- `simple_test_url`: Simple URL without protection
- `temp_dir`: Temporary directory for file operations
- `temp_file_path`: Temporary file path
- `expected_html_indicators`: HTML validation patterns
- `expected_markdown_indicators`: Markdown validation patterns

### Test Strategy

These are **integration tests**, not unit tests:
- Tests run against the **actual MCP server** (not mocks)
- Tests validate **real data** returned from tools
- Tests use **FastMCP's in-memory client** (no subprocess needed)
- Tests make **real HTTP requests** to validate Cloudflare bypass

## Expected Results

All 24 tests should pass:

```
============================= test session starts =============================
collected 24 items

tests/test_cloudscraper_mcp.py::TestToolDiscovery::test_lists_all_tools PASSED
tests/test_cloudscraper_mcp.py::TestToolDiscovery::test_tool_count PASSED
tests/test_cloudscraper_mcp.py::TestStandardRequestsBlocked::test_standard_requests_get_blocked PASSED
tests/test_cloudscraper_mcp.py::TestScrapeUrlTool::test_bypasses_cloudflare PASSED
...
tests/test_cloudscraper_mcp.py::TestEdgeCases::test_different_clean_content_settings PASSED

============================= 24 passed in 2.29s ==============================
```

## Test Coverage

The test suite covers:

- ✅ All 3 MCP tools (`scrape_url`, `scrape_url_raw`, `scrape_url_to_file`)
- ✅ Cloudflare bypass validation
- ✅ Standard requests blocking verification
- ✅ HTML and markdown content quality
- ✅ Chunking and continuation tokens
- ✅ File operations and directory creation
- ✅ Error handling (invalid URLs, missing params)
- ✅ Response structure and metadata
- ✅ Header cleaning
- ✅ POST method support
- ✅ Edge cases

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest -v
```

## Troubleshooting

### Tests fail with "ModuleNotFoundError"
```bash
pip install -e .
```

### Tests fail with import errors
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
# Windows: $env:PYTHONPATH = "$(Get-Location)"
```

### Cloudflare tests are flaky
- Cloudflare protection may change
- Tests include flexible validation to handle this
- Check if namemc.com is still Cloudflare-protected

### Tests are slow
- Some tests make real HTTP requests
- Use `-m "not cloudflare"` to skip Cloudflare tests
- Use `-m "not slow"` to skip slow tests

## Adding New Tests

Follow the pattern in `test_cloudscraper_mcp.py`:

```python
import pytest
from fastmcp import Client

class TestNewFeature:
    """Description of what you're testing."""

    @pytest.mark.asyncio
    async def test_specific_behavior(self, client: Client):
        """Test description."""
        result = await client.call_tool(
            "tool_name",
            {"param": "value"}
        )

        # Validate result
        assert not result.is_error
        content = result.content[0].text
        assert "expected" in content
```

## License

Same as parent project.
