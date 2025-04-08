from unittest.mock import patch, MagicMock
from pathlib import Path

from local_build.upstream import (
    clone_repository,
    determine_upstream_version,
    cleanup_temp_dir,
)


@patch("local_build.upstream.run_command")
def test_clone_repository_integration(
    mock_run, mock_build_context, mock_tracker, temp_test_dir
):
    mock_run.return_value = MagicMock(returncode=0)
    # Simulate the clone by creating the directory structure
    temp_clone = temp_test_dir / "upstream"
    temp_clone.mkdir()
    collector_dir = temp_clone / "collector"
    collector_dir.mkdir()
    (collector_dir / "Makefile").write_text("# Mock Makefile\n")
    (collector_dir / "VERSION").write_text("v0.42.0\n")
    # Patch determine_upstream_version to avoid running make
    with patch("local_build.upstream.determine_upstream_version") as mock_determine:
        mock_determine.return_value = mock_build_context
        mock_build_context.set_temp_dir(str(temp_clone))
        result = clone_repository(mock_build_context, mock_tracker)
    # The clone_repository creates its own temp dir, so just check it exists
    assert Path(result.temp_upstream_dir).is_dir()
    mock_run.assert_called_once()
    assert "git" in mock_run.call_args[0][0]


@patch("local_build.upstream.run_command")
def test_determine_upstream_version_integration(
    mock_run, mock_build_context, mock_tracker, mock_upstream_repo
):
    mock_run.return_value = MagicMock(returncode=0)
    mock_build_context.set_temp_dir(str(mock_upstream_repo))
    result = determine_upstream_version(mock_build_context, mock_tracker)
    assert result.upstream_version == "v0.42.0"
    mock_tracker.start_step.assert_called_with(1)
    mock_tracker.complete_step.assert_called_with(1, "Version: v0.42.0")


def test_cleanup_temp_dir(mock_build_context, mock_upstream_repo):
    mock_build_context.set_temp_dir(str(mock_upstream_repo))
    mock_build_context.keep_temp = False
    cleanup_temp_dir(mock_build_context)
    assert not Path(mock_upstream_repo).exists()
