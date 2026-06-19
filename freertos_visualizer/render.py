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

_WAITING_TEXT = "Waiting for task data..."


def draw_bar_chart(ax, store):
    """Draw a current-state *status strip* for ``store`` onto ``ax``.

    Each task gets one equal-height cell coloured by its current state, with the
    state name as the label. Height is constant on purpose: the state is
    categorical, so colour + label carry the meaning and there is no magnitude
    axis to mislead (the old ``index+1`` height implied Suspended > Running).
    """
    ax.clear()
    tasks = list(store.task_states.keys())
    if not tasks:
        ax.set_title("Current Task States")
        ax.text(0.5, 0.5, _WAITING_TEXT, ha="center", va="center")
        return

    states = [store.task_states[task][-1] for task in tasks]
    colors = [state_color(state) for state in states]

    bars = ax.bar(tasks, [1] * len(tasks), color=colors)
    ax.set_ylim(0, 1)
    ax.set_yticks([])  # no magnitude axis: state is categorical
    ax.set_title("Current Task States")

    for bar, state in zip(bars, states):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            0.5,
            state,
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
        )
    return bars


def draw_timeline(ax, store, cache=None, row_height=9, row_step=10):
    """Draw a Gantt-style task-state timeline for ``store`` onto ``ax``.

    Pass a :class:`~freertos_visualizer.timeline.SegmentCache` as ``cache`` to
    reuse previously-computed spans across repaints instead of rebuilding the
    full history every frame.
    """
    from matplotlib.patches import Patch

    ax.clear()
    segments = cache.update(store) if cache is not None else compute_segments(store)
    tasks = list(segments.keys())
    if not tasks:
        ax.set_title("Task State Timeline")
        ax.text(0.5, 0.5, _WAITING_TEXT, ha="center", va="center")
        return

    # Stored timestamps are device ticks or host seconds; scale to display units
    # (seconds when the tick rate is known, otherwise raw ticks) and label the
    # axis to match — never claim seconds for a raw tick count.
    scale = getattr(store, "time_scale", 1.0)

    for idx, task in enumerate(tasks):
        spans = segments[task]
        xranges = [
            (start * scale, max((end - start) * scale, 0.0))
            for (start, end, _s) in spans
        ]
        colors = [state_color(state) for (_a, _b, state) in spans]
        ax.broken_barh(xranges, (idx * row_step, row_height), facecolors=colors)

    ax.set_yticks([idx * row_step + row_height / 2 for idx in range(len(tasks))])
    ax.set_yticklabels(tasks)
    ax.set_xlabel(getattr(store, "time_axis_label", "Time (s)"))
    ax.set_title("Task State Timeline")
    ax.legend(
        handles=[Patch(color=color, label=state) for state, color in STATE_COLORS.items()],
        loc="upper right",
        fontsize="small",
        ncol=len(STATE_COLORS),
    )
