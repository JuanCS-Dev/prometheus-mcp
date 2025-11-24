# STREAMING FIX PACKAGE - Required Files

**Purpose**: Complete context for implementing streaming fixes in MAESTRO UI  
**Target Audience**: Developer implementing the fix  
**Date**: 2025-11-24

---

## 📋 MANDATORY FILES (Must Include)

### 1. Main Report
```
STREAMING_AUDIT_REPORT.md
```
**Why**: Complete problem analysis, architecture, and solution

---

### 2. Current Working Implementation (Reference)
```
qwen_dev_cli/agents/executor_nextgen.py
```
**Why**: ✅ This agent ALREADY HAS correct `execute_streaming()` implementation
**Use as**: Template/reference for implementing streaming in other agents
**Key sections**:
- Lines 562-650: `execute_streaming()` method (COMPLETE EXAMPLE)
- Lines 730-780: `_stream_command_generation()` helper
- Shows proper yielding of all update types

---

### 3. Orchestrator (Streaming Consumer)
```
maestro_v10_integrated.py
```
**Why**: Shows how streaming is consumed and routed to UI
**Key sections**:
- Lines 211-235: `execute_streaming()` method (routes to agents)
- Lines 1293-1355: Main loop that consumes stream and updates UI
- Lines 1299-1328: Update type handling (thinking, command, status, result)
**Shows**: What the UI expects to receive from agents

---

### 4. UI Component (Display Layer)
```
qwen_dev_cli/tui/components/maestro_shell_ui.py
```
**Why**: Shows how UI receives and displays streaming updates
**Key sections**:
- Lines 305-336: `update_agent_stream()` method
- Lines 276-288: `start()` method (30 FPS Live display)
- Lines 449-462: `add_agent()` method
**Shows**: UI is READY to receive streams, just needs agents to send them

---

### 5. Agents Needing Fixes (P0 - CRITICAL)

#### PlannerAgent
```
qwen_dev_cli/agents/planner.py
```
**Why**: ❌ Missing `execute_streaming()` - needs to be added
**Current state**: Only has `execute()` method (lines 500-600)
**What to add**: Streaming version following NextGenExecutor pattern
**Priority**: 🔴 P0 (CRITICAL - panel is empty in screenshot)

#### ExplorerAgent
```
qwen_dev_cli/agents/explorer.py
```
**Why**: ❌ Missing `execute_streaming()` - needs to be added
**Current state**: Only has `execute()` method
**What to add**: Streaming version
**Priority**: 🔴 P0 (CRITICAL - used frequently)

---

### 6. LLM Client (Streaming Source)
```
qwen_dev_cli/core/llm.py
```
**Why**: Needs `generate_stream()` method added
**Current state**: Only has `generate()` (non-streaming)
**What to add**: Async generator that yields tokens
**Key sections**:
- Lines 50-150: LLMClient class initialization
- Lines 200-300: `generate()` method (adapt this for streaming)
**Priority**: 🔴 P0 (REQUIRED for Phase 1 - foundation)

---

### 7. MCP Client (File Tracking)
```
qwen_dev_cli/core/mcp.py
```
**Why**: Needs automatic file operation tracking
**Current state**: Basic tool execution
**What to add**: Track file ops automatically in `call_tool()`
**Key sections**:
- Lines 87-116: `call_tool()` method
**Priority**: 🔴 P0 (for FILE OPERATIONS panel)

---

### 8. Base Agent Class
```
qwen_dev_cli/agents/base.py
```
**Why**: Understand agent interface and contracts
**Key sections**:
- Lines 56-91: AgentTask model
- Lines 93-108: AgentResponse model
- Lines 110-400: BaseAgent abstract class
**Shows**: Base class that all agents inherit from

---

### 9. File Operation Tracker
```
qwen_dev_cli/core/file_tracker.py
```
**Why**: Understand how file operations should be tracked
**Key sections**:
- FileOperationTracker class
- `track_operation()` method
- Callback mechanism for UI updates

---

## 📸 SUPPORTING FILES (Recommended)

### Screenshot Evidence
```
[The screenshot you provided showing empty PLANNER panel]
```
**Why**: Visual proof of the problem
**Include as**: PNG/JPG attachment or embedded in documentation

---

### Additional Agent Examples (P1 - High Priority)

#### ReviewerAgent
```
qwen_dev_cli/agents/reviewer.py
```
**Why**: ❌ Needs streaming (P1 priority)
**When**: Implement after P0 agents working

#### RefactorerAgent
```
qwen_dev_cli/agents/refactorer.py
```
**Why**: ❌ Needs streaming (P1 priority)
**When**: Implement after P0 agents working

---

## 📚 CONTEXT FILES (Optional but Helpful)

### Architecture Documentation
```
docs/ARCHITECTURE.md
```
**Why**: Overall system architecture understanding

### Migration Guide
```
docs/MIGRATION_v2.0.md
```
**Why**: Shows recent changes to codebase

### QA Report
```
QA_REPORT_ULTRATHINK.md
```
**Why**: Shows other known issues (but not directly related to streaming)

---

## 🎯 MINIMAL PACKAGE (If size is a concern)

If you need to send a smaller package, these are **ABSOLUTELY ESSENTIAL**:

1. ✅ `STREAMING_AUDIT_REPORT.md` (main report)
2. ✅ `qwen_dev_cli/agents/executor_nextgen.py` (reference implementation)
3. ✅ `maestro_v10_integrated.py` (orchestrator)
4. ✅ `qwen_dev_cli/agents/planner.py` (needs fixing)
5. ✅ `qwen_dev_cli/core/llm.py` (needs generate_stream())
6. ✅ Screenshot (visual proof)

**Total**: ~6 files + 1 image

---

## 📦 HOW TO PACKAGE

### Option 1: Create Archive
```bash
# Navigate to project root
cd /media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli

# Create streaming-fix package
tar -czf streaming-fix-package.tar.gz \
  STREAMING_AUDIT_REPORT.md \
  STREAMING_FIX_PACKAGE.md \
  maestro_v10_integrated.py \
  qwen_dev_cli/agents/executor_nextgen.py \
  qwen_dev_cli/agents/planner.py \
  qwen_dev_cli/agents/explorer.py \
  qwen_dev_cli/core/llm.py \
  qwen_dev_cli/core/mcp.py \
  qwen_dev_cli/core/file_tracker.py \
  qwen_dev_cli/tui/components/maestro_shell_ui.py \
  qwen_dev_cli/agents/base.py \
  qwen_dev_cli/agents/reviewer.py \
  qwen_dev_cli/agents/refactorer.py

echo "Package created: streaming-fix-package.tar.gz"
```

### Option 2: GitHub Issue/PR
Create a GitHub issue with:
- Link to STREAMING_AUDIT_REPORT.md
- Screenshot embedded
- References to specific line numbers in files
- Use GitHub's file browser for context

### Option 3: Documentation Site
If using a wiki/documentation platform:
- Upload STREAMING_AUDIT_REPORT.md as main page
- Link to relevant files in repository
- Embed screenshot
- Create navigation structure

---

## 📝 CHECKLIST FOR FIXER

Before starting implementation, fixer should have:

- [ ] Read STREAMING_AUDIT_REPORT.md completely
- [ ] Examined executor_nextgen.py (reference implementation)
- [ ] Understood how orchestrator consumes streams
- [ ] Reviewed UI component update methods
- [ ] Located planner.py and explorer.py to modify
- [ ] Understood LLMClient needs generate_stream() method
- [ ] Seen screenshot showing the problem
- [ ] Read through implementation plan (Phase 1-4)
- [ ] Ready to start with Phase 1 (LLMClient streaming)

---

## 🎯 IMPLEMENTATION ORDER

**Fixer should implement in this exact order:**

### Phase 1: Foundation
1. Add `LLMClient.generate_stream()` in `qwen_dev_cli/core/llm.py`
2. Test with existing NextGenExecutor
3. Add file tracking in `qwen_dev_cli/core/mcp.py`

### Phase 2: Critical Agents (P0)
4. Add `PlannerAgent.execute_streaming()` in `qwen_dev_cli/agents/planner.py`
5. Add `ExplorerAgent.execute_streaming()` in `qwen_dev_cli/agents/explorer.py`
6. Test in MAESTRO UI - panels should show streaming

### Phase 3: High-Priority Agents (P1)
7. Add streaming to ReviewerAgent
8. Add streaming to RefactorerAgent

### Phase 4: Remaining Agents (P2, P3)
9. Add streaming to remaining agents as needed

---

## 🔗 RELATED ISSUES

If fixer encounters problems:

### Issue: LLM API doesn't support streaming
**Solution**: Implement fallback (fake streaming by splitting response)
**See**: STREAMING_AUDIT_REPORT.md, section "LLM Streaming Helper"

### Issue: Agent has complex multi-step workflow
**Solution**: Stream each phase separately with status updates
**See**: STREAMING_AUDIT_REPORT.md, section "Known Issues & Workarounds"

### Issue: Tests failing
**Solution**: Follow testing strategy in report
**See**: STREAMING_AUDIT_REPORT.md, section "Testing Strategy"

---

## 📞 CONTACT INFO

If fixer has questions, they should reference:
- Line numbers in specific files
- Specific section in STREAMING_AUDIT_REPORT.md
- Phase number they're implementing

**Example good question**:
> "In Phase 2, implementing PlannerAgent.execute_streaming(), the template 
> shows `self.llm.generate_stream()` but line 150 of llm.py doesn't have 
> this method yet. Should I implement Phase 1 first?"

**Answer**: Yes, Phase 1 must be complete before Phase 2.

---

## ✅ SUCCESS CRITERIA

Fixer will know they succeeded when:

1. ✅ Launch `./maestro`
2. ✅ Type: "Create a plan for implementing user auth"
3. ✅ PLANNER panel shows:
   - "📋 Loading project context..." (status)
   - "🎯 Generating plan..." (status)
   - Token-by-token LLM output streaming in real-time
   - Smooth 30 FPS updates
4. ✅ Type: "Read the main.py file"
5. ✅ FILE OPERATIONS panel shows:
   - File path
   - Operation type (read)
   - Timestamp
   - Success status

**Before**: Empty panels (as in screenshot)  
**After**: All panels show live streaming content

---

**Package Version**: 1.0  
**Last Updated**: 2025-11-24  
**Status**: Ready for distribution

---

## 📋 QUICK REFERENCE: File Locations

```
Project Root: /media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/

Reports:
  └─ STREAMING_AUDIT_REPORT.md          [Main report]
  └─ STREAMING_FIX_PACKAGE.md           [This file]

Core System:
  └─ maestro_v10_integrated.py          [Orchestrator - streaming consumer]
  └─ qwen_dev_cli/
      ├─ core/
      │   ├─ llm.py                     [NEEDS: generate_stream()]
      │   ├─ mcp.py                     [NEEDS: file tracking]
      │   └─ file_tracker.py            [File operation tracking]
      │
      ├─ agents/
      │   ├─ base.py                    [Base class - interface]
      │   ├─ executor_nextgen.py        [✅ REFERENCE - has streaming]
      │   ├─ planner.py                 [❌ NEEDS: execute_streaming()]
      │   ├─ explorer.py                [❌ NEEDS: execute_streaming()]
      │   ├─ reviewer.py                [❌ P1: needs streaming]
      │   └─ refactorer.py              [❌ P1: needs streaming]
      │
      └─ tui/
          └─ components/
              └─ maestro_shell_ui.py    [✅ UI ready to receive streams]
```

---

**Ready to ship!** 🚀
