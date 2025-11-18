# 🎨 Visual Polish Plan - Qwen Dev CLI
**Inspired by**: Cursor, Claude Code, Gemini CLI

---

## 🎯 **Visual Polish Priorities**

### P0: Shell Rendering & UX (2h)
**Current State**: Basic Rich panels, functional but bland
**Goal**: Cursor-level polish, Claude-level clarity

#### 1. **Welcome Screen** ✨
**Inspiration**: Gemini CLI has the prettiest welcome
- [ ] Gradient border (cyan → blue → purple)
- [ ] ASCII art logo (small, tasteful)
- [ ] Session info card (model, tools count, context)
- [ ] Quick tips carousel

**Current**:
```
┌─ 🚀 AI-Powered Code Shell ─┐
│ QWEN-DEV-CLI v1.0           │
│ Tools: 25                   │
│ Working dir: /home/...      │
└─────────────────────────────┘
```

**Target**:
```
╔══════════════════════════════════════════════════════════╗
║  ⚡ QWEN-DEV-CLI  ·  Constitutional AI Code Assistant   ║
╟──────────────────────────────────────────────────────────╢
║  Model: Qwen/QwQ-32B-Preview (Local)                    ║
║  Tools: 25 registered  ·  Context: 0 files              ║
║  Session: abc123  ·  LEI: 0.00  ·  CPI: 1.00            ║
╟──────────────────────────────────────────────────────────╢
║  💡 Tip: Use /help for commands · /? for quick ref     ║
╚══════════════════════════════════════════════════════════╝
```

#### 2. **Prompt Style** 🎯
**Inspiration**: Cursor's clean, context-aware prompt
- [ ] Working directory with smart truncation
- [ ] Git branch indicator (when in repo)
- [ ] File count in context (if > 0)
- [ ] State indicator (● idle, ⏳ thinking, ⚡ executing)

**Current**:
```
> your prompt here
```

**Target**:
```
~/qwen-dev-cli [main] (3 files) ●
→ your prompt here
```

#### 3. **Response Rendering** 📝
**Inspiration**: Claude Code's markdown rendering + syntax highlighting
- [ ] Stream tokens smoothly (no flicker)
- [ ] Syntax highlighting for code blocks
- [ ] Diff rendering for file changes
- [ ] Collapsible sections for long outputs

**Improvements**:
```python
# Before
print(response)

# After
with console.pager():
    md = Markdown(response, code_theme="monokai")
    console.print(md)
```

#### 4. **Tool Call Visualization** 🔧
**Inspiration**: Cursor's tool call cards
- [ ] Tool name with icon
- [ ] Args in table format (if many)
- [ ] Progress spinner during execution
- [ ] Success/failure badge
- [ ] Execution time

**Current**:
```
Executing: read_file(path="test.py")
Result: <file content>
```

**Target**:
```
╭─ 📄 read_file ──────────────────── ⏱ 0.03s ─╮
│ path: qwen_dev_cli/shell.py                 │
│ size: 48 KB                                  │
├─────────────────────────────────────────────┤
│ ✅ Success                                   │
╰─────────────────────────────────────────────╯
```

#### 5. **Error Display** 🚨
**Inspiration**: Claude's error analysis + suggestions
- [ ] Error type badge (🔴 Critical, 🟡 Warning, 🔵 Info)
- [ ] Stack trace collapsible
- [ ] AI-generated suggestions panel
- [ ] Related errors (if any)

**Current**:
```
Error: FileNotFoundError: file.py
```

**Target**:
```
╭─ 🔴 FileNotFoundError ──────────────────────╮
│ File not found: file.py                     │
├─────────────────────────────────────────────┤
│ 💡 Suggestions:                             │
│  1. Did you mean: file.txt?                 │
│  2. Create it: touch file.py                │
│  3. Check path: pwd                         │
├─────────────────────────────────────────────┤
│ 📊 Context: 3 similar files in cwd          │
╰─────────────────────────────────────────────╯
```

---

### P1: Progress & Feedback (1h)

#### 1. **Loading States** ⏳
- [ ] Spinner for LLM calls ("Thinking...")
- [ ] Progress bar for multi-step operations
- [ ] Token streaming visualization
- [ ] ETA for long operations

#### 2. **Success Feedback** ✅
- [ ] Checkmark with message
- [ ] File modified counter
- [ ] Context updated indicator
- [ ] Metrics updated (LEI/CPI)

#### 3. **Warnings** ⚠️
- [ ] Danger detector output (destructive ops)
- [ ] Context limit warnings
- [ ] Performance degradation alerts

---

### P2: Color Scheme & Typography (1h)

#### Color Palette (inspired by Cursor Dark)
```python
THEME = {
    "primary": "#00D9FF",      # Cyan (prompts, highlights)
    "success": "#00FF88",      # Green (success states)
    "warning": "#FFB86C",      # Orange (warnings)
    "error": "#FF5555",        # Red (errors)
    "info": "#8BE9FD",         # Light blue (info)
    "muted": "#6272A4",        # Gray (secondary text)
    "code": "#F1FA8C",         # Yellow (code highlights)
    "border": "#44475A",       # Dark gray (borders)
}
```

#### Typography
- **Headers**: Bold + Primary color
- **Body**: Default with good spacing
- **Code**: Monospace with syntax highlighting
- **Emphasis**: Italic + Info color

---

### P3: Advanced Features (2h)

#### 1. **Interactive Tables**
- [ ] Tool results as tables (when structured)
- [ ] File listings as sortable tables
- [ ] Metrics dashboard table

#### 2. **Markdown Rendering**
- [ ] Full markdown support (bold, italic, lists)
- [ ] Code blocks with language detection
- [ ] Tables, quotes, horizontal rules

#### 3. **Context Awareness Display**
- [ ] Sidebar with current context
- [ ] File tree when relevant
- [ ] Git status integration

---

## 📊 **Implementation Checklist**

### Shell Improvements
- [ ] Update `_show_welcome()` with new design
- [ ] Create `_render_prompt()` for dynamic prompts
- [ ] Improve `_display_response()` with markdown
- [ ] Add `_render_tool_call()` for tool visualization
- [ ] Enhance `_display_error()` with suggestions

### New Components
- [ ] `ProgressBar` class for long operations
- [ ] `ErrorPanel` class for rich error display
- [ ] `ToolCallPanel` class for tool execution
- [ ] `MetricsDashboard` class for stats

### Configuration
- [ ] Add `~/.qwen-cli/theme.json` support
- [ ] Color customization
- [ ] Emoji disable flag
- [ ] Compact mode for CI/CD

---

## 🎨 **Code Changes Required**

### 1. shell.py modifications
```python
# Add to imports
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live

# New theme
THEME = {
    "primary": "cyan",
    "success": "green",
    "error": "red",
    # ...
}

# Update _show_welcome()
def _show_welcome(self):
    # New gradient design
    # ASCII art
    # Session info
    pass

# New _render_tool_call()
def _render_tool_call(self, tool_name, args, result):
    # Rich panel with icon
    # Args table
    # Success badge
    # Execution time
    pass
```

### 2. New module: ui/rendering.py
```python
"""Rich rendering utilities."""

class ToolCallPanel:
    """Render tool calls beautifully."""
    pass

class ErrorPanel:
    """Render errors with suggestions."""
    pass

class MetricsDashboard:
    """Render metrics table."""
    pass
```

---

## 🎯 **Success Criteria**

### Visual Quality
- [ ] Looks as good as Cursor CLI
- [ ] Information density matches Claude Code
- [ ] Color scheme is pleasing (dark mode)

### UX Quality
- [ ] Clear state indicators (idle/thinking/executing)
- [ ] Progress feedback for all operations > 1s
- [ ] Errors are helpful, not scary
- [ ] Success states are satisfying

### Performance
- [ ] No rendering lag
- [ ] Smooth token streaming
- [ ] Responsive to input

---

## 🚀 **Rollout Plan**

1. **Phase 1 (1h)**: Welcome + Prompt polish
2. **Phase 2 (1h)**: Tool call + Error display
3. **Phase 3 (1h)**: Color scheme + Typography
4. **Phase 4 (1h)**: Testing + Refinement

**Total**: 4h of focused visual polish 🎨
