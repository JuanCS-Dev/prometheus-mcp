"""Shell bridge - connects parser, LLM, and tool execution.

This is the CORE integration component that makes Phase 2.1 work.

Inspired by best practices from:
- Cursor AI: Semantic code understanding + RAG
- Claude Code: Hook-based validation + persistent sessions
- GitHub Codex: Tool calling + sandboxed execution  
- Aider AI: Function calling + context mapping

Architecture:
    User Input → LLM → Parser → Safety Check → Tool Execution → Result → LLM
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime

from ..core.parser import ResponseParser
from ..core.llm import LLMClient
from ..tools.base import ToolRegistry
from .safety import SafetyValidator
from .session import SessionManager, Session

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of tool execution."""
    success: bool
    tool_name: str
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    blocked: bool = False
    block_reason: Optional[str] = None


class ShellBridge:
    """Connects parser → validation → execution in a safe, efficient pipeline.
    
    This is what makes our implementation production-grade like Cursor/Claude.
    
    Features:
    - Multi-layer safety (Claude Code strategy)
    - Persistent sessions (Codex strategy)
    - Context-aware execution (Cursor strategy)
    - Automatic error recovery (Aider strategy)
    """
    
    def __init__(
        self,
        parser: Optional[ResponseParser] = None,
        llm_client: Optional[LLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        safety_validator: Optional[SafetyValidator] = None,
        session_manager: Optional[SessionManager] = None,
    ):
        """Initialize shell bridge.
        
        Args:
            parser: Response parser (creates new if None)
            llm_client: LLM client (creates new if None)
            tool_registry: Tool registry (creates new if None)
            safety_validator: Safety validator (creates new if None)
            session_manager: Session manager (creates new if None)
        """
        from ..core.parser import parser as default_parser
        from ..core.llm import llm_client as default_llm
        from .safety import safety_validator as default_safety
        from .session import session_manager as default_session
        
        self.parser = parser or default_parser
        self.llm = llm_client or default_llm
        self.registry = tool_registry or ToolRegistry()
        self.safety = safety_validator or default_safety
        self.sessions = session_manager or default_session
        
        self.current_session: Optional[Session] = None
        
        # Register core tools (Copilot + Cursor + Claude pattern)
        self._register_core_tools()
        
        logger.info("ShellBridge initialized")
    
    def _register_core_tools(self):
        """Register core tools (always available).
        
        Implements hybrid registry pattern:
        - Core tools (file, terminal, git) always loaded
        - Dynamic discovery based on project context
        - Lazy loading for heavy dependencies
        
        Inspired by:
        - Copilot CLI: Static core + dynamic permissions
        - Cursor AI: Context-aware discovery
        - Claude Code: MCP-style on-demand execution
        """
        from ..tools.file_ops import (
            ReadFileTool, WriteFileTool, EditFileTool,
            ListDirectoryTool, DeleteFileTool
        )
        from ..tools.file_mgmt import (
            MoveFileTool, CopyFileTool, CreateDirectoryTool,
            ReadMultipleFilesTool, InsertLinesTool
        )
        from ..tools.search import SearchFilesTool, GetDirectoryTreeTool
        from ..tools.web_search import WebSearchTool, SearchDocumentationTool
        from ..tools.exec import BashCommandTool
        from ..tools.git_ops import GitStatusTool, GitDiffTool
        from ..tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
        from ..tools.terminal import (
            CdTool, LsTool, PwdTool, MkdirTool, RmTool,
            CpTool, MvTool, TouchTool, CatTool
        )
        
        # File operations (9 tools)
        self.registry.register(ReadFileTool())
        self.registry.register(WriteFileTool())
        self.registry.register(EditFileTool())
        self.registry.register(ListDirectoryTool())
        self.registry.register(DeleteFileTool())
        self.registry.register(MoveFileTool())
        self.registry.register(CopyFileTool())
        self.registry.register(CreateDirectoryTool())
        self.registry.register(ReadMultipleFilesTool())
        self.registry.register(InsertLinesTool())
        
        # Search & navigation (4 tools)
        self.registry.register(SearchFilesTool())
        self.registry.register(GetDirectoryTreeTool())
        self.registry.register(WebSearchTool())
        self.registry.register(SearchDocumentationTool())
        
        # Execution (1 tool)
        self.registry.register(BashCommandTool())
        
        # Git operations (2 tools)
        self.registry.register(GitStatusTool())
        self.registry.register(GitDiffTool())
        
        # Context management (3 tools)
        self.registry.register(GetContextTool())
        self.registry.register(SaveSessionTool())
        self.registry.register(RestoreBackupTool())
        
        # Terminal commands (9 tools)
        self.registry.register(CdTool())
        self.registry.register(LsTool())
        self.registry.register(PwdTool())
        self.registry.register(MkdirTool())
        self.registry.register(RmTool())
        self.registry.register(CpTool())
        self.registry.register(MvTool())
        self.registry.register(TouchTool())
        self.registry.register(CatTool())
        
        logger.info(f"Registered {len(self.registry.tools)} core tools")
    
    async def process_input(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Process user input through full pipeline.
        
        This is the main entry point for Phase 2.1 integration.
        
        Flow:
        1. Get/create session
        2. Build context (files, history, etc)
        3. Send to LLM
        4. Parse response
        5. Validate & execute tools
        6. Return results
        
        Args:
            user_input: User's natural language input
            session_id: Session ID (creates new if None)
            context: Additional context dictionary
            
        Yields:
            Streaming response chunks
        """
        # Get or create session
        if session_id:
            session = self.sessions.get_or_create_session(session_id)
        else:
            session = self.sessions.create_session()
        
        self.current_session = session
        
        # Track user input
        session.add_history("user_input", {"input": user_input})
        
        try:
            # Build rich context (Cursor strategy)
            full_context = await self._build_context(session, context)
            
            # Stream from LLM
            full_response = ""
            async for chunk in self.llm.stream_chat(
                prompt=user_input,
                context=full_context,
                provider="auto"
            ):
                full_response += chunk
                yield chunk
            
            # Parse response for tool calls
            parse_result = self.parser.parse(full_response)
            
            if not parse_result.success:
                logger.warning(f"Parse failed: {parse_result.error}")
                yield f"\n\n⚠️ Parse error: {parse_result.error}"
                return
            
            # Execute tool calls if present
            if parse_result.tool_calls:
                yield "\n\n🔧 Executing tools...\n"
                
                results = await self._execute_tool_calls(
                    parse_result.tool_calls,
                    session
                )
                
                # Format and yield results
                for result in results:
                    yield self._format_execution_result(result)
            
            # Save session
            self.sessions._save_session(session)
            
        except Exception as e:
            logger.error(f"Error in process_input: {e}", exc_info=True)
            session.add_history("error", {"error": str(e)}, success=False)
            yield f"\n\n❌ Error: {str(e)}"
    
    async def execute_tool_calls(
        self,
        llm_response: str,
        session_id: Optional[str] = None,
    ) -> List[ExecutionResult]:
        """Execute tool calls from LLM response.
        
        This is the lower-level API for direct tool execution.
        
        Args:
            llm_response: Raw LLM response text
            session_id: Session ID (uses active if None)
            
        Returns:
            List of execution results
        """
        # Get session
        if session_id:
            session = self.sessions.get_or_create_session(session_id)
        else:
            session = self.sessions.get_active_session()
            if not session:
                session = self.sessions.create_session()
        
        # Parse response
        parse_result = self.parser.parse(llm_response)
        
        if not parse_result.success:
            logger.error(f"Parse failed: {parse_result.error}")
            return []
        
        if not parse_result.tool_calls:
            logger.info("No tool calls found in response")
            return []
        
        # Execute tools
        return await self._execute_tool_calls(parse_result.tool_calls, session)
    
    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        session: Session,
    ) -> List[ExecutionResult]:
        """Execute list of tool calls with safety validation.
        
        Args:
            tool_calls: Parsed tool calls
            session: Current session
            
        Returns:
            List of execution results
        """
        results = []
        
        for tool_call in tool_calls:
            result = await self._execute_single_tool(tool_call, session)
            results.append(result)
            
            # Track in session
            session.add_history(
                "tool_call",
                {
                    "tool": tool_call.get("tool"),
                    "args": tool_call.get("arguments", {}),
                },
                result=result.result,
                success=result.success
            )
        
        return results
    
    async def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        session: Session,
    ) -> ExecutionResult:
        """Execute single tool with full safety pipeline.
        
        Pipeline:
        1. Safety validation (Claude Code strategy)
        2. Tool execution
        3. Error handling
        4. Context tracking (Cursor strategy)
        
        Args:
            tool_call: Tool call dictionary
            session: Current session
            
        Returns:
            Execution result
        """
        start_time = datetime.now()
        tool_name = tool_call.get("tool", "unknown")
        # Support both "arguments" and "args" for compatibility
        arguments = tool_call.get("arguments") or tool_call.get("args", {})
        
        # Safety check (CRITICAL - Claude Code strategy)
        is_safe, block_reason = self.safety.is_safe(tool_call)
        if not is_safe:
            logger.warning(f"Tool call blocked: {block_reason}")
            return ExecutionResult(
                success=False,
                tool_name=tool_name,
                result=None,
                error=block_reason,
                blocked=True,
                block_reason=block_reason,
            )
        
        try:
            # Get tool from registry
            if tool_name not in self.registry.tools:
                return ExecutionResult(
                    success=False,
                    tool_name=tool_name,
                    result=None,
                    error=f"Tool not found: {tool_name}",
                )
            
            tool = self.registry.tools[tool_name]
            
            # Execute tool
            result = await tool.execute(**arguments)
            
            # Track file operations (Cursor strategy)
            self._track_file_operation(tool_name, arguments, session)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Check if tool execution actually succeeded
            tool_success = result.success if hasattr(result, 'success') else True
            
            return ExecutionResult(
                success=tool_success,
                tool_name=tool_name,
                result=result,
                execution_time=execution_time,
            )
        
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ExecutionResult(
                success=False,
                tool_name=tool_name,
                result=None,
                error=str(e),
                execution_time=execution_time,
            )
    
    def _track_file_operation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session: Session,
    ):
        """Track file operations for context (Cursor strategy)."""
        path = arguments.get("path") or arguments.get("file")
        if not path:
            return
        
        # Map tool names to operations
        if tool_name in ["read_file", "read_multiple_files", "cat"]:
            session.track_file_operation("read", path)
        elif tool_name in ["write_file", "edit_file", "touch"]:
            session.track_file_operation("write", path)
        elif tool_name in ["delete_file", "rm"]:
            session.track_file_operation("delete", path)
    
    async def _build_context(
        self,
        session: Session,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build rich context for LLM (Cursor RAG strategy).
        
        Args:
            session: Current session
            additional_context: Additional context to include
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Session info
        context_parts.append(f"Current directory: {session.cwd}")
        
        # Recent history (last 5 actions)
        if session.history:
            context_parts.append("\nRecent actions:")
            for entry in session.history[-5:]:
                action = entry.get("action")
                details = entry.get("details", {})
                context_parts.append(f"- {action}: {details}")
        
        # Modified files
        if session.modified_files:
            context_parts.append(f"\nModified files: {len(session.modified_files)}")
        
        # Additional context
        if additional_context:
            context_parts.append(f"\nAdditional context: {additional_context}")
        
        return "\n".join(context_parts)
    
    def _format_execution_result(self, result: ExecutionResult) -> str:
        """Format execution result for display."""
        if result.blocked:
            return f"🚫 {result.tool_name}: BLOCKED - {result.block_reason}\n"
        
        if not result.success:
            return f"❌ {result.tool_name}: ERROR - {result.error}\n"
        
        time_str = f"({result.execution_time:.2f}s)" if result.execution_time > 0 else ""
        return f"✅ {result.tool_name} {time_str}\n"
    
    def get_session_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get information about current session."""
        if session_id:
            session = self.sessions.get_session(session_id)
        else:
            session = self.current_session or self.sessions.get_active_session()
        
        if not session:
            return {"error": "No active session"}
        
        return session.get_summary()


# Global shell bridge instance
shell_bridge = ShellBridge()
