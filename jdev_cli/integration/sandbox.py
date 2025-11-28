"""
Docker-based sandbox executor for safe command execution.

This module provides isolated execution environment for potentially dangerous commands.
Complies with Constituição Vértice v3.0 - Safety First (Artigo IV).
"""

import docker
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result from sandbox execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    container_id: str
    success: bool

    @property
    def output(self) -> str:
        """Combined output."""
        return self.stdout + self.stderr


class SandboxExecutor:
    """
    Execute commands in isolated Docker containers.
    
    Security Features:
    - Isolated filesystem (no host access by default)
    - Resource limits (CPU, memory)
    - Network isolation (optional)
    - Timeout enforcement
    - Auto-cleanup
    
    Constitutional Compliance:
    - LEI = 0.0 (no learning from sandbox execution)
    - FPC = 100% (explicit permission required)
    - HRI = 1.0 (human controls sandbox settings)
    """

    def __init__(
        self,
        image: str = "python:3.12-slim",
        memory_limit: str = "512m",
        cpu_quota: int = 50000,  # 50% of one core
        network_disabled: bool = False,
        auto_pull: bool = True
    ):
        """
        Initialize sandbox executor.
        
        Args:
            image: Docker image to use
            memory_limit: Memory limit (e.g., "512m", "1g")
            cpu_quota: CPU quota in microseconds (100000 = 1 core)
            network_disabled: Disable network access
            auto_pull: Auto-pull image if not available
        """
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.network_disabled = network_disabled
        self.auto_pull = auto_pull

        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")

            if auto_pull:
                self._ensure_image()
        except docker.errors.DockerException as e:
            logger.warning(f"Docker not available: {e}")
            self.client = None

    def _ensure_image(self):
        """Ensure Docker image is available."""
        if not self.client:
            return

        try:
            self.client.images.get(self.image)
            logger.debug(f"Image {self.image} already available")
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling Docker image: {self.image}")
            try:
                self.client.images.pull(self.image)
                logger.info(f"Successfully pulled {self.image}")
            except docker.errors.APIError as e:
                logger.error(f"Failed to pull image: {e}")
                raise RuntimeError(f"Failed to pull Docker image {self.image}: {e}")

    def is_available(self) -> bool:
        """Check if sandbox is available."""
        return self.client is not None

    def execute(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: int = 30,
        readonly: bool = True,
        env: Optional[Dict[str, str]] = None,
        working_dir: str = "/workspace"
    ) -> SandboxResult:
        """
        Execute command in sandbox.
        
        Args:
            command: Command to execute
            cwd: Host directory to mount (if any)
            timeout: Timeout in seconds
            readonly: Mount directory as readonly
            env: Environment variables
            working_dir: Working directory inside container
        
        Returns:
            SandboxResult with execution details
        
        Raises:
            RuntimeError: If Docker is not available
            docker.errors.ContainerError: If execution fails
            docker.errors.APIError: If Docker API fails
        """
        if not self.is_available():
            raise RuntimeError(
                "Docker sandbox not available. Install Docker and ensure daemon is running."
            )

        start_time = datetime.now()
        container = None

        try:
            # Prepare volume mounts
            volumes = {}
            if cwd:
                mode = "ro" if readonly else "rw"
                volumes[str(cwd.absolute())] = {
                    'bind': working_dir,
                    'mode': mode
                }

            # Prepare environment
            environment = env or {}

            # Container configuration
            container_config = {
                'image': self.image,
                'command': ['sh', '-c', command],
                'working_dir': working_dir,
                'volumes': volumes,
                'environment': environment,
                'detach': True,
                'auto_remove': False,  # Manual cleanup for better control
                'mem_limit': self.memory_limit,
                'cpu_quota': self.cpu_quota,
                'network_disabled': self.network_disabled,
                'stdin_open': False,
                'tty': False,
            }

            logger.debug(f"Starting container with command: {command}")
            container = self.client.containers.run(**container_config)

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result['StatusCode']
            except Exception as e:
                logger.warning(f"Container timeout or error: {e}")
                container.stop(timeout=1)
                exit_code = -1

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            logger.debug(f"Container execution completed: exit_code={exit_code}, duration={duration_ms}ms")

            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                container_id=container.id,
                success=(exit_code == 0)
            )

        except docker.errors.ContainerError as e:
            logger.error(f"Container execution failed: {e}")
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return SandboxResult(
                exit_code=e.exit_status,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                container_id=e.container.id if e.container else "unknown",
                success=False
            )

        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"Docker API Error: {e}",
                duration_ms=duration_ms,
                container_id="unknown",
                success=False
            )

        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                    logger.debug(f"Container {container.id[:12]} removed")
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

    def execute_with_files(
        self,
        command: str,
        files: Dict[str, str],
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """
        Execute command with temporary files.
        
        Creates temporary directory, writes files, executes command, and cleans up.
        
        Args:
            command: Command to execute
            files: Dict mapping filenames to content
            timeout: Timeout in seconds
            env: Environment variables
        
        Returns:
            SandboxResult with execution details
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write files
            for filename, content in files.items():
                filepath = tmppath / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)

            # Execute in sandbox
            return self.execute(
                command=command,
                cwd=tmppath,
                timeout=timeout,
                readonly=False,  # Need write access for execution
                env=env
            )

    def test_availability(self) -> Dict[str, Any]:
        """
        Test sandbox availability and capabilities.
        
        Returns:
            Dict with availability status and details
        """
        if not self.is_available():
            return {
                'available': False,
                'reason': 'Docker client not initialized'
            }

        try:
            # Test with simple command
            result = self.execute("echo 'Sandbox test'", timeout=5)

            return {
                'available': True,
                'image': self.image,
                'memory_limit': self.memory_limit,
                'cpu_quota': self.cpu_quota,
                'network_disabled': self.network_disabled,
                'test_result': result.success,
                'test_output': result.stdout.strip()
            }
        except Exception as e:
            return {
                'available': False,
                'reason': f'Test execution failed: {e}'
            }

    def cleanup_old_containers(self, older_than_hours: int = 24):
        """
        Cleanup old containers from previous executions.
        
        Args:
            older_than_hours: Remove containers older than this many hours
        """
        if not self.is_available():
            return

        try:
            containers = self.client.containers.list(all=True)
            removed = 0

            for container in containers:
                # Check if it's our container (by image)
                if container.image.tags and self.image in container.image.tags:
                    # Remove if stopped
                    if container.status != 'running':
                        container.remove(force=True)
                        removed += 1

            if removed > 0:
                logger.info(f"Cleaned up {removed} old sandbox containers")
        except Exception as e:
            logger.warning(f"Failed to cleanup containers: {e}")


# Global singleton instance
_sandbox_instance: Optional[SandboxExecutor] = None


def get_sandbox() -> SandboxExecutor:
    """Get global sandbox executor instance."""
    global _sandbox_instance

    if _sandbox_instance is None:
        _sandbox_instance = SandboxExecutor()

    return _sandbox_instance
