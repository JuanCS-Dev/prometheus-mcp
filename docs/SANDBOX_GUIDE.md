# 🔒 Sandbox Execution Guide

## Overview

The qwen-dev-cli sandbox system provides **isolated Docker-based execution** for potentially dangerous commands. Execute untrusted code, test installations, and run risky operations without affecting your host system.

---

## Features

### 🛡️ Security
- **Filesystem isolation** - No host access by default
- **Resource limits** - CPU and memory constraints
- **Network isolation** - Optional network blocking
- **Timeout enforcement** - Automatic termination
- **Auto-cleanup** - Containers removed after execution

### ⚡ Performance
- Fast startup (<500ms for simple commands)
- Streaming output capture
- Parallel execution support
- Resource-efficient

### 🎯 Constitutional Compliance
- **LEI = 0.0** - No learning from sandbox execution
- **FPC = 100%** - Explicit permission required
- **HRI = 1.0** - Human controls all settings
- Safety First (Artigo IV, Constituição Vértice v3.0)

---

## Installation

### Prerequisites

```bash
# Install Docker
sudo apt-get install docker.io  # Ubuntu/Debian
# OR
brew install docker  # macOS

# Start Docker daemon
sudo systemctl start docker

# Add user to docker group (optional)
sudo usermod -aG docker $USER
```

### Python Package

```bash
pip install docker>=7.0.0
```

---

## Usage

### 1. Python API

#### Basic Execution

```python
from qwen_dev_cli.integration.sandbox import get_sandbox

sandbox = get_sandbox()

# Execute command
result = sandbox.execute(
    command="echo 'Hello Sandbox'",
    timeout=30
)

print(f"Exit code: {result.exit_code}")
print(f"Output: {result.stdout}")
print(f"Duration: {result.duration_ms}ms")
```

#### With Directory Mount

```python
from pathlib import Path

result = sandbox.execute(
    command="pytest tests/",
    cwd=Path("/path/to/project"),
    timeout=60,
    readonly=True  # Mount as read-only
)
```

#### With Environment Variables

```python
result = sandbox.execute(
    command="python script.py",
    env={
        'API_KEY': 'test-key',
        'DEBUG': 'true'
    }
)
```

#### Execute with Temporary Files

```python
files = {
    'script.py': 'print("Hello from script")',
    'data.txt': 'test data'
}

result = sandbox.execute_with_files(
    command="python /workspace/script.py",
    files=files,
    timeout=30
)
```

### 2. Slash Commands (Interactive Shell)

#### /sandbox Command

```bash
# Basic usage
/sandbox npm install

# With timeout
/sandbox --timeout 60 npm test

# Read-only mode
/sandbox --readonly cat config.json

# Aliases
/sb python test.py
/safe rm -rf /tmp/test
```

#### /review Command

```bash
# Basic review
/review

# With diffs
/review --diff

# With statistics
/review --stats

# Export to file
/review --export

# Aliases
/rv
/status
```

---

## Configuration

### Custom Image

```python
from qwen_dev_cli.integration.sandbox import SandboxExecutor

sandbox = SandboxExecutor(
    image="python:3.11-slim",
    auto_pull=True
)
```

### Resource Limits

```python
sandbox = SandboxExecutor(
    memory_limit="512m",     # 512 MB RAM
    cpu_quota=50000,         # 50% of one core
    network_disabled=True    # Block network access
)
```

### Timeout Settings

```python
# Per-execution timeout
result = sandbox.execute(
    command="long_running_task",
    timeout=300  # 5 minutes
)
```

---

## Examples

### Test Package Installation

```python
result = sandbox.execute(
    command="pip install requests && python -c 'import requests; print(requests.__version__)'",
    timeout=60
)
```

### Run Tests Safely

```python
result = sandbox.execute(
    command="pytest tests/ -v",
    cwd=Path("/path/to/project"),
    timeout=120,
    readonly=True
)
```

### Execute Untrusted Code

```python
untrusted_code = """
import os
print('Trying to access host...')
os.system('ls /host')  # Won't work - no /host directory
"""

result = sandbox.execute_with_files(
    command="python /workspace/untrusted.py",
    files={'untrusted.py': untrusted_code},
    timeout=10
)
```

### Check System Info

```python
result = sandbox.execute(
    command="python -c 'import sys, platform; print(sys.version); print(platform.system())'",
    timeout=5
)
```

---

## Security Considerations

### ✅ What's Protected

- **Host filesystem** - Isolated by default
- **Network** - Can be disabled
- **Resources** - CPU and memory limits enforced
- **Time** - Automatic timeout
- **Privileges** - Runs as non-root in container

### ⚠️ What to Watch For

- **Volume mounts** - Explicitly mounted directories ARE accessible
- **Docker socket** - Never mount Docker socket into sandbox
- **Secrets** - Don't pass secrets via environment variables
- **Resource exhaustion** - Set appropriate limits

### 🔒 Best Practices

1. **Always use timeouts** - Prevent infinite loops
2. **Use readonly mounts** - When you don't need to write
3. **Limit resources** - Set memory and CPU quotas
4. **Disable network** - If not needed
5. **Review logs** - Check stderr for warnings
6. **Clean up** - Use auto-cleanup (default)

---

## Troubleshooting

### Docker Not Available

```
Error: Docker sandbox not available
```

**Solution:**
- Install Docker
- Start Docker daemon: `sudo systemctl start docker`
- Check permissions: `docker ps`

### Permission Denied

```
Error: permission denied while trying to connect to Docker daemon
```

**Solution:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Image Not Found

```
Error: Image not found
```

**Solution:**
```python
sandbox = SandboxExecutor(auto_pull=True)  # Auto-pull images
```

### Timeout Errors

```
Error: Container timeout
```

**Solution:**
- Increase timeout
- Optimize command
- Check resource limits

### Read-only Filesystem

```
Error: Read-only file system
```

**Solution:**
```python
result = sandbox.execute(
    command="...",
    readonly=False  # Enable write access
)
```

---

## API Reference

### SandboxExecutor

```python
class SandboxExecutor:
    def __init__(
        self,
        image: str = "python:3.12-slim",
        memory_limit: str = "512m",
        cpu_quota: int = 50000,
        network_disabled: bool = False,
        auto_pull: bool = True
    )
    
    def is_available(self) -> bool
    
    def execute(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: int = 30,
        readonly: bool = True,
        env: Optional[Dict[str, str]] = None,
        working_dir: str = "/workspace"
    ) -> SandboxResult
    
    def execute_with_files(
        self,
        command: str,
        files: Dict[str, str],
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None
    ) -> SandboxResult
    
    def test_availability(self) -> Dict[str, Any]
    
    def cleanup_old_containers(self, older_than_hours: int = 24)
```

### SandboxResult

```python
@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    container_id: str
    success: bool
    
    @property
    def output(self) -> str  # Combined stdout + stderr
```

---

## Performance

### Benchmarks

```
Simple echo:        ~300ms
Python execution:   ~800ms
NPM install:        ~5s (varies)
Pytest suite:       ~2-10s (depends on tests)
```

### Optimization Tips

1. **Reuse SandboxExecutor** - Don't create new instances
2. **Use appropriate timeouts** - Not too short, not too long
3. **Minimize file mounts** - Only mount what's needed
4. **Cache Docker images** - Pre-pull images
5. **Parallel execution** - Multiple sandboxes can run simultaneously

---

## Integration with qwen-dev-cli

The sandbox system integrates seamlessly with the CLI:

```python
# In shell.py
from qwen_dev_cli.integration.sandbox import get_sandbox
from qwen_dev_cli.commands.sandbox import handle_sandbox

# Use in tool execution
sandbox = get_sandbox()
if risky_operation:
    result = sandbox.execute(command, timeout=60)
```

---

## Changelog

### v0.5.0 (Day 5)
- ✅ Initial sandbox implementation
- ✅ Docker integration
- ✅ /sandbox and /review commands
- ✅ Resource limits
- ✅ Network isolation
- ✅ 48/48 tests passing

---

## License

Part of qwen-dev-cli project.
Constituição Vértice v3.0 compliant.

---

## Support

For issues or questions:
- GitHub Issues: [qwen-dev-cli/issues](https://github.com/JuanCS-Dev/qwen-dev-cli/issues)
- Documentation: `/docs`
- Tests: `/tests/integration/test_sandbox.py`
