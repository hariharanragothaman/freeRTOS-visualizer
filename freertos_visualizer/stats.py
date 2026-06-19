"""Task statistics for freeRTOS-visualizer.

Turns captured task-state history into per-task summaries: sample counts, state
transitions, count-based state distribution, and (when timestamps are present)
time-in-state percentages.
"""

from freertos_visualizer.visualize import STATE_DICT

_ALL_STATES = list(STATE_DICT.values())


def _task_summary(timestamps, states):
    samples = len(states)
    state_counts = {state: 0 for state in _ALL_STATES}
    for state in states:
        state_counts[state] = state_counts.get(state, 0) + 1

    transitions = sum(
        1 for prev, cur in zip(states, states[1:]) if prev != cur
    )

    state_pct = {
        state: (100.0 * count / samples if samples else 0.0)
        for state, count in state_counts.items()
    }

    # Time-in-state: attribute the gap before each sample to the *previous*
    # sample's state. The final sample has no following gap, so its duration is
    # unknown and not counted.
    time_in_state = {state: 0.0 for state in state_counts}
    total_time = 0.0
    if len(timestamps) >= 2 and len(timestamps) == len(states):
        total_time = timestamps[-1] - timestamps[0]
        for i in range(len(states) - 1):
            duration = timestamps[i + 1] - timestamps[i]
            time_in_state[states[i]] = time_in_state.get(states[i], 0.0) + duration

    time_pct = {
        state: (100.0 * dur / total_time if total_time > 0 else 0.0)
        for state, dur in time_in_state.items()
    }

    return {
        "samples": samples,
        "transitions": transitions,
        "state_counts": state_counts,
        "state_pct": state_pct,
        "total_time": total_time,
        "time_in_state": time_in_state,
        "time_pct": time_pct,
    }


def compute_summary(store):
    """Return ``{task_name: summary_dict}`` for every task in ``store``."""
    summary = {}
    for task_name, states in store.task_states.items():
        timestamps = store.task_timestamps.get(task_name, [])
        summary[task_name] = _task_summary(timestamps, states)
    return summary


def format_summary(summary):
    """Render :func:`compute_summary` output as a human-readable table."""
    if not summary:
        return "No task data captured."

    lines = []
    header = f"{'Task':<14}{'Samples':>8}{'Transitions':>13}  State distribution (by samples)"
    lines.append(header)
    lines.append("-" * len(header))
    for task_name in sorted(summary):
        s = summary[task_name]
        dist = ", ".join(
            f"{state} {s['state_pct'][state]:.0f}%"
            for state in _ALL_STATES
            if s["state_counts"].get(state, 0) > 0
        )
        lines.append(
            f"{task_name:<14}{s['samples']:>8}{s['transitions']:>13}  {dist}"
        )
    return "\n".join(lines)
