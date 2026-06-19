"""Timeline / Gantt segment computation for freeRTOS-visualizer.

Collapses a task's timestamped state history into contiguous ``(start, end,
state)`` spans suitable for a Gantt-style ``broken_barh`` plot. The segment
computation is pure (no GUI), so it is fully unit-testable; the rendering layer
in ``visualize.py`` consumes its output.
"""

from freertos_visualizer.visualize import STATE_DICT

# Stable colour per state for both the timeline and any legend.
STATE_COLORS = {
    "Running": "#2ca02c",    # green
    "Ready": "#1f77b4",      # blue
    "Blocked": "#ff7f0e",    # orange
    "Suspended": "#d62728",  # red
    "Deleted": "#9467bd",    # purple
    "Invalid": "#8c564b",    # brown
    "Unknown": "#7f7f7f",    # grey
}


def state_color(state):
    """Return the colour for ``state``, falling back to the Unknown colour."""
    return STATE_COLORS.get(state, STATE_COLORS["Unknown"])


def _segments_for(timestamps, states):
    n = min(len(timestamps), len(states))
    if n == 0:
        return []

    spans = []
    start_idx = 0
    for i in range(1, n):
        if states[i] != states[start_idx]:
            spans.append((timestamps[start_idx], timestamps[i], states[start_idx]))
            start_idx = i
    # Final span ends at the last sample's timestamp. If the last sample begins a
    # new state it is a zero-width span, mirroring how stats treats the final
    # sample (its trailing duration is unknown).
    spans.append((timestamps[start_idx], timestamps[n - 1], states[start_idx]))
    return spans


def compute_segments(store):
    """Return ``{task_name: [(start, end, state), ...]}`` for every task."""
    segments = {}
    for task_name, states in store.task_states.items():
        timestamps = store.task_timestamps.get(task_name, [])
        segments[task_name] = _segments_for(timestamps, states)
    return segments


# Keep STATE_DICT importable from here for convenience / discoverability.
__all__ = ["STATE_COLORS", "state_color", "compute_segments", "STATE_DICT"]
