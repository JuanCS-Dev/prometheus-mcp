# 🔍 SEARCH & RESEARCH TOOLS AUDIT
**Date:** 2025-11-21  
**Auditor:** Boris Cherny  
**Status:** 🔴 CRITICAL GAPS DETECTED

---

## 📊 EXECUTIVE SUMMARY

**Current State:** 
- ✅ Local file search (ripgrep/grep) - WORKING
- ✅ Semantic code search - WORKING  
- ❌ Web search - **NOT IMPLEMENTED**
- ❌ API documentation search - **NOT IMPLEMENTED**
- ❌ Package registry search (PyPI, npm) - **NOT IMPLEMENTED**

**Risk Assessment:** 🔴 **HIGH** - AI cannot research external APIs/docs autonomously

---

## 🛠️ EXISTING TOOLS (INVENTORY)

### 1. **SearchFilesTool** ✅ PRODUCTION-READY
**Location:** `qwen_dev_cli/tools/search.py:14`

**Capabilities:**
- Text search via ripgrep (primary) / grep (fallback)
- Semantic code search (classes, functions, methods)
- File pattern filtering (`*.py`, `*.ts`, etc.)
- Max results limiting
- Graceful fallback chain

**Quality Score:** 9/10
- ✅ Dual backend (ripgrep + grep)
- ✅ Semantic search integration
- ✅ Error handling robust
- ⚠️ No fuzzy search
- ⚠️ No context lines (`-A`, `-B`, `-C` flags)

**Recommendation:** ADD context lines support for better code understanding

---

### 2. **GetDirectoryTreeTool** ✅ PRODUCTION-READY
**Location:** `qwen_dev_cli/tools/search.py:206`

**Capabilities:**
- Hierarchical file tree visualization
- Max depth limiting
- Auto-filters hidden files and common ignores
- Clean tree formatting

**Quality Score:** 8/10
- ✅ Clean ASCII tree output
- ✅ Ignores noise (node_modules, __pycache__, etc.)
- ⚠️ No option to show hidden files
- ⚠️ No file size info

**Recommendation:** ADD optional `show_hidden` and `show_size` flags

---

## ❌ MISSING TOOLS (CRITICAL GAPS)

### 1. **WebSearchTool** 🔴 CRITICAL
**Status:** NOT IMPLEMENTED

**Why Critical:**
- AI cannot research Gradio 6 API changes autonomously
- Cannot verify external library documentation
- Cannot check GitHub issues for known bugs
- Cannot validate community solutions

**Priority:** P0 (BLOCKING)

**Implementation Options:**

#### Option A: DuckDuckGo (No API Key Required) ⭐ RECOMMENDED
```python
# Uses duckduckgo-search package (no auth needed)
from duckduckgo_search import DDGS

class WebSearchTool(ValidatedTool):
    async def _execute_validated(
        self, 
        query: str, 
        max_results: int = 5,
        time_range: str = "y"  # d/w/m/y
    ) -> ToolResult:
        """Search web via DuckDuckGo."""
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query, 
                max_results=max_results,
                timelimit=time_range
            ))
        return ToolResult(success=True, data=results)
```

**Pros:**
- ✅ No API key required
- ✅ No rate limits
- ✅ Privacy-friendly
- ✅ Simple implementation

**Cons:**
- ⚠️ Less comprehensive than Google
- ⚠️ No advanced search operators

---

#### Option B: SerpAPI (Requires API Key)
```python
# Uses SerpAPI for Google/Bing/Baidu results
import requests

class WebSearchTool(ValidatedTool):
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        
    async def _execute_validated(
        self, 
        query: str, 
        engine: str = "google"
    ) -> ToolResult:
        """Search via SerpAPI."""
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "engine": engine,
                "api_key": self.api_key
            }
        )
        return ToolResult(success=True, data=resp.json())
```

**Pros:**
- ✅ Google-quality results
- ✅ Multiple search engines
- ✅ Structured data extraction

**Cons:**
- ❌ Requires API key + payment
- ❌ Rate limits (100 searches/month free)
- ❌ Additional dependency

---

#### Option C: Tavily AI (LLM-Optimized) ⭐⭐ BEST FOR AI
```python
# Uses Tavily for AI-optimized web search
from tavily import TavilyClient

class WebSearchTool(ValidatedTool):
    def __init__(self):
        self.client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
    async def _execute_validated(
        self, 
        query: str,
        search_depth: str = "advanced"  # basic/advanced
    ) -> ToolResult:
        """AI-optimized web search via Tavily."""
        result = self.client.search(
            query=query,
            search_depth=search_depth,
            include_answer=True,  # Get AI-summarized answer
            include_raw_content=True
        )
        return ToolResult(success=True, data=result)
```

**Pros:**
- ✅ AI-optimized (perfect for LLM consumption)
- ✅ Returns summarized answers
- ✅ Includes source content
- ✅ High-quality filtering

**Cons:**
- ❌ Requires API key
- ❌ Paid after free tier (1000 searches/month)

---

**RECOMMENDATION:** 
- **Phase 1:** Implement DuckDuckGo (immediate, no auth)
- **Phase 2:** Add Tavily as optional upgrade (better quality)

---

### 2. **PackageSearchTool** 🟡 HIGH PRIORITY
**Status:** NOT IMPLEMENTED

**Why Important:**
- AI cannot verify package existence (e.g., `duckduckgo-search`)
- Cannot check latest versions
- Cannot read PyPI/npm metadata

**Implementation:**

```python
class PackageSearchTool(ValidatedTool):
    """Search PyPI/npm registries."""
    
    async def _execute_validated(
        self,
        package_name: str,
        registry: str = "pypi"  # pypi | npm
    ) -> ToolResult:
        """Search package registry."""
        if registry == "pypi":
            url = f"https://pypi.org/pypi/{package_name}/json"
        elif registry == "npm":
            url = f"https://registry.npmjs.org/{package_name}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            
        if resp.status_code == 404:
            return ToolResult(
                success=False,
                error=f"Package '{package_name}' not found in {registry}"
            )
        
        data = resp.json()
        
        # Extract key info
        if registry == "pypi":
            info = {
                "name": data["info"]["name"],
                "version": data["info"]["version"],
                "summary": data["info"]["summary"],
                "author": data["info"]["author"],
                "license": data["info"]["license"],
                "homepage": data["info"]["home_page"],
                "requires_python": data["info"]["requires_python"]
            }
        else:  # npm
            info = {
                "name": data["name"],
                "version": data["dist-tags"]["latest"],
                "description": data["description"],
                "author": data.get("author", {}).get("name"),
                "license": data.get("license"),
                "homepage": data.get("homepage")
            }
        
        return ToolResult(success=True, data=info)
```

**Priority:** P1 (HIGH)

---

### 3. **GitHubSearchTool** 🟡 MEDIUM PRIORITY
**Status:** NOT IMPLEMENTED (but GitHub MCP tools exist)

**Current GitHub Tools:**
- ✅ `get_file_contents` (read files)
- ✅ `search_code` (code search)
- ✅ `search_issues` (issue search)
- ❌ No unified "find similar projects" tool

**Why Useful:**
- Find example implementations
- Check issue trackers for bugs
- Discover community solutions

**Status:** Partially covered by existing MCP tools, LOW priority

---

## 🛡️ HARDENING EXISTING TOOLS

### **SearchFilesTool Improvements**

#### 1. Add Context Lines Support
```python
# Current: Only matches exact line
# Improved: Show surrounding context

class SearchFilesTool(ValidatedTool):
    def __init__(self):
        self.parameters = {
            # ... existing params ...
            "context_before": {
                "type": "integer",
                "description": "Lines of context before match",
                "required": False
            },
            "context_after": {
                "type": "integer",
                "description": "Lines of context after match",
                "required": False
            }
        }
    
    async def _execute_validated(
        self, 
        pattern: str,
        context_before: int = 0,
        context_after: int = 0,
        **kwargs
    ):
        cmd = ["rg", "--line-number", "--with-filename"]
        
        # Add context flags
        if context_before > 0:
            cmd.extend(["-B", str(context_before)])
        if context_after > 0:
            cmd.extend(["-A", str(context_after)])
        
        # ... rest of implementation
```

**Benefit:** Better code comprehension for AI

---

#### 2. Add Fuzzy Search Mode
```python
# Use approximate matching for typos
cmd = ["rg", "--fixed-strings"]  # Disable regex for speed

# OR use fzf-like fuzzy matching
from thefuzz import fuzz

def fuzzy_filter(results, query, threshold=80):
    """Filter results by fuzzy match score."""
    return [
        r for r in results 
        if fuzz.partial_ratio(query.lower(), r["text"].lower()) >= threshold
    ]
```

**Benefit:** Handles typos in search queries

---

#### 3. Add Result Ranking
```python
def rank_results(results, query):
    """Rank results by relevance."""
    for r in results:
        score = 0
        
        # Exact match in filename
        if query in r["file"]:
            score += 10
        
        # Match at start of line
        if r["text"].strip().startswith(query):
            score += 5
        
        # Multiple occurrences
        score += r["text"].count(query)
        
        r["relevance_score"] = score
    
    return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
```

**Benefit:** Most relevant results first

---

### **GetDirectoryTreeTool Improvements**

#### 1. Add File Size Info
```python
def build_tree(dir_path: Path, prefix: str = "", depth: int = 0):
    for item in items:
        size_str = ""
        if item.is_file():
            size = item.stat().st_size
            size_str = f" ({format_size(size)})"
        
        lines.append(
            f"{prefix}{current_prefix}{item.name}{size_str}"
        )

def format_size(bytes: int) -> str:
    """Format bytes as human-readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024
    return f"{bytes:.1f}TB"
```

---

#### 2. Add `.gitignore` Respect
```python
import pathspec

def load_gitignore(path: Path) -> pathspec.PathSpec:
    """Load .gitignore patterns."""
    gitignore = path / ".gitignore"
    if gitignore.exists():
        with open(gitignore) as f:
            patterns = f.read().splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return None

# In build_tree:
gitignore_spec = load_gitignore(dir_path)
items = [
    x for x in items 
    if not gitignore_spec or not gitignore_spec.match_file(str(x))
]
```

**Benefit:** Respects project ignore patterns automatically

---

## 📋 IMPLEMENTATION PLAN

### **Phase 1: Web Search (P0) - 4 hours**

**Tasks:**
1. Install `duckduckgo-search` package (30min)
   ```bash
   pip install duckduckgo-search
   ```

2. Create `qwen_dev_cli/tools/web_search.py` (2h)
   ```python
   class WebSearchTool(ValidatedTool):
       """Search web via DuckDuckGo."""
       # Implementation as shown above
   ```

3. Add to ToolRegistry (30min)
   ```python
   # In tools/__init__.py
   from .web_search import WebSearchTool
   
   # In registry initialization
   registry.register(WebSearchTool())
   ```

4. Write tests (1h)
   ```python
   # tests/tools/test_web_search.py
   @pytest.mark.asyncio
   async def test_web_search_gradio():
       tool = WebSearchTool()
       result = await tool.execute(
           query="Gradio 6 API documentation",
           max_results=3
       )
       assert result.success
       assert len(result.data) <= 3
   ```

**Deliverable:** Functional web search in 4 hours

---

### **Phase 2: Package Search (P1) - 3 hours**

**Tasks:**
1. Create `qwen_dev_cli/tools/package_search.py` (2h)
2. Add to registry (30min)
3. Write tests (30min)

**Deliverable:** PyPI/npm search functional

---

### **Phase 3: Harden Existing Tools (P2) - 4 hours**

**Tasks:**
1. Add context lines to SearchFilesTool (1h)
2. Add file sizes to GetDirectoryTreeTool (1h)
3. Add .gitignore support (1h)
4. Add result ranking (1h)

**Deliverable:** Enhanced search quality

---

## 🎯 SUCCESS CRITERIA

### **For Web Search:**
- ✅ AI can research external APIs autonomously
- ✅ No API keys required (DuckDuckGo)
- ✅ Results parsed and structured
- ✅ Rate limiting handled gracefully
- ✅ Error messages are actionable

### **For Package Search:**
- ✅ AI can verify package existence before suggesting
- ✅ Version compatibility checking
- ✅ Zero false positives (no hallucinated packages)

### **For Hardened Tools:**
- ✅ Search results include context
- ✅ Tree shows file sizes
- ✅ .gitignore patterns respected
- ✅ Results ranked by relevance

---

## 🚨 IMMEDIATE ACTION REQUIRED

**BLOCKING ISSUE:** AI cannot research Gradio 6 API without web search.

**Next Steps:**
1. Get Arquiteto-Chefe approval for implementation plan
2. Implement Phase 1 (Web Search) - **TODAY**
3. Test with real Gradio 6 documentation query
4. Deploy and validate

---

**Audit Complete**  
**Status:** 🔴 CRITICAL - Web search needed ASAP  
**Estimated Fix Time:** 4 hours (Phase 1 only)  
**Blocker Resolution:** Phase 1 completion

---

**Arquiteto-Chefe:** Approval to proceed with Phase 1 (WebSearchTool)?
