"""Tests for web search tools."""
import pytest

from qwen_dev_cli.tools.web_search import WebSearchTool, SearchDocumentationTool


class TestWebSearchTool:
    """Test WebSearchTool functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic web search."""
        tool = WebSearchTool()
        
        result = await tool.execute(
            query="Python programming language",
            max_results=3
        )
        
        assert result.success
        assert len(result.data) <= 3
        assert result.metadata["engine"] == "duckduckgo"
        assert result.metadata["query"] == "Python programming language"
        
        # Check structure of results
        for item in result.data:
            assert "title" in item
            assert "url" in item
            assert "snippet" in item
            assert "source" in item
    
    @pytest.mark.asyncio
    async def test_search_with_time_range(self):
        """Test search with time range filter."""
        tool = WebSearchTool()
        
        result = await tool.execute(
            query="Gradio 6 release",
            max_results=5,
            time_range="m"  # Last month
        )
        
        assert result.success
        assert result.metadata["time_range"] == "m"
    
    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Test search with unlikely query returns gracefully."""
        tool = WebSearchTool()
        
        result = await tool.execute(
            query="xyzabc123unlikely456query789",
            max_results=5
        )
        
        # Should succeed (DuckDuckGo may return related results even for nonsense)
        assert result.success
        # Just ensure it doesn't crash and returns structured data
        assert isinstance(result.data, list)
        assert result.metadata["count"] >= 0
    
    @pytest.mark.asyncio
    async def test_search_max_results_clamping(self):
        """Test that max_results is clamped to valid range."""
        tool = WebSearchTool()
        
        # Test upper bound
        result = await tool.execute(
            query="Python",
            max_results=100  # Should be clamped to 20
        )
        
        assert result.success
        assert len(result.data) <= 20
        
        # Test lower bound
        result = await tool.execute(
            query="Python",
            max_results=0  # Should be clamped to 1
        )
        
        assert result.success
        assert len(result.data) >= 1
    
    @pytest.mark.asyncio
    async def test_search_gradio_documentation(self):
        """Test real-world use case: searching Gradio documentation."""
        tool = WebSearchTool()
        
        result = await tool.execute(
            query="Gradio 6.0.0 Blocks API documentation",
            max_results=5
        )
        
        assert result.success
        assert len(result.data) > 0
        
        # Should find gradio-related results
        found_gradio = any(
            "gradio" in item["url"].lower() or "gradio" in item["title"].lower()
            for item in result.data
        )
        assert found_gradio, "Should find Gradio-related results"


class TestSearchDocumentationTool:
    """Test SearchDocumentationTool functionality."""
    
    @pytest.mark.asyncio
    async def test_search_without_site_restriction(self):
        """Test documentation search without site restriction."""
        tool = SearchDocumentationTool()
        
        result = await tool.execute(
            query="asyncio documentation",
            max_results=3
        )
        
        assert result.success
        assert len(result.data) <= 3
        assert result.metadata["search_type"] == "documentation"
    
    @pytest.mark.asyncio
    async def test_search_with_site_restriction(self):
        """Test documentation search with site restriction."""
        tool = SearchDocumentationTool()
        
        result = await tool.execute(
            query="Blocks API",
            site="gradio.app",
            max_results=5
        )
        
        assert result.success
        assert result.metadata["search_type"] == "documentation"
        assert result.metadata["restricted_to_site"] == "gradio.app"
        
        # All results should be from gradio.app
        for item in result.data:
            assert "gradio.app" in item["url"].lower()
    
    @pytest.mark.asyncio
    async def test_search_github_docs(self):
        """Test searching GitHub documentation."""
        tool = SearchDocumentationTool()
        
        result = await tool.execute(
            query="Actions workflow syntax",
            site="docs.github.com",
            max_results=3
        )
        
        assert result.success
        
        # Should find GitHub docs
        if result.data:  # May be empty if rate limited
            for item in result.data:
                assert "github.com" in item["url"].lower()
    
    @pytest.mark.asyncio
    async def test_search_readthedocs(self):
        """Test searching Read the Docs."""
        tool = SearchDocumentationTool()
        
        result = await tool.execute(
            query="Django models",
            site="readthedocs.io",
            max_results=3
        )
        
        assert result.success
        # Results may vary, just ensure no crash


class TestToolRegistration:
    """Test that tools are properly registered."""
    
    def test_web_search_tool_properties(self):
        """Test WebSearchTool has correct properties."""
        tool = WebSearchTool()
        
        assert tool.name == "web_search"
        assert tool.category.value == "search"
        assert "query" in tool.parameters
        assert tool.parameters["query"]["required"] is True
    
    def test_search_documentation_tool_properties(self):
        """Test SearchDocumentationTool has correct properties."""
        tool = SearchDocumentationTool()
        
        assert tool.name == "search_documentation"
        assert tool.category.value == "search"
        assert "query" in tool.parameters
        assert "site" in tool.parameters
        assert tool.parameters["query"]["required"] is True
        assert tool.parameters["site"]["required"] is False
