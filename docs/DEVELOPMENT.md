# DEVELOPMENT GUIDE

**For Contributors and Advanced Users**

---

## Quick Setup

### 1. Virtual Environment (Recommended)

```bash
# Create venv
python3 -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Verify
which python  # Should point to .venv/bin/python
```

### 2. Install Dependencies

```bash
# Production + Development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Or install in editable mode
pip install -e .
```

### 3. Environment Configuration

```bash
# Copy example config
cp .env.example .env

# Edit with your keys
nano .env  # or vim, code, etc.
```

Required variables:
```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash  # Optional, defaults to this
```

### 4. Optional: Environment Optimization

```bash
# Copy environment optimization file
cp .envrc.example .envrc

# If using direnv:
direnv allow

# Or source manually:
source .envrc
```

This configures:
- gRPC warning suppression
- Python optimization flags
- Faster startup

---

## Running the CLI

### Standard Shell

```bash
# Direct execution
./qwen

# Or via Python module
python -m qwen_dev_cli.shell_main
```

### Maestro UI (Advanced)

```bash
# Cyberpunk TUI with full features
./maestro

# Or
python -m qwen_dev_cli.tui.maestro_layout
```

---

## Testing

### Run All Tests

```bash
# Full test suite
pytest tests/

# With coverage
pytest tests/ --cov=qwen_dev_cli --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Specific test file
pytest tests/unit/test_registry_setup.py -v
```

### Check for Deprecation Warnings

```bash
# Enable all warnings
pytest -W default::DeprecationWarning tests/
```

**Expected**: No warnings about `AgentTask.description` field

---

## Code Quality

### Type Checking

```bash
# Run mypy
mypy qwen_dev_cli/

# Strict mode
mypy --strict qwen_dev_cli/
```

### Linting

```bash
# Run flake8
flake8 qwen_dev_cli/

# Run pylint
pylint qwen_dev_cli/
```

### Security Scan

```bash
# Run bandit security scanner
bandit -r qwen_dev_cli/

# With config
bandit -r qwen_dev_cli/ -c .bandit
```

---

## Common Development Tasks

### Adding a New Agent

1. Create agent file: `qwen_dev_cli/agents/my_agent.py`
2. Inherit from `BaseAgent`
3. Implement required methods
4. Register in `qwen_dev_cli/agents/__init__.py`
5. Write tests in `tests/unit/test_my_agent.py`

Example:
```python
from qwen_dev_cli.agents.base import BaseAgent, AgentTask, AgentResponse

class MyAgent(BaseAgent):
    async def _think(self, task: AgentTask) -> str:
        # Reasoning logic
        pass
    
    async def _act(self, task: AgentTask, reasoning: str) -> AgentResponse:
        # Execution logic
        pass
```

### Adding a New Tool

1. Create tool file: `qwen_dev_cli/tools/my_tool.py`
2. Inherit from `BaseTool`
3. Define parameters with Pydantic
4. Implement `_execute()` method
5. Register in tool registry

Example:
```python
from qwen_dev_cli.tools.base import BaseTool, ToolResult
from pydantic import BaseModel, Field

class MyToolParams(BaseModel):
    param1: str = Field(description="Parameter description")

class MyTool(BaseTool):
    name = "my_tool"
    description = "Tool description"
    parameters_schema = MyToolParams
    
    async def _execute(self, **kwargs) -> ToolResult:
        # Tool logic
        return ToolResult(success=True, data={"result": "output"})
```

### Updating Tool Registry

When adding/modifying default tools, update:
- `qwen_dev_cli/tools/registry_setup.py` - Factory functions
- `tests/unit/test_registry_setup.py` - Comprehensive tests
- `docs/MIGRATION_v2.0.md` - If breaking change

---

## Troubleshooting

### ImportError: No module named 'qwen_dev_cli'

**Solution**: Install in editable mode
```bash
pip install -e .
```

### Tool not found errors

**Solution**: Use factory function for tool setup
```python
from qwen_dev_cli.core.mcp import create_mcp_client
mcp = create_mcp_client()  # Auto-registers tools
```

### gRPC ALTS warnings

**Solution**: Set environment variables
```bash
export GRPC_ENABLE_FORK_SUPPORT=1
export GRPC_POLL_STRATEGY=poll
```

Or use `.envrc` file (see setup above)

### Venv not activating

**Symptoms**: `which python` points to system Python

**Solution**:
```bash
# Deactivate any existing venv
deactivate

# Remove old venv
rm -rf .venv

# Recreate
python3 -m venv .venv
source .venv/bin/activate
```

---

## Project Structure

```
qwen-dev-cli/
├── qwen_dev_cli/          # Main package
│   ├── agents/            # Agent implementations
│   ├── core/              # Core systems (LLM, MCP, context)
│   ├── tools/             # Tool implementations
│   ├── tui/               # Terminal UI components
│   └── ui/                # Web UI (Gradio)
│
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── test_agents.py     # Agent tests
│
├── docs/                  # Documentation
│   ├── MIGRATION_v2.0.md  # Migration guide
│   ├── DEVELOPMENT.md     # This file
│   └── architecture/      # Architecture docs
│
├── .env.example           # Environment template
├── .envrc.example         # Optional optimization
├── requirements.txt       # Dependencies
└── README.md              # Main documentation
```

---

## Best Practices

### 1. Constitutional Compliance

Follow **Vértice Constitution v3.0** principles:
- **P1**: Zero placeholders, complete implementation
- **P2**: Validate before use, fail fast
- **P3**: Challenge assumptions, be skeptical
- **P4**: Traceable sources, clear provenance
- **P5**: Systemic awareness, document impacts
- **P6**: Token efficiency, max 2 iterations

### 2. Testing Standards

- **Coverage**: ≥90% for new code
- **Edge cases**: Test failure modes
- **Integration**: Test with real LLM (mocked)
- **Security**: No hardcoded credentials

### 3. Code Style

- **Type hints**: All functions must have type annotations
- **Docstrings**: Google style, include examples
- **Error handling**: Explicit, with clear messages
- **Logging**: Use appropriate levels (DEBUG, INFO, WARNING, ERROR)

### 4. Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, commit frequently
git add .
git commit -m "feat: Add new feature"

# Push and create PR
git push origin feature/my-feature
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring

---

## Resources

- **Architecture**: `docs/ARCHITECTURE.md`
- **Migration Guide**: `docs/MIGRATION_v2.0.md`
- **QA Report**: `QA_REPORT_ULTRATHINK.md`
- **Constitution**: `docs/CONSTITUIÇÃO_VÉRTICE_v3.0.md`

---

## Getting Help

1. **Check documentation**: `docs/` folder
2. **Read QA report**: Known issues and solutions
3. **Search issues**: GitHub issues page
4. **Create issue**: Include reproduction steps

---

**Last Updated**: 2025-11-24  
**Compliance**: Vértice Constitution v3.0 - P4 (Documentation)
