import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from freertos_visualizer.render import draw_bar_chart, draw_timeline  # noqa: E402
from freertos_visualizer.visualize import TaskStateStore  # noqa: E402


@pytest.fixture
def ax():
    fig, axes = plt.subplots()
    yield axes
    plt.close(fig)


def _store(samples):
    store = TaskStateStore()
    for ts, line in samples:
        store.ingest_line(line, timestamp=ts)
    return store


def test_bar_chart_empty_shows_waiting(ax):
    draw_bar_chart(ax, TaskStateStore())
    texts = [t.get_text() for t in ax.texts]
    assert "Waiting for task data..." in texts


def test_bar_chart_draws_one_bar_per_task(ax):
    store = _store([
        (0.0, "Task:A,State:0"),
        (1.0, "Task:B,State:1"),
        (2.0, "Task:A,State:2"),
    ])
    bars = draw_bar_chart(ax, store)
    assert len(bars) == 2  # tasks A and B
    assert ax.get_title() == "Current Task States"


def test_bar_chart_is_equal_height_status_strip(ax):
    # State is categorical: every cell is the same height (no magnitude axis).
    store = _store([(0.0, "Task:A,State:0"), (1.0, "Task:B,State:3")])
    bars = draw_bar_chart(ax, store)
    assert {round(b.get_height(), 6) for b in bars} == {1.0}
    assert list(ax.get_yticks()) == []


def test_bar_chart_labels_use_latest_state(ax):
    store = _store([(0.0, "Task:A,State:0"), (1.0, "Task:A,State:2")])
    draw_bar_chart(ax, store)
    labels = {t.get_text() for t in ax.texts}
    assert "Blocked" in labels  # latest state, not "Running"


def test_timeline_empty_shows_waiting(ax):
    draw_timeline(ax, TaskStateStore())
    texts = [t.get_text() for t in ax.texts]
    assert "Waiting for task data..." in texts


def test_timeline_has_row_per_task(ax):
    store = _store([
        (0.0, "Task:A,State:0"),
        (1.0, "Task:B,State:1"),
        (2.0, "Task:A,State:1"),
    ])
    draw_timeline(ax, store)
    assert ax.get_title() == "Task State Timeline"
    assert [lbl.get_text() for lbl in ax.get_yticklabels()] == ["A", "B"]


def test_timeline_axis_label_is_ticks_without_rate(ax):
    # Device ticks, no announced rate: axis must say "Device ticks", not seconds.
    store = TaskStateStore()
    store.ingest_line("Task:A,State:0,Tick:0")
    store.ingest_line("Task:A,State:1,Tick:100")
    draw_timeline(ax, store)
    assert ax.get_xlabel() == "Device ticks"


def test_timeline_axis_scales_to_seconds_with_rate(ax):
    # With TickRate the axis reads seconds and segments are scaled by 1/rate.
    store = TaskStateStore()
    store.ingest_line("TickRate:1000")
    store.ingest_line("Task:A,State:0,Tick:0")
    store.ingest_line("Task:A,State:1,Tick:2000")  # 2000 ticks = 2.0 s
    draw_timeline(ax, store)
    assert ax.get_xlabel() == "Time (s)"
    # The single span should span 0 -> 2.0 seconds, not 0 -> 2000.
    xmin, xmax = ax.get_xlim()
    assert xmax <= 10  # would be ~2000 if unscaled
