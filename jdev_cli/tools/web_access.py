"""Full unrestricted web access tools for CLI."""
import logging
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .base import ToolResult, ToolCategory
from .validated import ValidatedTool

logger = logging.getLogger(__name__)


class PackageSearchTool(ValidatedTool):
    """Search package registries (PyPI, npm) for package information."""

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.description = "Search PyPI or npm for package metadata (version, dependencies, etc.)"
        self.parameters = {
            "package_name": {
                "type": "string",
                "description": "Name of the package to search for",
                "required": True
            },
            "registry": {
                "type": "string",
                "description": "Package registry: 'pypi' or 'npm' (default: pypi)",
                "required": False
            }
        }

    def get_validators(self):
        return {}

    async def _execute_validated(
        self,
        package_name: str,
        registry: str = "pypi"
    ) -> ToolResult:
        """
        Search package registry for metadata.
        
        Args:
            package_name: Package name
            registry: 'pypi' or 'npm'
        
        Returns:
            ToolResult with package metadata
        """
        try:
            if registry not in ["pypi", "npm"]:
                return ToolResult(
                    success=False,
                    error=f"Invalid registry '{registry}'. Must be 'pypi' or 'npm'"
                )

            logger.info(f"Searching {registry} for package: {package_name}")

            # Build URL
            if registry == "pypi":
                url = f"https://pypi.org/pypi/{package_name}/json"
            else:  # npm
                url = f"https://registry.npmjs.org/{package_name}"

            # Fetch package data
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)

            if resp.status_code == 404:
                return ToolResult(
                    success=False,
                    error=f"Package '{package_name}' not found in {registry}"
                )

            resp.raise_for_status()
            data = resp.json()

            # Extract key info based on registry
            if registry == "pypi":
                info = {
                    "name": data["info"]["name"],
                    "version": data["info"]["version"],
                    "summary": data["info"]["summary"],
                    "author": data["info"]["author"],
                    "license": data["info"]["license"],
                    "homepage": data["info"]["home_page"],
                    "requires_python": data["info"]["requires_python"],
                    "project_url": data["info"]["project_url"],
                    "package_url": f"https://pypi.org/project/{package_name}/",
                    "dependencies": list(data.get("info", {}).get("requires_dist") or [])[:10]  # First 10
                }
            else:  # npm
                info = {
                    "name": data["name"],
                    "version": data.get("dist-tags", {}).get("latest", "unknown"),
                    "description": data.get("description", ""),
                    "author": data.get("author", {}).get("name") if isinstance(data.get("author"), dict) else data.get("author"),
                    "license": data.get("license", "unknown"),
                    "homepage": data.get("homepage", ""),
                    "repository": data.get("repository", {}).get("url") if isinstance(data.get("repository"), dict) else data.get("repository"),
                    "package_url": f"https://www.npmjs.com/package/{package_name}",
                    "dependencies": list(data.get("versions", {}).get(data.get("dist-tags", {}).get("latest", ""), {}).get("dependencies", {}).keys())[:10]
                }

            logger.info(f"Found {package_name} v{info['version']} in {registry}")

            return ToolResult(
                success=True,
                data=info,
                metadata={
                    "registry": registry,
                    "package_name": package_name
                }
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            return ToolResult(
                success=False,
                error=f"HTTP {e.response.status_code}: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Package search failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Package search failed: {str(e)}"
            )


class FetchURLTool(ValidatedTool):
    """Fetch content from any URL (HTML, JSON, text, etc.)."""

    def __init__(self):
        super().__init__()
        self.name = "fetch_url"  # Override auto-generated name
        self.category = ToolCategory.SEARCH
        self.description = "Fetch content from any URL (supports HTML, JSON, plain text)"
        self.parameters = {
            "url": {
                "type": "string",
                "description": "URL to fetch",
                "required": True
            },
            "extract_text": {
                "type": "boolean",
                "description": "If HTML, extract clean text (removes tags)",
                "required": False
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum content length in characters (default: 50000)",
                "required": False
            }
        }

    def get_validators(self):
        return {}

    async def _execute_validated(
        self,
        url: str,
        extract_text: bool = False,
        max_length: int = 50000
    ) -> ToolResult:
        """
        Fetch URL content.
        
        Args:
            url: URL to fetch
            extract_text: Extract plain text from HTML
            max_length: Max content length
        
        Returns:
            ToolResult with content and metadata
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ToolResult(
                    success=False,
                    error=f"Invalid URL: {url}"
                )

            logger.info(f"Fetching URL: {url}")

            # Fetch content
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; QwenDevCLI/1.0)"}
            ) as client:
                resp = await client.get(url)

            resp.raise_for_status()

            # Detect content type
            content_type = resp.headers.get("content-type", "").lower()

            # Process based on content type
            if "application/json" in content_type:
                # JSON response
                content = resp.json()
                content_str = str(content)[:max_length]
                data_type = "json"

            elif "text/html" in content_type:
                # HTML response
                html = resp.text

                if extract_text:
                    # Extract clean text
                    soup = BeautifulSoup(html, "html.parser")

                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()

                    # Get text
                    text = soup.get_text()

                    # Clean up whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    content_str = '\n'.join(chunk for chunk in chunks if chunk)[:max_length]
                    data_type = "text"
                else:
                    content_str = html[:max_length]
                    data_type = "html"

            else:
                # Plain text or other
                content_str = resp.text[:max_length]
                data_type = "text"

            # Check if truncated
            was_truncated = len(resp.text) > max_length

            logger.info(f"Fetched {len(content_str)} chars from {url} (type: {data_type})")

            return ToolResult(
                success=True,
                data={
                    "url": url,
                    "content": content_str,
                    "content_type": content_type,
                    "data_type": data_type,
                    "truncated": was_truncated,
                    "full_length": len(resp.text),
                    "status_code": resp.status_code
                },
                metadata={
                    "url": url,
                    "type": data_type,
                    "size": len(content_str)
                }
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            return ToolResult(
                success=False,
                error=f"HTTP {e.response.status_code}: Failed to fetch {url}"
            )
        except Exception as e:
            logger.error(f"URL fetch failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Failed to fetch URL: {str(e)}"
            )


class DownloadFileTool(ValidatedTool):
    """Download file from URL to local filesystem."""

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.description = "Download file from URL to local path"
        self.parameters = {
            "url": {
                "type": "string",
                "description": "URL of file to download",
                "required": True
            },
            "destination": {
                "type": "string",
                "description": "Local path to save file (optional, auto-generates if not provided)",
                "required": False
            }
        }

    def get_validators(self):
        return {}

    async def _execute_validated(
        self,
        url: str,
        destination: Optional[str] = None
    ) -> ToolResult:
        """
        Download file from URL.
        
        Args:
            url: URL to download from
            destination: Local path to save (auto-generated if None)
        
        Returns:
            ToolResult with download info
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ToolResult(
                    success=False,
                    error=f"Invalid URL: {url}"
                )

            # Auto-generate destination if not provided
            if not destination:
                # Extract filename from URL
                filename = Path(parsed.path).name
                if not filename:
                    filename = "downloaded_file"
                destination = f"./downloads/{filename}"

            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading {url} to {dest_path}")

            # Download file
            async with httpx.AsyncClient(
                timeout=60.0,
                follow_redirects=True
            ) as client:
                async with client.stream("GET", url) as resp:
                    resp.raise_for_status()

                    # Get file size if available
                    total_size = int(resp.headers.get("content-length", 0))

                    # Write to file
                    with open(dest_path, "wb") as f:
                        downloaded = 0
                        async for chunk in resp.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)

            file_size = dest_path.stat().st_size

            logger.info(f"Downloaded {file_size} bytes to {dest_path}")

            return ToolResult(
                success=True,
                data={
                    "url": url,
                    "destination": str(dest_path),
                    "size": file_size,
                    "size_mb": round(file_size / 1024 / 1024, 2)
                },
                metadata={
                    "url": url,
                    "path": str(dest_path),
                    "size": file_size
                }
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            return ToolResult(
                success=False,
                error=f"HTTP {e.response.status_code}: Failed to download {url}"
            )
        except Exception as e:
            logger.error(f"Download failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Download failed: {str(e)}"
            )


class HTTPRequestTool(ValidatedTool):
    """Make arbitrary HTTP requests (GET, POST, PUT, DELETE, etc.)."""

    def __init__(self):
        super().__init__()
        self.name = "http_request"  # Override auto-generated name
        self.category = ToolCategory.SEARCH
        self.description = "Make arbitrary HTTP request with custom method, headers, and body"
        self.parameters = {
            "url": {
                "type": "string",
                "description": "URL to request",
                "required": True
            },
            "method": {
                "type": "string",
                "description": "HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)",
                "required": False
            },
            "headers": {
                "type": "object",
                "description": "Request headers as dict",
                "required": False
            },
            "body": {
                "type": "string",
                "description": "Request body (JSON string or plain text)",
                "required": False
            },
            "params": {
                "type": "object",
                "description": "URL query parameters as dict",
                "required": False
            }
        }

    def get_validators(self):
        return {}

    async def _execute_validated(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        params: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """
        Make HTTP request.
        
        Args:
            url: URL to request
            method: HTTP method
            headers: Custom headers
            body: Request body
            params: Query parameters
        
        Returns:
            ToolResult with response data
        """
        try:
            # Validate method
            method = method.upper()
            valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
            if method not in valid_methods:
                return ToolResult(
                    success=False,
                    error=f"Invalid HTTP method: {method}. Must be one of {valid_methods}"
                )

            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ToolResult(
                    success=False,
                    error=f"Invalid URL: {url}"
                )

            logger.info(f"HTTP {method} {url}")

            # Build request
            request_kwargs = {
                "method": method,
                "url": url,
                "timeout": 30.0,
                "follow_redirects": True
            }

            if headers:
                request_kwargs["headers"] = headers

            if params:
                request_kwargs["params"] = params

            if body:
                # Try to parse as JSON first
                try:
                    import json
                    body_json = json.loads(body)
                    request_kwargs["json"] = body_json
                except (json.JSONDecodeError, TypeError, ValueError):
                    # Not JSON, send as text
                    request_kwargs["content"] = body

            # Make request
            async with httpx.AsyncClient() as client:
                resp = await client.request(**request_kwargs)

            # Parse response
            content_type = resp.headers.get("content-type", "").lower()

            if "application/json" in content_type:
                try:
                    response_data = resp.json()
                except (json.JSONDecodeError, ValueError):
                    response_data = resp.text
            else:
                response_data = resp.text[:10000]  # Limit text responses

            logger.info(f"HTTP {method} {url} -> {resp.status_code}")

            return ToolResult(
                success=True,
                data={
                    "url": url,
                    "method": method,
                    "status_code": resp.status_code,
                    "status_text": resp.reason_phrase,
                    "headers": dict(resp.headers),
                    "body": response_data,
                    "content_type": content_type
                },
                metadata={
                    "url": url,
                    "method": method,
                    "status": resp.status_code
                }
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            return ToolResult(
                success=False,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
        except Exception as e:
            logger.error(f"HTTP request failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"HTTP request failed: {str(e)}"
            )
