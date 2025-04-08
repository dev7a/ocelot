import os
import tempfile
import json


from scripts.otel_layer_utils.github_utils import set_github_output


def test_set_github_output_simple_value():
    with tempfile.NamedTemporaryFile("r+", delete=False) as tmp:
        os.environ["GITHUB_OUTPUT"] = tmp.name
        success = set_github_output("MY_VAR", "hello world")
        tmp.seek(0)
        content = tmp.read()
    assert success
    assert "MY_VAR=hello world" in content


def test_set_github_output_multiline_string():
    multiline = "line1\nline2\nline3"
    with tempfile.NamedTemporaryFile("r+", delete=False) as tmp:
        os.environ["GITHUB_OUTPUT"] = tmp.name
        success = set_github_output("MULTI", multiline)
        tmp.seek(0)
        content = tmp.read()
    assert success
    assert "MULTI<<" in content
    assert "line1\nline2\nline3" in content


def test_set_github_output_complex_value():
    data = {"foo": [1, 2, 3], "bar": "baz"}
    with tempfile.NamedTemporaryFile("r+", delete=False) as tmp:
        os.environ["GITHUB_OUTPUT"] = tmp.name
        success = set_github_output("COMPLEX", data)
        tmp.seek(0)
        content = tmp.read()
    assert success
    # Should contain JSON string
    assert json.dumps(data) in content


def test_set_github_output_env_not_set(monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    # Should return False, not raise or exit
    result = set_github_output("FOO", "bar", fail_on_error=False)
    assert result is False
