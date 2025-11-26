# E2E Test Report - Juan-Dev-Code

**Generated:** 2025-11-26T14:15:50.868360

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 8 |
| Passed | 8 |
| Failed | 0 |
| Errors | 0 |
| Pass Rate | 100.0% |
| Duration | 0.03s |

## Test Results

### ✅ write_and_read_file

- **Status:** passed
- **Duration:** 0.02s

**Details:**
```json
{
  "tools": [
    "WriteFileTool",
    "ReadFileTool"
  ],
  "file_size": 173,
  "lines": 9
}
```

---

### ✅ edit_file

- **Status:** passed
- **Duration:** 0.00s

**Details:**
```json
{
  "tools": [
    "WriteFileTool",
    "EditFileTool",
    "ReadFileTool"
  ],
  "changes": 1
}
```

---

### ✅ search_in_files

- **Status:** passed
- **Duration:** 0.00s

**Details:**
```json
{
  "tools": [
    "SearchFilesTool"
  ],
  "matches_found": 8
}
```

---

### ✅ search_for_bugs

- **Status:** passed
- **Duration:** 0.00s

**Details:**
```json
{
  "tools": [
    "SearchFilesTool"
  ],
  "bugs_found": 4
}
```

---

### ✅ create_python_module

- **Status:** passed
- **Duration:** 0.00s

**Details:**
```json
{
  "project_type": "python_module",
  "files_created": 7
}
```

---

### ✅ git_status

- **Status:** passed
- **Duration:** 0.01s

**Details:**
```json
{
  "tools": [
    "GitStatusTool"
  ],
  "status_data": "{'branch': 'main', 'modified': [], 'untracked': [], 'staged': ['tests/e2e_textual/E2E_REPORT.json', 'tests/e2e_textual/E2E_REPORT.md', 'tests/e2e_textual/__init__.py', 'tests/e2e_textual/conftest.py',"
}
```

---

### ✅ plan_mode_cycle

- **Status:** passed
- **Duration:** 0.00s

**Details:**
```json
{
  "tools": [
    "EnterPlanModeTool",
    "ExitPlanModeTool"
  ],
  "plan_file": "/tmp/jdev_e2e_j_vvfpd2/.jdev/plans/e2e_plan.md"
}
```

---

### ✅ search_and_fix_workflow

- **Status:** passed
- **Duration:** 0.00s

**Details:**
```json
{
  "workflow": "search_fix",
  "tools": 3,
  "fixed": true,
  "issues_found": 3
}
```

---

