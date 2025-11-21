"""Web search tool using DuckDuckGo."""
import logging
from typing import Optional, List, Dict, Any

from ddgs import DDGS

from .base import Tool, ToolResult, ToolCategory
from .validated import ValidatedTool

logger = logging.getLogger(__name__)


class WebSearchTool(ValidatedTool):
    """Search the web using DuckDuckGo (no API key required)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.description = "Search the web for information using DuckDuckGo"
        self.parameters = {
            "query": {
                "type": "string",
                "description": "Search query",
                "required": True
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5, max: 20)",
                "required": False
            },
            "time_range": {
                "type": "string",
                "description": "Time range filter: 'd' (day), 'w' (week), 'm' (month), 'y' (year), or None for all time",
                "required": False
            }
        }
    
    def get_validators(self):
        """No additional validation needed."""
        return {}
    
    async def _execute_validated(
        self,
        query: str,
        max_results: int = 5,
        time_range: Optional[str] = None
    ) -> ToolResult:
        """
        Search the web via DuckDuckGo.
        
        Args:
            query: Search query string
            max_results: Number of results to return (1-20)
            time_range: Filter by time ('d', 'w', 'm', 'y', or None)
        
        Returns:
            ToolResult with list of search results
        """
        try:
            # Clamp max_results
            max_results = max(1, min(max_results, 20))
            
            # Validate time_range
            valid_time_ranges = ['d', 'w', 'm', 'y', None]
            if time_range not in valid_time_ranges:
                logger.warning(
                    f"Invalid time_range '{time_range}', using None. "
                    f"Valid values: {valid_time_ranges}"
                )
                time_range = None
            
            logger.info(f"Web search: query='{query}', max_results={max_results}, time_range={time_range}")
            
            # Execute search
            with DDGS() as ddgs:
                results_raw = ddgs.text(
                    query=query,
                    max_results=max_results,
                    timelimit=time_range
                )
            
            if not results_raw:
                return ToolResult(
                    success=True,
                    data=[],
                    metadata={
                        "query": query,
                        "count": 0,
                        "message": "No results found",
                        "engine": "duckduckgo"
                    }
                )
            
            # Parse and structure results
            results = []
            for item in results_raw:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "source": item.get("href", "").split("/")[2] if item.get("href") else ""
                })
            
            logger.info(f"Web search successful: {len(results)} results")
            
            return ToolResult(
                success=True,
                data=results,
                metadata={
                    "query": query,
                    "count": len(results),
                    "engine": "duckduckgo",
                    "time_range": time_range
                }
            )
        
        except Exception as e:
            logger.error(f"Web search failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Web search failed: {str(e)}"
            )


class SearchDocumentationTool(ValidatedTool):
    """
    Specialized tool for searching technical documentation.
    
    Uses site-specific search to target documentation sites directly.
    """
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.description = "Search technical documentation sites (GitHub, Read the Docs, official docs)"
        self.parameters = {
            "query": {
                "type": "string",
                "description": "Search query",
                "required": True
            },
            "site": {
                "type": "string",
                "description": "Specific site to search (e.g., 'github.com', 'readthedocs.io', 'gradio.app')",
                "required": False
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results",
                "required": False
            }
        }
    
    def get_validators(self):
        return {}
    
    async def _execute_validated(
        self,
        query: str,
        site: Optional[str] = None,
        max_results: int = 5
    ) -> ToolResult:
        """
        Search documentation with optional site filtering.
        
        Args:
            query: Search query
            site: Optional site to restrict search to
            max_results: Number of results
        
        Returns:
            ToolResult with documentation search results
        """
        try:
            # Build search query with site filter if provided
            search_query = query
            if site:
                search_query = f"site:{site} {query}"
            
            logger.info(f"Documentation search: '{search_query}'")
            
            # Use WebSearchTool internally
            web_tool = WebSearchTool()
            result = await web_tool.execute(
                query=search_query,
                max_results=max_results
            )
            
            if not result.success:
                return result
            
            # Add metadata about doc search
            result.metadata["search_type"] = "documentation"
            if site:
                result.metadata["restricted_to_site"] = site
            
            return result
        
        except Exception as e:
            logger.error(f"Documentation search failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Documentation search failed: {str(e)}"
            )
