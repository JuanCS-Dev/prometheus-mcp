"""
Web Tools - WebFetch, WebSearch
===============================

Web content retrieval tools for Claude Code parity.

Contains:
- WebFetchTool: Fetch URL and convert to text/markdown
- WebSearchTool: Search the web with DuckDuckGo

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Tuple

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult
from jdev_cli.tools._parity_utils import (
    HTMLConverter,
    DEFAULT_USER_AGENT,
    DEFAULT_CACHE_TTL,
    MAX_FETCH_SIZE,
)

logger = logging.getLogger(__name__)


# =============================================================================
# WEB FETCH TOOL
# =============================================================================

class WebFetchTool(Tool):
    """
    Fetch content from URL and convert to readable text.

    Features:
    - HTTP to HTTPS upgrade
    - HTML to text/markdown conversion
    - 15-minute cache with TTL
    - Content length limiting
    - Redirect detection

    Example:
        result = await fetch.execute(url="https://example.com", max_length=5000)
    """

    def __init__(self):
        super().__init__()
        self.name = "web_fetch"
        self.category = ToolCategory.SEARCH
        self.description = "Fetch URL content and convert to readable text/markdown"
        self.parameters = {
            "url": {
                "type": "string",
                "description": "URL to fetch content from",
                "required": True
            },
            "prompt": {
                "type": "string",
                "description": "Optional prompt to process the content",
                "required": False
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum content length to return (default: 10000)",
                "required": False
            }
        }
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl = DEFAULT_CACHE_TTL

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Fetch and process URL content."""
        url = kwargs.get("url", "")
        prompt = kwargs.get("prompt", "")
        max_length = kwargs.get("max_length", 10000)

        # Validate URL
        if not url:
            return ToolResult(success=False, error="URL is required")

        if not url.startswith(("http://", "https://")):
            return ToolResult(success=False, error="URL must start with http:// or https://")

        # Validate max_length
        if not isinstance(max_length, int) or max_length < 100:
            max_length = 10000
        max_length = min(max_length, MAX_FETCH_SIZE)

        # Upgrade HTTP to HTTPS
        if url.startswith("http://"):
            url = "https://" + url[7:]
            logger.debug(f"Upgraded URL to HTTPS: {url}")

        try:
            # Check cache
            if url in self._cache:
                content, cached_at = self._cache[url]
                if time.time() - cached_at < self._cache_ttl:
                    logger.debug(f"Cache hit for {url}")
                    return ToolResult(
                        success=True,
                        data=content[:max_length],
                        metadata={
                            "url": url,
                            "cached": True,
                            "cache_age": int(time.time() - cached_at)
                        }
                    )

            # Fetch URL
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': f'{DEFAULT_USER_AGENT} (CLI coding assistant)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                }
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                # Check for redirect to different host
                final_url = response.geturl()
                original_host = urllib.parse.urlparse(url).netloc
                final_host = urllib.parse.urlparse(final_url).netloc

                if original_host != final_host:
                    return ToolResult(
                        success=True,
                        data={
                            "redirect_detected": True,
                            "original_url": url,
                            "redirect_url": final_url,
                            "message": f"Redirected to different host. Fetch {final_url} to continue."
                        },
                        metadata={"redirect": True}
                    )

                # Check content length
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > MAX_FETCH_SIZE:
                    return ToolResult(
                        success=False,
                        error=f"Content too large ({content_length} bytes). Max: {MAX_FETCH_SIZE}"
                    )

                html = response.read().decode('utf-8', errors='ignore')

            # Check actual size
            if len(html) > MAX_FETCH_SIZE:
                html = html[:MAX_FETCH_SIZE]
                logger.warning(f"Truncated response from {url}")

            # Convert HTML to text
            content = HTMLConverter.to_text(html)

            # Cache the result
            self._cache[url] = (content, time.time())

            # Clean old cache entries (simple LRU)
            if len(self._cache) > 100:
                oldest = min(self._cache.items(), key=lambda x: x[1][1])
                del self._cache[oldest[0]]

            return ToolResult(
                success=True,
                data=content[:max_length],
                metadata={
                    "url": url,
                    "cached": False,
                    "original_length": len(content),
                    "truncated": len(content) > max_length
                }
            )

        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP error fetching {url}: {e.code}")
            return ToolResult(success=False, error=f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            logger.warning(f"URL error fetching {url}: {e.reason}")
            return ToolResult(success=False, error=f"URL Error: {e.reason}")
        except TimeoutError:
            return ToolResult(success=False, error="Request timed out after 30 seconds")
        except Exception as e:
            logger.error(f"WebFetch error: {e}")
            return ToolResult(success=False, error=str(e))

    def clear_cache(self) -> int:
        """Clear the URL cache. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count


# =============================================================================
# WEB SEARCH TOOL
# =============================================================================

class WebSearchTool(Tool):
    """
    Search the web using DuckDuckGo (no API key required).

    Claude Code Parity:
    - Returns search results with titles, URLs, and snippets
    - Includes formatted sources/citations section
    - Supports domain filtering (allowed/blocked)

    Example:
        result = await search.execute(
            query="Python asyncio tutorial",
            num_results=5,
            blocked_domains=["pinterest.com"]
        )
    """

    def __init__(self):
        super().__init__()
        self.name = "web_search"
        self.category = ToolCategory.SEARCH
        self.description = "Search the web and return results with citations"
        self.parameters = {
            "query": {
                "type": "string",
                "description": "Search query",
                "required": True
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "required": False
            },
            "allowed_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only include results from these domains",
                "required": False
            },
            "blocked_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exclude results from these domains",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute web search with citations."""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)
        allowed_domains = kwargs.get("allowed_domains", [])
        blocked_domains = kwargs.get("blocked_domains", [])

        # Validate query
        if not query:
            return ToolResult(success=False, error="Query is required")

        if len(query) < 2:
            return ToolResult(success=False, error="Query too short (min 2 characters)")

        # Validate num_results
        if not isinstance(num_results, int) or num_results < 1:
            num_results = 5
        num_results = min(num_results, 20)  # Hard limit

        # Validate domain lists
        if not isinstance(allowed_domains, list):
            allowed_domains = []
        if not isinstance(blocked_domains, list):
            blocked_domains = []

        try:
            # Use DuckDuckGo HTML search (no API key needed)
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': DEFAULT_USER_AGENT
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Parse results (get extra for filtering)
            results = self._parse_ddg_results(html, num_results * 2)

            if not results:
                return ToolResult(
                    success=True,
                    data={"results": [], "sources": [], "sources_markdown": ""},
                    metadata={"query": query, "num_results": 0, "no_results": True}
                )

            # Apply domain filters
            if allowed_domains:
                results = [
                    r for r in results
                    if any(domain.lower() in r["url"].lower() for domain in allowed_domains)
                ]

            if blocked_domains:
                results = [
                    r for r in results
                    if not any(domain.lower() in r["url"].lower() for domain in blocked_domains)
                ]

            # Limit to requested count
            results = results[:num_results]

            # Format citations (Claude Code parity)
            sources = self._format_sources(results)
            sources_markdown = self._format_sources_markdown(results)

            return ToolResult(
                success=True,
                data={
                    "results": results,
                    "sources": sources,
                    "sources_markdown": sources_markdown,
                },
                metadata={
                    "query": query,
                    "num_results": len(results),
                    "filtered": bool(allowed_domains or blocked_domains)
                }
            )

        except urllib.error.HTTPError as e:
            return ToolResult(success=False, error=f"Search failed: HTTP {e.code}")
        except urllib.error.URLError as e:
            return ToolResult(success=False, error=f"Search failed: {e.reason}")
        except TimeoutError:
            return ToolResult(success=False, error="Search timed out after 10 seconds")
        except Exception as e:
            logger.error(f"WebSearch error: {e}")
            return ToolResult(success=False, error=str(e))

    def _parse_ddg_results(self, html: str, max_results: int) -> List[Dict[str, str]]:
        """Parse DuckDuckGo HTML results."""
        results = []

        # Find result blocks - using multiple patterns for robustness
        patterns = [
            # Pattern 1: Standard result format
            re.compile(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?'
                r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>',
                re.DOTALL
            ),
            # Pattern 2: Alternative format
            re.compile(
                r'<a[^>]+href="([^"]+)"[^>]+class="result__a"[^>]*>(.*?)</a>.*?'
                r'class="result__snippet"[^>]*>(.*?)</(?:a|span)',
                re.DOTALL
            ),
        ]

        for pattern in patterns:
            for match in pattern.finditer(html):
                if len(results) >= max_results:
                    break

                url = match.group(1)
                title = HTMLConverter.decode_entities(match.group(2).strip())
                snippet = HTMLConverter.decode_entities(match.group(3).strip())

                # Clean up URL (DDG wraps URLs)
                if '/l/?uddg=' in url:
                    url_match = re.search(r'uddg=([^&]+)', url)
                    if url_match:
                        url = urllib.parse.unquote(url_match.group(1))

                # Skip if URL is empty or not HTTP(S)
                if not url or not url.startswith(('http://', 'https://')):
                    continue

                # Skip duplicates
                if any(r["url"] == url for r in results):
                    continue

                results.append({
                    "title": title[:200] if title else "No title",
                    "url": url,
                    "snippet": snippet[:500] if snippet else ""
                })

            if results:
                break  # Use first successful pattern

        return results

    def _format_sources(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format results as citation sources."""
        sources = []
        for i, r in enumerate(results, 1):
            sources.append({
                "index": i,
                "title": r["title"],
                "url": r["url"],
                "citation": f"[{i}] [{r['title']}]({r['url']})"
            })
        return sources

    def _format_sources_markdown(self, results: List[Dict[str, str]]) -> str:
        """
        Format sources as markdown for direct inclusion in response.

        Claude Code Pattern: Include Sources section at end of response.
        """
        if not results:
            return ""

        lines = ["", "Sources:"]
        for r in results:
            lines.append(f"- [{r['title']}]({r['url']})")
        return "\n".join(lines)


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_web_tools() -> List[Tool]:
    """Get all web operation tools."""
    return [
        WebFetchTool(),
        WebSearchTool(),
    ]


__all__ = [
    "WebFetchTool",
    "WebSearchTool",
    "get_web_tools",
]
