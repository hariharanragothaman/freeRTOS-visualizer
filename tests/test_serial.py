import pytest
from unittest.mock import MagicMock

import re
from visualize import parse_serial_line, state_dict


def parse_serial_line(line):
    match = re.search(r"Task:(\S+),State:(\d+)", line)
    if match:
        task_name = match.group(1)
        task_state = state_dict.get(match.group(2), 'Unknown')
        return task_name, task_state
    return None


def test_parse_serial_line():
    line = "Task:Task1,State:0"
    task_name, task_state = parse_serial_line(line)
    assert task_name == "Task1"
    assert task_state == "Running"

    line_invalid = "Invalid Line"
    result = parse_serial_line(line_invalid)
    assert result is None
