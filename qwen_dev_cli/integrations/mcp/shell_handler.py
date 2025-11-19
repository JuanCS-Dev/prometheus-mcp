"""Reverse shell handler for MCP - PTY-based interactive shell."""
import asyncio
import os
import pty
import select
import subprocess
import struct
import fcntl
import termios
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ShellSession:
    """PTY-based shell session for interactive command execution."""
    
    def __init__(self, session_id: str, cwd: Optional[str] = None):
        self.session_id = session_id
        self.cwd = cwd or os.getcwd()
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.output_callback: Optional[Callable] = None
        self._running = False
        
    async def start(self):
        """Start shell session with PTY."""
        try:
            self.pid, self.master_fd = pty.fork()
            
            if self.pid == 0:
                os.chdir(self.cwd)
                shell = os.getenv("SHELL", "/bin/bash")
                os.execvp(shell, [shell])
            else:
                self._running = True
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
                logger.info(f"Shell session {self.session_id} started (PID: {self.pid})")
                
        except Exception as e:
            logger.error(f"Failed to start shell: {e}")
            raise
    
    async def write(self, data: str):
        """Write data to shell stdin."""
        if not self._running or self.master_fd is None:
            raise RuntimeError("Shell not running")
        
        try:
            os.write(self.master_fd, data.encode())
        except Exception as e:
            logger.error(f"Write error: {e}")
            raise
    
    async def read(self, timeout: float = 0.1) -> str:
        """Read available output from shell."""
        if not self._running or self.master_fd is None:
            return ""
        
        output = []
        try:
            while True:
                ready, _, _ = select.select([self.master_fd], [], [], timeout)
                if not ready:
                    break
                    
                try:
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        break
                    output.append(data.decode('utf-8', errors='replace'))
                except OSError:
                    break
                    
        except Exception as e:
            logger.error(f"Read error: {e}")
            
        return ''.join(output)
    
    async def execute(self, command: str, timeout: float = 30.0) -> dict:
        """Execute command and return output."""
        if not self._running:
            await self.start()
        
        try:
            await self.write(command + '\n')
            await asyncio.sleep(0.5)
            
            output = await self.read(timeout=1.0)
            
            return {
                "success": True,
                "output": output,
                "session_id": self.session_id,
                "command": command,
                "cwd": self.cwd
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "session_id": self.session_id,
                "command": command
            }
    
    async def resize(self, rows: int, cols: int):
        """Resize PTY."""
        if self.master_fd is None:
            return
            
        try:
            size = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
        except Exception as e:
            logger.error(f"Resize error: {e}")
    
    async def close(self):
        """Close shell session."""
        self._running = False
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except (OSError, ValueError) as e:
                logger.debug(f"Failed to close master_fd {self.master_fd}: {e}")
        if self.pid is not None:
            try:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, 0)
            except (ProcessLookupError, ChildProcessError, PermissionError) as e:
                logger.debug(f"Failed to kill process {self.pid}: {e}")
        logger.info(f"Shell session {self.session_id} closed")


class ShellManager:
    """Manage multiple shell sessions."""
    
    def __init__(self):
        self.sessions: dict[str, ShellSession] = {}
    
    async def create_session(self, session_id: str, cwd: Optional[str] = None) -> ShellSession:
        """Create new shell session."""
        if session_id in self.sessions:
            await self.sessions[session_id].close()
        
        session = ShellSession(session_id, cwd)
        await session.start()
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ShellSession]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str):
        """Close and remove session."""
        if session_id in self.sessions:
            await self.sessions[session_id].close()
            del self.sessions[session_id]
    
    async def close_all(self):
        """Close all sessions."""
        for session_id in list(self.sessions.keys()):
            await self.close_session(session_id)
