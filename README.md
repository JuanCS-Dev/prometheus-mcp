# 🚀 QWEN-DEV-CLI

**Constitutional AI-Powered Development Assistant with MCP Integration**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)
[![Paridade](https://img.shields.io/badge/Copilot_Parity-88%25-brightgreen.svg)](MASTER_PLAN.md)

> A production-grade development assistant featuring Constitutional AI, multi-LLM support (cloud + local), interactive REPL, and Model Context Protocol integration. Built for the MCP 1st Birthday Hackathon. 🎉

📋 **[Master Plan & Roadmap](MASTER_PLAN.md)** | 📁 **[Project Structure](PROJECT_STRUCTURE.md)**

📁 **[View Complete Project Structure](PROJECT_STRUCTURE.md)**

---

## ✨ Key Features

### 🧠 **Multi-LLM Support**
- **Cloud**: HuggingFace API, Nebius AI (Qwen3-235B, QwQ-32B)
- **Local**: Ollama integration for complete privacy
- **Fallback**: Automatic provider switching with circuit breaker

### 🛡️ **Constitutional AI**
- Defense layer against prompt injection (25+ patterns)
- LEI (Legal-Ethical Index), HRI (Human Rights Index), CPI (Constitutional Protection Index)
- Safety validation for dangerous operations
- Rate limiting & resource protection

### 🎨 **Interactive REPL** (NEW: Integration Sprint Week 1)
- **Command Palette** (Ctrl+K) - Fuzzy search 9+ commands
- **Token Tracking** - Real-time usage + cost estimation
- **Inline Preview** - Review diffs before applying changes
- **Workflow Visualizer** - Track operation progress
- **Animations** - Smooth state transitions (ease-out)
- **Dashboard** - Live system metrics & operation history
- Reactive TUI with real-time streaming
- Multi-line input with syntax highlighting
- Session persistence & command history
- Smart tab completion & suggestions

### 🔧 **MCP Integration** 
- 27+ production tools (filesystem, git, search)
- Dynamic tool discovery & lazy loading
- Context-aware assistance with smart file selection
- Workflow orchestration for complex tasks

### ⚡ **Performance**
- TTFT < 2s (Time to First Token)
- Async streaming with backpressure control
- Token budget management (1M context window)
- Zero bare exceptions (production-grade error handling)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         QWEN-DEV-CLI                        │
├─────────────────────────────────────────────┤
│                                             │
│  CLI (Typer)         Web UI (Gradio 6)      │
│  ├─ explain          ├─ Chat interface     │
│  ├─ generate         ├─ Streaming          │
│  └─ serve            └─ Mobile responsive  │
│                                             │
├─────────────────────────────────────────────┤
│         Core Business Logic                 │
│  ├─ LLM Client (HF API + Ollama)           │
│  ├─ MCP Manager (Filesystem)               │
│  └─ Context Builder                        │
├─────────────────────────────────────────────┤
│         External Services                   │
│  ├─ HuggingFace Inference API              │
│  ├─ Ollama (Optional)                      │
│  └─ MCP Filesystem Server                  │
└─────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/JuanCS-Dev/qwen-dev-cli.git
cd qwen-dev-cli

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys (HuggingFace, Nebius)
```

### Usage Modes

#### 🔥 **Interactive REPL** (Recommended)

```bash
# Start interactive shell
python -m qwen_dev_cli.shell

# Available commands:
# /help        - Show all commands
# /context     - Manage context files
# /model       - Switch LLM provider
# /metrics     - View constitutional metrics
# /clear       - Clear conversation
# Ctrl+C       - Exit
```

#### 🎯 **One-Shot Mode**

```bash
# Explain code
qwen-dev explain main.py

# Generate code
qwen-dev generate "Create a FastAPI endpoint"

# Execute workflow
qwen-dev workflow "setup project with FastAPI + Docker"
```

#### 🌐 **Web UI Mode**

```bash
# Start Gradio interface
python -m qwen_dev_cli.ui

# Open browser at http://localhost:7860
```

---

## 🛠️ Technology Stack

- **LLM Providers**: HuggingFace Inference API, Nebius AI, Ollama
- **MCP**: Model Context Protocol 1.0 (27+ tools)
- **UI**: Prompt Toolkit (REPL), Gradio 6.0+ (Web), Rich (CLI)
- **Backend**: Python 3.11+, Asyncio, Pydantic
- **Testing**: Pytest (313 tests, 88% passing)
- **Architecture**: Constitutional AI + Defense-in-Depth

---

## 📦 Project Structure

```
qwen-dev-cli/
├── qwen_dev_cli/           # Core application
│   ├── core/               # Business logic layer
│   │   ├── llm.py          # LLM client abstraction
│   │   ├── mcp.py          # MCP server integration
│   │   ├── context.py      # Context management
│   │   └── config.py       # Configuration handling
│   ├── integration/        # External integrations
│   │   ├── parser.py       # Shell command parsing
│   │   └── workflow.py     # Workflow orchestration
│   ├── tools/              # MCP tools implementation
│   │   ├── shell.py        # Shell execution tools
│   │   └── terminal.py     # Terminal utilities
│   ├── prompts/            # System prompts
│   ├── cli.py              # CLI interface (Typer)
│   ├── shell.py            # Interactive shell
│   └── ui.py               # Web interface (Gradio)
│
├── tests/                  # Comprehensive test suite
│   ├── test_*.py           # Unit & integration tests
│   ├── validate_*.py       # Validation scripts
│   └── __init__.py         # Test package
│
├── docs/                   # Documentation hub
│   ├── planning/           # Project planning docs
│   │   ├── MASTER_PLAN.md  # Master roadmap
│   │   └── DAILY_LOG.md    # Development journal
│   ├── reports/            # Status & audit reports
│   │   ├── VALIDATION_REPORT.md
│   │   ├── AUDIT_REPORT.md
│   │   └── *_SUMMARY.md    # Various summaries
│   └── research/           # Technical research
│       └── PHASE_*.md      # Phase-specific research
│
├── examples/               # Usage examples
│   └── example_parser_usage.py
│
├── benchmarks/             # Performance benchmarks
│   └── benchmark_llm.py
│
├── scripts/                # Utility scripts
│
├── pyproject.toml          # Project metadata (Poetry)
├── requirements.txt        # Python dependencies
└── pytest.ini              # Test configuration
```

---

## 🎯 MCP Integration (Hackathon Focus)

This project demonstrates advanced Model Context Protocol usage:

### **27+ Production Tools**
- **Filesystem**: `read_file`, `write_file`, `list_directory`, `search_files`
- **Git**: `git_status`, `git_diff`, `git_log`, `git_commit`
- **Search**: `grep`, `glob`, `ripgrep` with advanced patterns
- **Shell**: Safe command execution with validation
- **Context**: Smart file selection & token budget management

### **Constitutional MCP Server**
- ✅ **Defense Layer** - Prompt injection detection (25+ patterns)
- ✅ **Metrics System** - LEI, HRI, CPI compliance tracking
- ✅ **Safety Validation** - Risk assessment for dangerous operations
- ✅ **Rate Limiting** - Circuit breaker with exponential backoff
- ✅ **Audit Trail** - Complete logging of all tool invocations

### **Innovation Highlights**
1. **Hybrid Registry** - Dynamic discovery + lazy loading (Cursor + Claude patterns)
2. **Context Optimizer** - Smart file selection within token budget
3. **Workflow Engine** - Multi-step task orchestration with rollback
4. **Constitutional AI** - First MCP server with built-in ethical framework

---

## 🚀 Deployment Options

### **Local Development**
```bash
python -m qwen_dev_cli.shell  # Interactive REPL
python -m qwen_dev_cli.ui     # Web UI (localhost:7860)
```

### **HuggingFace Spaces** (Coming Soon)
🔗 **[Live Demo](https://huggingface.co/spaces/JuanCS-Dev/qwen-dev-cli)** 

### **Docker** (Planned)
```bash
docker run -e HF_TOKEN=xxx -e NEBIUS_API_KEY=xxx qwen-dev-cli
```

---

## 📊 Metrics & Performance

### **Speed**
- ⚡ TTFT: < 2s (Time to First Token)
- 🚀 Throughput: 12-18 tokens/sec (streaming)
- 🔥 Cold Start: ~5s (HF API) / ~45s (Ollama)

### **Quality**
- ✅ Test Coverage: 88% (273/313 tests passing)
- 🛡️ Constitutional Compliance: 100% (all defense tests passing)
- 🎯 Copilot Parity: 88% (validated via diagnostic)
- 📦 Zero Bare Exceptions: Production-grade error handling

### **Scale**
- 📊 Context Window: 1M tokens (Nebius QwQ-32B)
- 🔧 Tools Available: 27+ production-ready
- 📝 Codebase: 13,838 LOC across 63 files
- 🔌 LLM Providers: 3 (HuggingFace, Nebius, Ollama)

---

## 📊 Development Status

**Current:** 88% Copilot Parity | **Target:** 90%+ | **Deadline:** 2025-11-30

```
Progress: [██████████████████░░] 88% Complete

✅ Phase 1: LLM Backend (100%)           - Multi-provider, streaming, fallback
✅ Phase 2: Shell Integration (100%)     - 27+ tools, safety validation  
✅ Phase 3: Constitutional AI (100%)     - Defense layer, metrics system
✅ Phase 4: Interactive REPL (75%)       - Reactive TUI, streaming output
🔄 Phase 5: Production Polish (40%)      - Tests, docs, visual refinement
```

**Recent Achievements:**
- ✅ Interactive REPL with prompt_toolkit
- ✅ Constitutional metrics (LEI, HRI, CPI)
- ✅ Multi-LLM support (3 providers)
- ✅ 27+ MCP tools with dynamic registry
- ✅ Defense layer (prompt injection detection)
- ✅ Zero bare exceptions (production-grade)

**Next Steps (12 days):**
- 🎯 Fix remaining 40 test failures
- 🎨 Visual polish (colors, formatting)
- 📚 Complete documentation
- 🚀 HuggingFace Spaces deployment

See **[MASTER_PLAN.md](MASTER_PLAN.md)** for complete roadmap.

## 🤝 Contributing

This is a hackathon project for the **MCP 1st Birthday Hackathon** (Anthropic + Gradio).

Contributions welcome after the hackathon concludes!

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run specific test suite
pytest tests/test_parser.py -v

# Run benchmarks
python benchmarks/benchmark_llm.py
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Anthropic** - For the amazing Claude and MCP
- **Gradio Team** - For the excellent UI framework
- **HuggingFace** - For Inference API and Spaces hosting
- **Ollama** - For local LLM capabilities

---

## 📞 Contact

**Author**: Juan Carlos  
**GitHub**: [@JuanCS-Dev](https://github.com/JuanCS-Dev)  
**Project**: [qwen-dev-cli](https://github.com/JuanCS-Dev/qwen-dev-cli)

---

**Built for MCP 1st Birthday Hackathon 🎉**

*Soli Deo Gloria* 🙏
