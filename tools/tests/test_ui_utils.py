
from scripts.otel_layer_utils.ui_utils import (
    format_elapsed_time,
    format_file_size,
    format_traceback,
)


def test_format_elapsed_time():
    assert format_elapsed_time(45) == "45.0s"
    assert format_elapsed_time(125) == "2m 5s"
    assert format_elapsed_time(3725) == "1h 2m 5s"
    assert format_elapsed_time(0) == "0.0s"
    assert format_elapsed_time(3600) == "1h 0m 0s"


def test_format_file_size():
    assert format_file_size(500) == "500 bytes"
    assert format_file_size(1500) == "1.5 KB"
    assert format_file_size(1500000) == "1.43 MB"
    assert format_file_size(1500000000) == "1.40 GB"


def test_format_traceback_simple():
    try:
        raise ValueError("Test error")
    except Exception as e:
        tb_str = format_traceback(e)
        # The formatted traceback should include the error type and message
        assert "ValueError" in tb_str
        assert "Test error" in tb_str
