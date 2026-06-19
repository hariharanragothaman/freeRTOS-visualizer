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


class SegmentCache:
    """Incrementally maintains Gantt segments as samples are appended.

    :func:`compute_segments` rebuilds every task's full history on each call —
    O(total samples) per repaint. Once ingest is decoupled from paint
    (`SerialReader`), that recompute dominates a long session. This cache keeps a
    per-task running span and only appends *new* samples; it falls back to a full
    rebuild for a task whose history was trimmed/reset (so it stays correct under
    ``max_history`` eviction). Output is identical to :func:`compute_segments`.
    """

    def __init__(self):
        self._state = {}

    def update(self, store):
        result = {}
        for task_name, states in store.task_states.items():
            stamps = store.task_timestamps.get(task_name, [])
            n = min(len(states), len(stamps))
            st = self._state.get(task_name)
            trimmed = (
                st is None
                or st["count"] == 0
                or n < st["count"]
                or (n and stamps[0] != st["first_ts"])
            )
            if trimmed:
                st = self._rebuild(stamps, states, n)
            elif n > st["count"]:
                self._append(st, stamps, states, n)
            self._state[task_name] = st
            result[task_name] = self._materialize(st)

        # Forget tasks that no longer exist in the store.
        for gone in set(self._state) - set(store.task_states):
            del self._state[gone]
        return result

    @staticmethod
    def _rebuild(stamps, states, n):
        st = {
            "count": n,
            "first_ts": stamps[0] if n else None,
            "completed": [],
            "run_start": stamps[0] if n else None,
            "run_state": states[0] if n else None,
            "last_ts": stamps[0] if n else None,
        }
        if n:
            SegmentCache._append(st, stamps, states, n, _from=1)
        return st

    @staticmethod
    def _append(st, stamps, states, n, _from=None):
        start = st["count"] if _from is None else _from
        for i in range(start, n):
            if states[i] != st["run_state"]:
                st["completed"].append((st["run_start"], stamps[i], st["run_state"]))
                st["run_start"] = stamps[i]
                st["run_state"] = states[i]
            st["last_ts"] = stamps[i]
        st["count"] = n

    @staticmethod
    def _materialize(st):
        if st["run_state"] is None:
            return []
        return st["completed"] + [(st["run_start"], st["last_ts"], st["run_state"])]


# Keep STATE_DICT importable from here for convenience / discoverability.
__all__ = [
    "STATE_COLORS",
    "state_color",
    "compute_segments",
    "SegmentCache",
    "STATE_DICT",
]
