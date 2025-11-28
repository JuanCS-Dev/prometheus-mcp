"""Session state dataclass."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any


@dataclass
class SessionState:
    """Complete session state for persistence.
    
    Attributes:
        session_id: Unique session identifier
        cwd: Working directory path
        history: Command history list
        conversation: List of message dicts (role, content)
        context: Current context dictionary
        files_read: Set of files read during session
        files_modified: Set of files modified during session
        tool_calls_count: Number of tool calls made
        created_at: Session creation timestamp
        last_activity: Last activity timestamp
        metadata: Additional metadata
    """

    session_id: str
    cwd: Path
    history: List[str] = field(default_factory=list)
    conversation: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    files_read: Set[str] = field(default_factory=set)
    files_modified: Set[str] = field(default_factory=set)
    tool_calls_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session state to dictionary for serialization.
        
        Returns:
            Dictionary representation of session state
        """
        return {
            'session_id': self.session_id,
            'cwd': str(self.cwd),
            'history': self.history,
            'conversation': self.conversation,
            'context': self.context,
            'files_read': list(self.files_read),
            'files_modified': list(self.files_modified),
            'tool_calls_count': self.tool_calls_count,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create session state from dictionary.
        
        Args:
            data: Dictionary with session data
            
        Returns:
            SessionState instance
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ['session_id', 'cwd', 'created_at', 'last_activity']
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields in session data: {', '.join(missing)}")

        try:
            return cls(
                session_id=data['session_id'],
                cwd=Path(data['cwd']),
                history=data.get('history', []),
                conversation=data.get('conversation', []),
                context=data.get('context', {}),
                files_read=set(data.get('files_read', [])),
                files_modified=set(data.get('files_modified', [])),
                tool_calls_count=data.get('tool_calls_count', 0),
                created_at=datetime.fromisoformat(data['created_at']),
                last_activity=datetime.fromisoformat(data['last_activity']),
                metadata=data.get('metadata', {}),
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid session data format: {e}")

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def add_message(self, role: str, content: str):
        """Add message to conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.conversation.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
        })
        self.update_activity()

    def add_file_read(self, filepath: str):
        """Track file that was read.
        
        Args:
            filepath: Path to file that was read
        """
        self.files_read.add(filepath)
        self.update_activity()

    def add_file_modified(self, filepath: str):
        """Track file that was modified.
        
        Args:
            filepath: Path to file that was modified
        """
        self.files_modified.add(filepath)
        self.update_activity()

    def increment_tool_calls(self):
        """Increment tool call counter."""
        self.tool_calls_count += 1
        self.update_activity()
