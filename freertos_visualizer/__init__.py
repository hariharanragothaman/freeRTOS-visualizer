"""freeRTOS-visualizer: real-time visualization of FreeRTOS task states."""

from freertos_visualizer.reader import SerialReader
from freertos_visualizer.security import (
    sanitize_csv_field,
    sanitize_display_text,
    strip_ansi,
)
from freertos_visualizer.simulator import DEFAULT_TASKS, TaskSimulator
from freertos_visualizer.stats import compute_summary, format_summary
from freertos_visualizer.timeline import STATE_COLORS, SegmentCache, compute_segments
from freertos_visualizer.visualize import (
    STATE_DICT,
    SerialConnection,
    TaskStateStore,
    parse_meta_line,
    parse_serial_line,
)

__all__ = [
    "STATE_DICT",
    "SerialConnection",
    "SerialReader",
    "TaskStateStore",
    "TaskSimulator",
    "DEFAULT_TASKS",
    "compute_summary",
    "format_summary",
    "compute_segments",
    "SegmentCache",
    "STATE_COLORS",
    "parse_serial_line",
    "parse_meta_line",
    "sanitize_csv_field",
    "sanitize_display_text",
    "strip_ansi",
]
