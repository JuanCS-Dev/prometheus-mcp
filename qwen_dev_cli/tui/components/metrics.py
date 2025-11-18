"""
Constitutional Metrics Display - Visual gauges for LEI, HRI, Safety
Apple-style clean visualization of code quality metrics

Features:
- LEI Meter (Lazy Engineering Index: 0.0 = perfect)
- HRI Gauge (Human Readability Index: 0-100, higher = better)
- Safety Status Panel (warnings, errors)
- CPI Chart (Constitutional Performance Index over time)
- Real-time updates
- Color-coded thresholds (green/yellow/red)
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime

from rich.console import RenderableType
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table
from rich.text import Text
from textual.widgets import Static
from textual.containers import Horizontal, Vertical

from qwen_dev_cli.tui.theme import COLORS


class MetricLevel(Enum):
    """Metric quality levels"""
    EXCELLENT = "excellent"  # Green
    GOOD = "good"            # Light green
    WARNING = "warning"      # Yellow
    POOR = "poor"            # Orange
    CRITICAL = "critical"    # Red


@dataclass
class LEIMetric:
    """
    Lazy Engineering Index (0.0 - 1.0)
    
    Measures:
    - TODOs, FIXMEs, placeholders
    - Hardcoded values
    - Magic numbers
    - Copy-paste code
    - Incomplete implementations
    
    0.0 = Perfect (no laziness)
    1.0 = Terrible (all placeholders)
    """
    value: float  # 0.0 to 1.0
    total_issues: int
    issues_by_type: Dict[str, int]
    
    @property
    def level(self) -> MetricLevel:
        """Determine quality level"""
        if self.value == 0.0:
            return MetricLevel.EXCELLENT
        elif self.value < 0.1:
            return MetricLevel.GOOD
        elif self.value < 0.3:
            return MetricLevel.WARNING
        elif self.value < 0.6:
            return MetricLevel.POOR
        else:
            return MetricLevel.CRITICAL
    
    @property
    def color(self) -> str:
        """Get color for current level"""
        return METRIC_COLORS[self.level]
    
    @property
    def label(self) -> str:
        """Get text label"""
        if self.value == 0.0:
            return "Perfect"
        elif self.value < 0.1:
            return "Excellent"
        elif self.value < 0.3:
            return "Good"
        elif self.value < 0.6:
            return "Needs Work"
        else:
            return "Critical"


@dataclass
class HRIMetric:
    """
    Human Readability Index (0 - 100)
    
    Measures:
    - Variable naming clarity
    - Function complexity
    - Comment quality
    - Code structure
    - Docstring presence
    
    100 = Perfect readability
    0 = Unreadable
    """
    value: int  # 0 to 100
    factors: Dict[str, int]  # Individual factor scores
    
    @property
    def level(self) -> MetricLevel:
        """Determine quality level"""
        if self.value >= 90:
            return MetricLevel.EXCELLENT
        elif self.value >= 75:
            return MetricLevel.GOOD
        elif self.value >= 60:
            return MetricLevel.WARNING
        elif self.value >= 40:
            return MetricLevel.POOR
        else:
            return MetricLevel.CRITICAL
    
    @property
    def color(self) -> str:
        """Get color for current level"""
        return METRIC_COLORS[self.level]
    
    @property
    def label(self) -> str:
        """Get text label"""
        if self.value >= 90:
            return "Excellent"
        elif self.value >= 75:
            return "Good"
        elif self.value >= 60:
            return "Acceptable"
        elif self.value >= 40:
            return "Poor"
        else:
            return "Unreadable"


@dataclass
class SafetyStatus:
    """
    Safety status and warnings
    
    Tracks:
    - Security vulnerabilities
    - Type safety violations
    - Potential runtime errors
    - Best practice violations
    """
    safe: bool
    warnings: List[str]
    errors: List[str]
    last_check: datetime
    
    @property
    def level(self) -> MetricLevel:
        """Determine safety level"""
        if not self.errors and not self.warnings:
            return MetricLevel.EXCELLENT
        elif not self.errors and len(self.warnings) <= 2:
            return MetricLevel.GOOD
        elif not self.errors:
            return MetricLevel.WARNING
        elif len(self.errors) <= 2:
            return MetricLevel.POOR
        else:
            return MetricLevel.CRITICAL
    
    @property
    def color(self) -> str:
        """Get color for safety level"""
        return METRIC_COLORS[self.level]
    
    @property
    def icon(self) -> str:
        """Get icon for safety status"""
        if not self.errors and not self.warnings:
            return "✓"
        elif not self.errors:
            return "⚠"
        else:
            return "✗"


@dataclass
class CPIDataPoint:
    """Single data point for CPI chart"""
    timestamp: datetime
    lei: float
    hri: int
    safety_score: float  # 0.0 to 1.0


# Color mapping for metric levels
METRIC_COLORS = {
    MetricLevel.EXCELLENT: COLORS['accent_green'],
    MetricLevel.GOOD: COLORS['accent_green'],
    MetricLevel.WARNING: COLORS['accent_yellow'],
    MetricLevel.POOR: COLORS['accent_orange'],
    MetricLevel.CRITICAL: COLORS['accent_red'],
}


class LEIMeter(Static):
    """
    Visual LEI gauge (Apple-style)
    
    Display:
    ┌──────────────────────────────┐
    │ 💎 Lazy Engineering Index    │
    │                              │
    │ ████░░░░░░ 0.00              │
    │ Perfect                      │
    │                              │
    │ Issues: 0                    │
    │ • TODOs: 0                   │
    │ • FIXMEs: 0                  │
    │ • Placeholders: 0            │
    └──────────────────────────────┘
    """
    
    def __init__(self, metric: LEIMetric):
        super().__init__()
        self.metric = metric
    
    def render(self) -> RenderableType:
        """Render the LEI meter"""
        content = Text()
        
        # Title
        content.append("💎 Lazy Engineering Index\n\n", style=f"bold {COLORS['accent_purple']}")
        
        # Progress bar (inverted: less = better)
        bar_width = 30
        filled = int((1.0 - self.metric.value) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        content.append(bar, style=self.metric.color)
        content.append(f" {self.metric.value:.2f}\n", style=f"bold {self.metric.color}")
        content.append(f"{self.metric.label}\n\n", style=self.metric.color)
        
        # Issues breakdown
        content.append(f"Issues: {self.metric.total_issues}\n", style=COLORS['text_secondary'])
        for issue_type, count in self.metric.issues_by_type.items():
            content.append(f"• {issue_type}: {count}\n", style=COLORS['text_tertiary'])
        
        return Panel(
            content,
            border_style=self.metric.color,
            padding=(1, 2)
        )


class HRIGauge(Static):
    """
    Visual HRI gauge (Apple-style)
    
    Display:
    ┌──────────────────────────────┐
    │ 📖 Readability Index          │
    │                              │
    │ ██████████ 100/100           │
    │ Excellent                    │
    │                              │
    │ Factors:                     │
    │ • Naming: 100                │
    │ • Complexity: 95             │
    │ • Documentation: 100         │
    └──────────────────────────────┘
    """
    
    def __init__(self, metric: HRIMetric):
        super().__init__()
        self.metric = metric
    
    def render(self) -> RenderableType:
        """Render the HRI gauge"""
        content = Text()
        
        # Title
        content.append("📖 Readability Index\n\n", style=f"bold {COLORS['accent_blue']}")
        
        # Progress bar
        bar_width = 30
        filled = int((self.metric.value / 100.0) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        content.append(bar, style=self.metric.color)
        content.append(f" {self.metric.value}/100\n", style=f"bold {self.metric.color}")
        content.append(f"{self.metric.label}\n\n", style=self.metric.color)
        
        # Factors breakdown
        content.append("Factors:\n", style=COLORS['text_secondary'])
        for factor, score in self.metric.factors.items():
            content.append(f"• {factor}: {score}\n", style=COLORS['text_tertiary'])
        
        return Panel(
            content,
            border_style=self.metric.color,
            padding=(1, 2)
        )


class SafetyPanel(Static):
    """
    Safety status panel
    
    Display:
    ┌──────────────────────────────┐
    │ 🛡️ Safety Status              │
    │                              │
    │ ✓ Safe                       │
    │                              │
    │ Warnings: 0                  │
    │ Errors: 0                    │
    │                              │
    │ Last check: 2 min ago        │
    └──────────────────────────────┘
    """
    
    def __init__(self, status: SafetyStatus):
        super().__init__()
        self.status = status
    
    def render(self) -> RenderableType:
        """Render the safety panel"""
        content = Text()
        
        # Title
        content.append("🛡️ Safety Status\n\n", style=f"bold {COLORS['accent_green']}")
        
        # Status icon + text
        content.append(f"{self.status.icon} ", style=f"bold {self.status.color}")
        status_text = "Safe" if self.status.safe else "Issues Detected"
        content.append(f"{status_text}\n\n", style=f"bold {self.status.color}")
        
        # Counts
        content.append(f"Warnings: {len(self.status.warnings)}\n", style=COLORS['text_secondary'])
        content.append(f"Errors: {len(self.status.errors)}\n\n", style=COLORS['text_secondary'])
        
        # Recent issues (max 3)
        if self.status.warnings:
            content.append("Recent Warnings:\n", style=COLORS['accent_yellow'])
            for warning in self.status.warnings[:3]:
                content.append(f"• {warning}\n", style=COLORS['text_tertiary'])
        
        if self.status.errors:
            content.append("\nErrors:\n", style=COLORS['accent_red'])
            for error in self.status.errors[:3]:
                content.append(f"• {error}\n", style=COLORS['text_tertiary'])
        
        # Last check
        time_ago = self._format_time_ago(self.status.last_check)
        content.append(f"\nLast check: {time_ago}", style=COLORS['text_tertiary'])
        
        return Panel(
            content,
            border_style=self.status.color,
            padding=(1, 2)
        )
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as 'X min ago'"""
        delta = datetime.now() - dt
        if delta.seconds < 60:
            return "just now"
        elif delta.seconds < 3600:
            return f"{delta.seconds // 60} min ago"
        elif delta.seconds < 86400:
            return f"{delta.seconds // 3600} hr ago"
        else:
            return f"{delta.days} days ago"


class CPIChart(Static):
    """
    Constitutional Performance Index chart
    
    Shows trend over time (sparkline-style)
    
    Display:
    ┌──────────────────────────────┐
    │ 📈 CPI Trend (24h)           │
    │                              │
    │ LEI:   ▁▁▂▂▁▁▁▁░             │
    │ HRI:   ▇▇▇▆▆▇▇▇█             │
    │ Safe:  ▇▇▇▇▇▇▇▇▇             │
    │                              │
    │ Current CPI: 98.5/100        │
    └──────────────────────────────┘
    """
    
    def __init__(self, data_points: List[CPIDataPoint], window_hours: int = 24):
        super().__init__()
        self.data_points = data_points
        self.window_hours = window_hours
    
    def render(self) -> RenderableType:
        """Render the CPI chart"""
        content = Text()
        
        # Title
        content.append(f"📈 CPI Trend ({self.window_hours}h)\n\n", style=f"bold {COLORS['accent_purple']}")
        
        if not self.data_points:
            content.append("No data yet", style=COLORS['text_tertiary'])
        else:
            # Generate sparklines
            lei_sparkline = self._generate_sparkline([dp.lei for dp in self.data_points], inverted=True)
            hri_sparkline = self._generate_sparkline([dp.hri / 100.0 for dp in self.data_points])
            safety_sparkline = self._generate_sparkline([dp.safety_score for dp in self.data_points])
            
            # Display sparklines
            content.append("LEI:   ", style=COLORS['text_secondary'])
            content.append(lei_sparkline, style=COLORS['accent_green'])
            content.append("\n")
            
            content.append("HRI:   ", style=COLORS['text_secondary'])
            content.append(hri_sparkline, style=COLORS['accent_blue'])
            content.append("\n")
            
            content.append("Safe:  ", style=COLORS['text_secondary'])
            content.append(safety_sparkline, style=COLORS['accent_green'])
            content.append("\n\n")
            
            # Current CPI score
            current_cpi = self._calculate_cpi(self.data_points[-1])
            cpi_color = self._get_cpi_color(current_cpi)
            content.append(f"Current CPI: ", style=COLORS['text_secondary'])
            content.append(f"{current_cpi:.1f}/100", style=f"bold {cpi_color}")
        
        return Panel(
            content,
            border_style=COLORS['border_emphasis'],
            padding=(1, 2)
        )
    
    def _generate_sparkline(self, values: List[float], inverted: bool = False) -> str:
        """Generate a sparkline from values (0.0 to 1.0)"""
        if not values:
            return "░" * 20
        
        # Sparkline characters (8 levels)
        chars = "▁▂▃▄▅▆▇█"
        if inverted:
            chars = chars[::-1]
        
        # Normalize and convert to chars
        sparkline = ""
        for value in values[-20:]:  # Last 20 data points
            if inverted:
                value = 1.0 - value
            char_index = min(int(value * len(chars)), len(chars) - 1)
            sparkline += chars[char_index]
        
        # Pad if needed
        while len(sparkline) < 20:
            sparkline += "░"
        
        return sparkline
    
    def _calculate_cpi(self, dp: CPIDataPoint) -> float:
        """
        Calculate Constitutional Performance Index
        
        Formula: CPI = (1 - LEI) * 0.3 + (HRI / 100) * 0.4 + safety_score * 0.3
        Range: 0 to 100
        """
        return ((1.0 - dp.lei) * 30.0 + (dp.hri / 100.0) * 40.0 + dp.safety_score * 30.0)
    
    def _get_cpi_color(self, cpi: float) -> str:
        """Get color for CPI score"""
        if cpi >= 90:
            return COLORS['accent_green']
        elif cpi >= 75:
            return COLORS['accent_blue']
        elif cpi >= 60:
            return COLORS['accent_yellow']
        else:
            return COLORS['accent_red']


class MetricsDashboard(Horizontal):
    """
    Complete metrics dashboard (3 columns)
    
    Layout:
    ┌──────────┬──────────┬──────────┐
    │ LEI      │ HRI      │ Safety   │
    │ Meter    │ Gauge    │ Panel    │
    └──────────┴──────────┴──────────┘
    ┌─────────────────────────────────┐
    │ CPI Chart (full width)          │
    └─────────────────────────────────┘
    """
    
    def __init__(
        self,
        lei: LEIMetric,
        hri: HRIMetric,
        safety: SafetyStatus,
        cpi_data: List[CPIDataPoint]
    ):
        super().__init__()
        self.lei = lei
        self.hri = hri
        self.safety = safety
        self.cpi_data = cpi_data
    
    def compose(self):
        """Compose the dashboard layout"""
        yield LEIMeter(self.lei)
        yield HRIGauge(self.hri)
        yield SafetyPanel(self.safety)
        yield CPIChart(self.cpi_data)


# Convenience functions
def create_demo_metrics() -> tuple:
    """Create demo metrics for testing"""
    lei = LEIMetric(
        value=0.0,
        total_issues=0,
        issues_by_type={}
    )
    
    hri = HRIMetric(
        value=100,
        factors={
            "Naming": 100,
            "Complexity": 95,
            "Documentation": 100
        }
    )
    
    safety = SafetyStatus(
        safe=True,
        warnings=[],
        errors=[],
        last_check=datetime.now()
    )
    
    cpi_data = [
        CPIDataPoint(
            timestamp=datetime.now(),
            lei=0.0,
            hri=100,
            safety_score=1.0
        )
    ]
    
    return lei, hri, safety, cpi_data


if __name__ == "__main__":
    # Demo
    print("📊 Constitutional Metrics Display")
    print("=" * 70)
    print("✓ LEI Meter (Lazy Engineering Index)")
    print("✓ HRI Gauge (Human Readability Index)")
    print("✓ Safety Status Panel")
    print("✓ CPI Chart (Constitutional Performance Index)")
    print("✓ Real-time updates")
    print("✓ Color-coded thresholds")
    print("=" * 70)
    print("\n'By wisdom a house is built.' — Proverbs 24:3")
