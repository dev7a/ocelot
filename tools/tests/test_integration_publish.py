from unittest.mock import patch, MagicMock
import os

from local_build.publish import publish_layer


@patch("local_build.publish.run_command")
def test_publish_layer_integration(
    mock_run, mock_build_context, mock_tracker, mock_layer_zip
):
    mock_build_context.aws_region = "us-west-2"
    mock_build_context.dynamodb_region = "us-west-2"
    mock_build_context.skip_publish = False
    mock_build_context.public = False
    mock_build_context.set_layer_file(mock_layer_zip, os.path.getsize(mock_layer_zip))
    mock_proc = MagicMock()
    mock_proc.stdout = (
        "Published Layer ARN: arn:aws:lambda:us-west-2:123456789012:layer:test-layer:1"
    )
    mock_env_vars = {
        "layer_arn": "arn:aws:lambda:us-west-2:123456789012:layer:test-layer:1"
    }
    mock_run.return_value = (mock_proc, mock_env_vars)
    result = publish_layer(mock_build_context, mock_tracker)
    assert (
        result.layer_arn == "arn:aws:lambda:us-west-2:123456789012:layer:test-layer:1"
    )
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "lambda_layer_publisher.py" in str(cmd)
    assert "--layer-name" in cmd
    assert "--region" in cmd
    assert mock_build_context.aws_region in cmd
    assert "--distribution" in cmd
    assert mock_build_context.distribution in cmd


def test_publish_layer_skipped(mock_build_context, mock_tracker):
    mock_build_context.skip_publish = True
    result = publish_layer(mock_build_context, mock_tracker)
    mock_tracker.complete_step.assert_called_with(4, "Skipped (not requested)")
    assert result == mock_build_context
