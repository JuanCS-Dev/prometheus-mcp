# MIGRATION GUIDE v2.0

**Date**: 2025-11-24  
**Version**: qwen-dev-cli v2.0  
**Compliance**: Vértice Constitution v3.0 - P3 (Clear Error Messages)

---

## EXECUTIVE SUMMARY

This guide helps you migrate from **qwen-dev-cli v1.x** to **v2.0**.

**Breaking Changes**: 2  
**Deprecation Warnings**: 1  
**New Features**: Tool Registry Factory Functions

---

## BREAKING CHANGES

### 1. AgentTask Field Renamed: `description` → `request`

**Status**: ⚠️ DEPRECATED (Auto-migration active until v3.0)

**Old Code (v1.x)**:
```python
from qwen_dev_cli.agents.base import AgentTask

task = AgentTask(
    description="Analyze the codebase",  # ❌ Deprecated
    context={"repo": "/path/to/repo"}
)
```

**New Code (v2.0)**:
```python
from qwen_dev_cli.agents.base import AgentTask

task = AgentTask(
    request="Analyze the codebase",  # ✅ Use 'request' instead
    context={"repo": "/path/to/repo"}
)
```

**Behavior**:
- Using `description` will emit a `DeprecationWarning`
- Value is automatically copied to `request` field
- Will be **removed in v3.0**

**Migration Steps**:
1. Search your codebase: `grep -r "description=" --include="*.py"`
2. Replace all `description=` with `request=` in AgentTask instantiation
3. Run tests to ensure no warnings

---

### 2. MCPClient Requires ToolRegistry

**Status**: 🔴 BREAKING (Use factory function instead)

**Old Code (v1.x)**:
```python
from qwen_dev_cli.core.mcp_client import MCPClient

# ❌ This fails in v2.0
mcp = MCPClient()
```

**New Code (v2.0) - RECOMMENDED**:
```python
from qwen_dev_cli.core.mcp import create_mcp_client

# ✅ Use factory function with auto-setup
mcp = create_mcp_client()
```

**Alternative (Manual Setup)**:
```python
from qwen_dev_cli.tools.registry_setup import setup_default_tools

registry, mcp = setup_default_tools()
```

**Why This Changed**:
- Previous empty registry caused cryptic "Tool not found" errors
- New factory provides zero-config experience
- Explicit tool registration for custom setups

**Migration Steps**:
1. Replace all `MCPClient()` with `create_mcp_client()`
2. Or use `setup_default_tools()` for more control
3. See "Tool Registry Setup" section below

---

## NEW FEATURES

### Tool Registry Factory Functions

**Location**: `qwen_dev_cli.tools.registry_setup`

**Purpose**: Zero-config tool registration for agents

#### Quick Start (Recommended)
```python
from qwen_dev_cli.core.mcp import create_mcp_client

# Auto-setup with all default tools
mcp = create_mcp_client()
```

#### Default Tools Setup
```python
from qwen_dev_cli.tools.registry_setup import setup_default_tools

# Full control over tool groups
registry, mcp = setup_default_tools(
    include_file_ops=True,   # read, write, edit, move, copy, mkdir
    include_bash=True,       # bash command execution
    include_search=True,     # search files, directory tree
    include_git=True,        # git status, git diff
    custom_tools=[]          # Your custom tools
)
```

**Default Tools Included** (11 tools):
- `read_file`, `write_file`, `edit_file`
- `create_directory`, `move_file`, `copy_file`
- `bash_command`
- `search_files`, `get_directory_tree`
- `git_status`, `git_diff`

#### Minimal Setup (3 tools only)
```python
from qwen_dev_cli.tools.registry_setup import setup_minimal_tools

registry, mcp = setup_minimal_tools()
# Registers: read_file, write_file, edit_file
```

#### Read-Only Setup (Security)
```python
from qwen_dev_cli.tools.registry_setup import setup_readonly_tools

registry, mcp = setup_readonly_tools()
# No write operations, safe for untrusted execution
```

#### Custom Tools Only
```python
from qwen_dev_cli.tools.registry_setup import setup_custom_tools
from my_tools import MyCustomTool

registry, mcp = setup_custom_tools([
    MyCustomTool(),
    AnotherCustomTool()
])
# No default tools, only your custom tools
```

---

## AGENT USAGE PATTERNS

### Pattern 1: Simple Agent Execution
```python
from qwen_dev_cli.core.llm import LLMClient
from qwen_dev_cli.core.mcp import create_mcp_client
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.base import AgentTask

# 1. Setup
llm = LLMClient()
mcp = create_mcp_client()  # Auto-registers tools

# 2. Create agent
agent = PlannerAgent(llm, mcp)

# 3. Create task (note: 'request' not 'description')
task = AgentTask(
    request="Create a plan to refactor the authentication module",
    context={"project_root": "/path/to/project"}
)

# 4. Execute
response = await agent.execute(task)

if response.success:
    print(response.data)
else:
    print(f"Error: {response.error}")
```

### Pattern 2: Custom Tool Configuration
```python
from qwen_dev_cli.tools.registry_setup import setup_default_tools
from my_company.tools import CompanySpecificTool

# Setup with custom tools
registry, mcp = setup_default_tools(
    include_bash=False,  # Disable bash for security
    custom_tools=[CompanySpecificTool()]
)

# Use with agent
agent = PlannerAgent(llm, mcp)
```

### Pattern 3: Multiple Agents, Shared Registry
```python
from qwen_dev_cli.tools.registry_setup import setup_default_tools

# One registry for all agents
registry, mcp = setup_default_tools()

# Multiple agents share same tools
planner = PlannerAgent(llm, mcp)
explorer = ExplorerAgent(llm, mcp)
refactorer = RefactorerAgent(llm, mcp)
```

---

## TESTING YOUR MIGRATION

### Step 1: Check for Deprecation Warnings
```bash
# Run with warnings enabled
python -W default::DeprecationWarning your_script.py

# Or in pytest
pytest -W default::DeprecationWarning tests/
```

**Expected**: No warnings about `description` field

### Step 2: Verify Tool Registration
```python
from qwen_dev_cli.core.mcp import create_mcp_client

mcp = create_mcp_client()

# Should print 11+ tools
print(f"Registered tools: {len(mcp.registry.tools)}")
print(f"Tools: {list(mcp.registry.tools.keys())}")
```

**Expected Output**:
```
Registered tools: 11
Tools: ['read_file', 'write_file', 'edit_file', 'create_directory', 
        'move_file', 'copy_file', 'bash_command', 'search_files', 
        'get_directory_tree', 'git_status', 'git_diff']
```

### Step 3: Run Integration Tests
```bash
# Run full test suite
pytest tests/

# Run only agent tests
pytest tests/test_agents.py -v
```

**Expected**: All tests pass with 0 failures

---

## COMMON MIGRATION ERRORS

### Error 1: "Tool 'read_file' not found"

**Cause**: MCPClient created without tools registered

**Fix**:
```python
# ❌ Don't do this
from qwen_dev_cli.tools.base import ToolRegistry
from qwen_dev_cli.core.mcp_client import MCPClient
registry = ToolRegistry()
mcp = MCPClient(registry)  # Empty registry!

# ✅ Do this instead
from qwen_dev_cli.core.mcp import create_mcp_client
mcp = create_mcp_client()  # Auto-registers tools
```

### Error 2: "AgentTask() got unexpected keyword argument 'description'"

**Cause**: Using old field name without validator triggering

**Fix**:
```python
# ❌ Old way
task = AgentTask(description="...")

# ✅ New way
task = AgentTask(request="...")
```

### Error 3: "TypeError: MCPClient() missing required argument: 'registry'"

**Cause**: Trying to instantiate MCPClient directly without registry

**Fix**: Use factory function
```python
from qwen_dev_cli.core.mcp import create_mcp_client
mcp = create_mcp_client()
```

---

## BACKWARDS COMPATIBILITY

### What Still Works (v1.x → v2.0)

✅ **AgentTask with 'description' field** (with warning)  
✅ **Importing from `mcp_client` module** (redirects to `mcp`)  
✅ **All existing agents** (no API changes)  
✅ **Tool execution** (same interface)

### What No Longer Works

❌ **MCPClient() without arguments**  
❌ **Empty ToolRegistry expecting agents to work**

---

## TIMELINE

| Version | Status | Description |
|---------|--------|-------------|
| v1.x | Old | `description` field, manual tool setup |
| **v2.0** | **Current** | `request` field, factory functions, deprecation warnings |
| v2.x | Stable | Continue deprecation warnings |
| v3.0 | Future | Remove `description` support entirely |

**Recommendation**: Migrate fully to v2.0 patterns now to avoid v3.0 breakage.

---

## GETTING HELP

### Documentation
- README.md - Quick start guide
- QA_REPORT_ULTRATHINK.md - Known issues and fixes
- RELATORIO_PROBLEMAS_COMPLETO.md - Problem analysis

### Code Examples
- `examples/simple_agent_execution.py` (TODO)
- `examples/custom_tool_registration.py` (TODO)

### Issues
Found a bug? See unexpected behavior?
- Check QA_REPORT_ULTRATHINK.md first
- File issue with reproduction steps

---

## MIGRATION CHECKLIST

Use this checklist to track your migration progress:

- [ ] Replace all `description=` with `request=` in AgentTask
- [ ] Replace `MCPClient()` with `create_mcp_client()`
- [ ] Run tests with deprecation warnings enabled
- [ ] Verify no warnings appear
- [ ] Verify all agents have tools available
- [ ] Update documentation/comments referencing old API
- [ ] Review custom tool registration (if applicable)
- [ ] Test integration with your application

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-24  
**Compliance**: Vértice Constitution v3.0 - P3 (Ceticismo Crítico)
