from unittest.mock import patch, MagicMock

from local_build.build import build_layer


@patch("local_build.build.run_command")
def test_build_layer_integration(
    mock_run, mock_build_context, mock_tracker, temp_test_dir
):
    mock_run.return_value = MagicMock(returncode=0)
    mock_build_context.distribution = "test-dist"
    mock_build_context.architecture = "x86_64"
    mock_build_context.upstream_version = "v0.42.0"
    mock_build_context.build_tags_string = "tag1,tag2"
    build_dir = temp_test_dir / "build"
    build_dir.mkdir(exist_ok=True)
    mock_build_context.build_dir = build_dir
    # Create expected output file
    layer_file = build_dir / "collector-x86_64-test-dist.zip"
    layer_file.write_text("mock zip content")
    result = build_layer(mock_build_context, mock_tracker)
    assert result.layer_file == layer_file
    assert result.layer_file_size > 0
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "build_extension_layer.py" in str(cmd)
    assert "--distribution" in cmd
    assert mock_build_context.distribution in cmd
    assert "--build-tags" in cmd
    assert mock_build_context.build_tags_string in cmd
