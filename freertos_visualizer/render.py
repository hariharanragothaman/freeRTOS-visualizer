"""Matplotlib rendering helpers shared by the GUI and the demo recorder.

These functions draw onto a provided matplotlib ``Axes``; they do not depend on
PyQt5. Keeping the drawing logic here lets the live GUI, the headless timeline
example, and the GIF recorder all share the exact same visuals — and lets the
rendering be unit-tested with the non-interactive Agg backend.

``matplotlib`` is imported lazily by callers, so importing this module (and the
package) never forces a matplotlib dependency on headless/CI environments that
only run the core logic tests.
"""

from freertos_visualizer.timeline import STATE_COLORS, compute_segments, state_color
from freertos_visualizer.visualize import STATE_DICT

_WAITING_TEXT = "Waiting for task data..."


def draw_bar_chart(ax, store):
    """Draw the current-state bar chart for ``store`` onto ``ax``."""
    ax.clear()
    tasks = list(store.task_states.keys())
    if not tasks:
        ax.set_title("Current Task States")
        ax.text(0.5, 0.5, _WAITING_TEXT, ha="center", va="center")
        return

    state_labels = list(STATE_DICT.values())
    states = [store.task_states[task][-1] for task in tasks]
    values = [
        (state_labels.index(state) + 1) if state in state_labels else 0
        for state in states
    ]
    colors = [state_color(state) for state in states]

    bars = ax.bar(tasks, values, color=colors)
    ax.set_ylim(0, len(STATE_DICT) + 1)
    ax.set_ylabel("Task State")
    ax.set_title("Current Task States")
    ax.set_yticks(range(0, len(STATE_DICT) + 1))
    ax.set_yticklabels(["Unknown"] + state_labels)

    for bar, state in zip(bars, states):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.1,
            state,
            ha="center",
            va="bottom",
        )
    return bars


def draw_timeline(ax, store, row_height=9, row_step=10):
    """Draw a Gantt-style task-state timeline for ``store`` onto ``ax``."""
    from matplotlib.patches import Patch

    ax.clear()
    segments = compute_segments(store)
    tasks = list(segments.keys())
    if not tasks:
        ax.set_title("Task State Timeline")
        ax.text(0.5, 0.5, _WAITING_TEXT, ha="center", va="center")
        return

    for idx, task in enumerate(tasks):
        spans = segments[task]
        xranges = [(start, max(end - start, 0.0)) for (start, end, _s) in spans]
        colors = [state_color(state) for (_a, _b, state) in spans]
        ax.broken_barh(xranges, (idx * row_step, row_height), facecolors=colors)

    ax.set_yticks([idx * row_step + row_height / 2 for idx in range(len(tasks))])
    ax.set_yticklabels(tasks)
    ax.set_xlabel("Time (s)")
    ax.set_title("Task State Timeline")
    ax.legend(
        handles=[Patch(color=color, label=state) for state, color in STATE_COLORS.items()],
        loc="upper right",
        fontsize="small",
        ncol=len(STATE_COLORS),
    )
