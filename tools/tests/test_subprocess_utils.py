import subprocess
import tempfile

import pytest
from unittest.mock import patch, MagicMock

from scripts.otel_layer_utils.subprocess_utils import run_command


@patch("subprocess.run")
def test_run_command_success(mock_run):
    mock_proc = subprocess.CompletedProcess(
        args=["echo", "hello"], returncode=0, stdout="output", stderr=""
    )
    mock_run.return_value = mock_proc

    result = run_command(["echo", "hello"], capture_output=True)
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 0


@patch("subprocess.run")
def test_run_command_failure_check_true(mock_run):
    mock_proc = subprocess.CompletedProcess(
        args=["false"], returncode=1, stdout="fail output", stderr="fail error"
    )
    mock_run.return_value = mock_proc

    with pytest.raises(subprocess.CalledProcessError):
        run_command(["false"], capture_output=True, check=True)


@patch("subprocess.run")
def test_run_command_failure_check_false(mock_run):
    mock_proc = subprocess.CompletedProcess(
        args=["false"], returncode=1, stdout="fail output", stderr="fail error"
    )
    mock_run.return_value = mock_proc

    result = run_command(["false"], capture_output=True, check=False)
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 1


@patch("subprocess.run")
def test_run_command_capture_github_env(mock_run):
    # Prepare fake subprocess result
    mock_proc = subprocess.CompletedProcess(
        args=["echo", "hi"], returncode=0, stdout="some output", stderr=""
    )
    mock_run.return_value = mock_proc

    # Prepare fake GitHub env files
    with (
        tempfile.NamedTemporaryFile("w+", delete=False) as env_file,
        tempfile.NamedTemporaryFile("w+", delete=False) as out_file,
    ):
        env_file.write("FOO=bar\n")
        env_file.flush()
        out_file.write("BAZ=qux\n")
        out_file.flush()

        # Patch tempfile.NamedTemporaryFile to return our files
        with patch("tempfile.NamedTemporaryFile") as mock_tmp:
            env_mock = MagicMock(name="env")
            env_mock.name = env_file.name
            out_mock = MagicMock(name="out")
            out_mock.name = out_file.name
            mock_tmp.side_effect = [env_mock, out_mock]
            # Also patch os.path.exists and os.path.getsize to simulate files exist
            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=10),
            ):
                proc, env_vars = run_command(
                    ["echo", "hi"],
                    capture_output=True,
                    capture_github_env=True,
                )
                assert isinstance(proc, subprocess.CompletedProcess)
                assert env_vars.get("FOO") == "bar"
                assert env_vars.get("BAZ") == "qux"

        # No cleanup needed: run_command deletes temp files
