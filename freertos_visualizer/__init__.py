"""freeRTOS-visualizer: real-time visualization of FreeRTOS task states."""

from freertos_visualizer.simulator import DEFAULT_TASKS, TaskSimulator
from freertos_visualizer.stats import compute_summary, format_summary
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
    "parse_serial_line",
]
