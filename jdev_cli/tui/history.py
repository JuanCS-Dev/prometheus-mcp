"""Advanced command history system with search and analytics.

Constitutional compliance: P1 (Completeness), P4 (Traceability), P6 (Efficiency)
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class HistoryEntry:
    """Single command history entry."""

    timestamp: str
    command: str
    cwd: str
    success: bool
    duration_ms: int
    tokens_used: int = 0
    tool_calls: int = 0
    files_modified: List[str] = None
    session_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.files_modified is None:
            self.files_modified = []


class CommandHistory:
    """Persistent command history with advanced search."""

    def __init__(self, db_path: Optional[Path | str] = None):
        """Initialize history database."""
        if db_path is None:
            self.db_path = Path.home() / '.jdev_cli' / 'history.db'
        elif isinstance(db_path, str):
            self.db_path = Path(db_path)
        else:
            self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                command TEXT NOT NULL,
                cwd TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                duration_ms INTEGER NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                tool_calls INTEGER DEFAULT 0,
                files_modified TEXT,
                session_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for fast search
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_command ON history(command)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cwd ON history(cwd)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON history(session_id)')

        conn.commit()
        conn.close()

    def add(self, entry: HistoryEntry) -> int:
        """Add entry to history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO history (
                timestamp, command, cwd, success, duration_ms,
                tokens_used, tool_calls, files_modified, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.timestamp,
            entry.command,
            entry.cwd,
            entry.success,
            entry.duration_ms,
            entry.tokens_used,
            entry.tool_calls,
            json.dumps(entry.files_modified),
            entry.session_id
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id

    def get_recent(self, limit: int = 100) -> List[HistoryEntry]:
        """Get recent history entries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM history
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))

        entries = [self._row_to_entry(row) for row in cursor.fetchall()]
        conn.close()
        return entries

    def search(
        self,
        query: str,
        limit: int = 50,
        cwd_filter: Optional[str] = None
    ) -> List[HistoryEntry]:
        """Fuzzy search history entries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Simple fuzzy search using LIKE
        sql = 'SELECT * FROM history WHERE command LIKE ?'
        params = [f'%{query}%']

        if cwd_filter:
            sql += ' AND cwd LIKE ?'
            params.append(f'{cwd_filter}%')

        sql += ' ORDER BY id DESC LIMIT ?'
        params.append(str(limit))

        cursor.execute(sql, params)
        entries = [self._row_to_entry(row) for row in cursor.fetchall()]
        conn.close()
        return entries

    def get_by_session(self, session_id: str) -> List[HistoryEntry]:
        """Get all commands from a session."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM history
            WHERE session_id = ?
            ORDER BY id ASC
        ''', (session_id,))

        entries = [self._row_to_entry(row) for row in cursor.fetchall()]
        conn.close()
        return entries

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get usage statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get stats from last N days
        cursor.execute('''
            SELECT
                COUNT(*) as total_commands,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                AVG(duration_ms) as avg_duration,
                SUM(tokens_used) as total_tokens,
                SUM(tool_calls) as total_tool_calls
            FROM history
            WHERE datetime(created_at) >= datetime('now', '-' || ? || ' days')
        ''', (days,))

        row = cursor.fetchone()

        stats = {
            'total_commands': row[0] or 0,
            'successful': row[1] or 0,
            'failed': row[2] or 0,
            'avg_duration_ms': round(row[3] or 0, 2),
            'total_tokens': row[4] or 0,
            'total_tool_calls': row[5] or 0,
            'success_rate': round((row[1] or 0) / (row[0] or 1) * 100, 2)
        }

        # Get most used commands
        cursor.execute('''
            SELECT command, COUNT(*) as count
            FROM history
            WHERE datetime(created_at) >= datetime('now', '-' || ? || ' days')
            GROUP BY command
            ORDER BY count DESC
            LIMIT 10
        ''', (days,))

        stats['top_commands'] = [
            {'command': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]

        conn.close()
        return stats

    def clear(self, days_to_keep: Optional[int] = None) -> int:
        """Clear history (optionally keeping recent N days)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if days_to_keep:
            cursor.execute('''
                DELETE FROM history
                WHERE datetime(created_at) < datetime('now', '-' || ? || ' days')
            ''', (days_to_keep,))
        else:
            cursor.execute('DELETE FROM history')

        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def _row_to_entry(self, row: sqlite3.Row) -> HistoryEntry:
        """Convert database row to HistoryEntry."""
        return HistoryEntry(
            timestamp=row['timestamp'],
            command=row['command'],
            cwd=row['cwd'],
            success=bool(row['success']),
            duration_ms=row['duration_ms'],
            tokens_used=row['tokens_used'],
            tool_calls=row['tool_calls'],
            files_modified=json.loads(row['files_modified']) if row['files_modified'] else [],
            session_id=row['session_id']
        )


class SessionReplay:
    """Replay command history from previous sessions."""

    def __init__(self, history: CommandHistory):
        self.history = history

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent sessions with metadata."""
        entries = self.history.get_recent(limit=500)

        # Group by session
        sessions: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            if not entry.session_id:
                continue

            if entry.session_id not in sessions:
                sessions[entry.session_id] = {
                    'session_id': entry.session_id,
                    'start_time': entry.timestamp,
                    'command_count': 0,
                    'total_tokens': 0,
                    'success_count': 0,
                    'files_modified': set()
                }

            session = sessions[entry.session_id]
            session['command_count'] += 1
            session['total_tokens'] += entry.tokens_used
            if entry.success:
                session['success_count'] += 1
            session['files_modified'].update(entry.files_modified)

        # Convert to list and sort
        session_list = [
            {**session, 'files_modified': list(session['files_modified'])}
            for session in sessions.values()
        ]
        session_list.sort(key=lambda x: x['start_time'], reverse=True)

        return session_list[:limit]

    def replay(self, session_id: str) -> List[str]:
        """Get commands from session for replay."""
        entries = self.history.get_by_session(session_id)
        return [entry.command for entry in entries]

    def export(self, session_id: str, output_path: Path) -> None:
        """Export session to file."""
        entries = self.history.get_by_session(session_id)

        export_data = {
            'session_id': session_id,
            'exported_at': datetime.now().isoformat(),
            'commands': [asdict(entry) for entry in entries]
        }

        output_path.write_text(json.dumps(export_data, indent=2))


# Export main interfaces
__all__ = [
    'CommandHistory',
    'HistoryEntry',
    'SessionReplay'
]
