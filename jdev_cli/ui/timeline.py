"""Timeline replay system for session events."""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
from enum import Enum


class EventType(Enum):
    """Types of recordable events."""
    USER_INPUT = "user_input"
    ASSISTANT_RESPONSE = "assistant_response"
    TOOL_CALL = "tool_call"
    FILE_EDIT = "file_edit"
    COMMAND_EXECUTE = "command_execute"
    CONTEXT_UPDATE = "context_update"
    ERROR = "error"


@dataclass
class TimelineEvent:
    """Single event in timeline."""
    timestamp: datetime
    event_type: EventType
    description: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None


class Timeline:
    """Session timeline with playback capabilities."""

    def __init__(self):
        """Initialize timeline."""
        self.events: List[TimelineEvent] = []
        self.playback_index: int = 0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0

    def record(self, event_type: EventType, description: str, data: Dict = None, duration_ms: float = None):
        """Record new event."""
        event = TimelineEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            description=description,
            data=data or {},
            duration_ms=duration_ms
        )
        self.events.append(event)

    def get_events(self, event_type: Optional[EventType] = None, since: Optional[datetime] = None) -> List[TimelineEvent]:
        """Get filtered events."""
        filtered = self.events

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        if since:
            filtered = [e for e in filtered if e.timestamp >= since]

        return filtered

    def jump_to(self, index: int) -> Optional[TimelineEvent]:
        """Jump to specific event in timeline."""
        if 0 <= index < len(self.events):
            self.playback_index = index
            return self.events[index]
        return None

    def next_event(self) -> Optional[TimelineEvent]:
        """Get next event in playback."""
        if self.playback_index < len(self.events):
            event = self.events[self.playback_index]
            self.playback_index += 1
            return event
        return None

    def previous_event(self) -> Optional[TimelineEvent]:
        """Get previous event in playback."""
        if self.playback_index > 0:
            self.playback_index -= 1
            return self.events[self.playback_index]
        return None

    def set_playback_speed(self, speed: float):
        """Set playback speed multiplier."""
        self.playback_speed = max(0.1, min(speed, 10.0))  # Clamp between 0.1x and 10x

    def export(self, filepath: Optional[str] = None) -> str:
        """Export timeline to JSON."""
        data = {
            "metadata": {
                "total_events": len(self.events),
                "start_time": self.events[0].timestamp.isoformat() if self.events else None,
                "end_time": self.events[-1].timestamp.isoformat() if self.events else None,
                "export_time": datetime.now().isoformat()
            },
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.event_type.value,
                    "description": e.description,
                    "data": e.data,
                    "duration_ms": e.duration_ms
                }
                for e in self.events
            ]
        }

        json_str = json.dumps(data, indent=2)

        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)

        return json_str

    def import_timeline(self, json_data: str):
        """Import timeline from JSON."""
        data = json.loads(json_data)
        self.events = []

        for event_dict in data.get("events", []):
            event = TimelineEvent(
                timestamp=datetime.fromisoformat(event_dict["timestamp"]),
                event_type=EventType(event_dict["type"]),
                description=event_dict["description"],
                data=event_dict.get("data", {}),
                duration_ms=event_dict.get("duration_ms")
            )
            self.events.append(event)

    def get_summary(self) -> Dict:
        """Get timeline summary statistics."""
        if not self.events:
            return {"empty": True}

        event_counts = {}
        total_duration = 0

        for event in self.events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            if event.duration_ms:
                total_duration += event.duration_ms

        duration = (self.events[-1].timestamp - self.events[0].timestamp).total_seconds()

        return {
            "total_events": len(self.events),
            "event_types": event_counts,
            "session_duration_seconds": duration,
            "total_processing_time_ms": total_duration,
            "start_time": self.events[0].timestamp.isoformat(),
            "end_time": self.events[-1].timestamp.isoformat()
        }
