"""freeRTOS-visualizer: real-time visualization of FreeRTOS task states."""

from freertos_visualizer.simulator import DEFAULT_TASKS, TaskSimulator
from freertos_visualizer.stats import compute_summary, format_summary
from freertos_visualizer.timeline import STATE_COLORS, compute_segments
from freertos_visualizer.visualize import (
    STATE_DICT,
    SerialConnection,
    TaskStateStore,
    parse_serial_line,
)

__all__ = [
    "STATE_DICT",
    "SerialConnection",
    "TaskStateStore",
    "TaskSimulator",
    "DEFAULT_TASKS",
    "compute_summary",
    "format_summary",
    "compute_segments",
    "STATE_COLORS",
    "parse_serial_line",
]
