"""Tests for full web access tools."""
import pytest
from pathlib import Path

from jdev_cli.tools.web_access import (
    PackageSearchTool,
    FetchURLTool,
    DownloadFileTool,
    HTTPRequestTool
)


class TestPackageSearchTool:
    """Test PackageSearchTool functionality."""

    @pytest.mark.asyncio
    async def test_search_pypi_package(self):
        """Test searching PyPI for a known package."""
        tool = PackageSearchTool()

        result = await tool.execute(
            package_name="requests",
            registry="pypi"
        )

        assert result.success
        assert result.data["name"] == "requests"
        assert "version" in result.data
        assert "summary" in result.data
        assert result.metadata["registry"] == "pypi"

    @pytest.mark.asyncio
    async def test_search_npm_package(self):
        """Test searching npm for a known package."""
        tool = PackageSearchTool()

        result = await tool.execute(
            package_name="express",
            registry="npm"
        )

        assert result.success
        assert result.data["name"] == "express"
        assert "version" in result.data
        assert "description" in result.data
        assert result.metadata["registry"] == "npm"

    @pytest.mark.asyncio
    async def test_search_nonexistent_package(self):
        """Test searching for nonexistent package."""
        tool = PackageSearchTool()

        result = await tool.execute(
            package_name="this-package-definitely-does-not-exist-xyz123",
            registry="pypi"
        )

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_registry(self):
        """Test invalid registry name."""
        tool = PackageSearchTool()

        result = await tool.execute(
            package_name="test",
            registry="invalid"
        )

        assert not result.success
        assert "invalid registry" in result.error.lower()

    @pytest.mark.asyncio
    async def test_default_registry_pypi(self):
        """Test default registry is PyPI."""
        tool = PackageSearchTool()

        result = await tool.execute(package_name="pip")

        assert result.success
        assert result.metadata["registry"] == "pypi"


class TestFetchURLTool:
    """Test FetchURLTool functionality."""

    @pytest.mark.asyncio
    async def test_fetch_json_api(self):
        """Test fetching JSON from API."""
        tool = FetchURLTool()

        result = await tool.execute(
            url="https://api.github.com/repos/python/cpython"
        )

        assert result.success
        assert result.data["data_type"] == "json"
        assert "content" in result.data
        assert result.data["status_code"] == 200

    @pytest.mark.asyncio
    async def test_fetch_html_page(self):
        """Test fetching HTML page."""
        tool = FetchURLTool()

        result = await tool.execute(
            url="https://www.python.org",
            extract_text=False
        )

        assert result.success
        assert result.data["data_type"] in ["html", "text"]
        assert "<" in result.data["content"]  # Contains HTML tags

    @pytest.mark.asyncio
    async def test_fetch_html_with_text_extraction(self):
        """Test fetching HTML with text extraction."""
        tool = FetchURLTool()

        result = await tool.execute(
            url="https://www.python.org",
            extract_text=True
        )

        assert result.success
        assert result.data["data_type"] == "text"
        # Should have text but minimal HTML tags
        assert "python" in result.data["content"].lower()

    @pytest.mark.asyncio
    async def test_fetch_invalid_url(self):
        """Test fetching invalid URL."""
        tool = FetchURLTool()

        result = await tool.execute(url="not-a-valid-url")

        assert not result.success
        assert "invalid url" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_with_max_length(self):
        """Test max_length parameter."""
        tool = FetchURLTool()

        result = await tool.execute(
            url="https://www.python.org",
            max_length=1000
        )

        assert result.success
        assert len(result.data["content"]) <= 1000
        if result.data["truncated"]:
            assert result.data["full_length"] > 1000


class TestDownloadFileTool:
    """Test DownloadFileTool functionality."""

    @pytest.mark.asyncio
    async def test_download_small_file(self):
        """Test downloading a small file."""
        tool = DownloadFileTool()

        # Download a small text file from GitHub
        result = await tool.execute(
            url="https://raw.githubusercontent.com/python/cpython/main/README.rst",
            destination="./test_downloads/README.rst"
        )

        assert result.success
        assert Path(result.data["destination"]).exists()
        assert result.data["size"] > 0

        # Cleanup
        Path(result.data["destination"]).unlink()
        Path(result.data["destination"]).parent.rmdir()

    @pytest.mark.asyncio
    async def test_download_auto_destination(self):
        """Test download with auto-generated destination."""
        tool = DownloadFileTool()

        result = await tool.execute(
            url="https://raw.githubusercontent.com/python/cpython/main/LICENSE"
        )

        assert result.success
        dest_path = Path(result.data["destination"])
        assert dest_path.exists()
        assert "LICENSE" in dest_path.name

        # Cleanup
        dest_path.unlink()
        if dest_path.parent.name == "downloads":
            try:
                dest_path.parent.rmdir()
            except:
                pass

    @pytest.mark.asyncio
    async def test_download_invalid_url(self):
        """Test download with invalid URL."""
        tool = DownloadFileTool()

        result = await tool.execute(url="not-a-valid-url")

        assert not result.success
        assert "invalid url" in result.error.lower()


class TestHTTPRequestTool:
    """Test HTTPRequestTool functionality."""

    @pytest.mark.asyncio
    async def test_get_request(self):
        """Test GET request."""
        tool = HTTPRequestTool()

        result = await tool.execute(
            url="https://httpbin.org/get",
            method="GET"
        )

        assert result.success
        assert result.data["method"] == "GET"
        assert result.data["status_code"] == 200

    @pytest.mark.asyncio
    async def test_post_request_with_json(self):
        """Test POST request with JSON body."""
        tool = HTTPRequestTool()

        result = await tool.execute(
            url="https://httpbin.org/post",
            method="POST",
            body='{"test": "data", "number": 123}'
        )

        assert result.success
        assert result.data["method"] == "POST"
        assert result.data["status_code"] == 200

    @pytest.mark.asyncio
    async def test_request_with_headers(self):
        """Test request with custom headers."""
        tool = HTTPRequestTool()

        result = await tool.execute(
            url="https://httpbin.org/headers",
            method="GET",
            headers={"X-Custom-Header": "test-value"}
        )

        assert result.success
        assert result.data["status_code"] == 200

    @pytest.mark.asyncio
    async def test_request_with_params(self):
        """Test request with query parameters."""
        tool = HTTPRequestTool()

        result = await tool.execute(
            url="https://httpbin.org/get",
            method="GET",
            params={"foo": "bar", "test": "123"}
        )

        assert result.success
        assert result.data["status_code"] == 200

    @pytest.mark.asyncio
    async def test_invalid_method(self):
        """Test invalid HTTP method."""
        tool = HTTPRequestTool()

        result = await tool.execute(
            url="https://httpbin.org/get",
            method="INVALID"
        )

        assert not result.success
        assert "invalid http method" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test invalid URL."""
        tool = HTTPRequestTool()

        result = await tool.execute(
            url="not-a-valid-url",
            method="GET"
        )

        assert not result.success
        assert "invalid url" in result.error.lower()


class TestToolRegistration:
    """Test tool registration properties."""

    def test_package_search_tool_properties(self):
        """Test PackageSearchTool properties."""
        tool = PackageSearchTool()

        assert tool.name == "package_search"
        assert tool.category.value == "search"
        assert "package_name" in tool.parameters
        assert tool.parameters["package_name"]["required"] is True

    def test_fetch_url_tool_properties(self):
        """Test FetchURLTool properties."""
        tool = FetchURLTool()

        assert tool.name == "fetch_url"
        assert tool.category.value == "search"
        assert "url" in tool.parameters
        assert tool.parameters["url"]["required"] is True

    def test_download_file_tool_properties(self):
        """Test DownloadFileTool properties."""
        tool = DownloadFileTool()

        assert tool.name == "download_file"
        assert tool.category.value == "search"
        assert "url" in tool.parameters
        assert tool.parameters["url"]["required"] is True

    def test_http_request_tool_properties(self):
        """Test HTTPRequestTool properties."""
        tool = HTTPRequestTool()

        assert tool.name == "http_request"
        assert tool.category.value == "search"
        assert "url" in tool.parameters
        assert tool.parameters["url"]["required"] is True
        assert "method" in tool.parameters
