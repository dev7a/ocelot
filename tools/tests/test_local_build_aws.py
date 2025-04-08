from unittest.mock import patch, MagicMock

import pytest

from local_build.aws import (
    check_aws_credentials,
    get_aws_region,
    verify_credentials,
)
from local_build.context import BuildContext
from local_build.exceptions import TerminateApp


@patch("boto3.client")
def test_check_aws_credentials_success(mock_client):
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
    mock_client.return_value = mock_sts

    assert check_aws_credentials() is True


@patch("boto3.client")
def test_check_aws_credentials_failure(mock_client):
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.side_effect = Exception("fail")
    mock_client.return_value = mock_sts

    assert check_aws_credentials() is False


@patch("boto3.session.Session")
def test_get_aws_region_success(mock_session_cls):
    mock_session = MagicMock()
    mock_session.region_name = "us-east-1"
    mock_session_cls.return_value = mock_session

    assert get_aws_region() == "us-east-1"


@patch("boto3.session.Session")
def test_get_aws_region_failure(mock_session_cls):
    mock_session = MagicMock()
    mock_session.region_name = None
    mock_session_cls.return_value = mock_session

    with pytest.raises(TerminateApp):
        get_aws_region()


@patch("local_build.aws.get_aws_region", return_value="us-east-1")
@patch("local_build.aws.check_aws_credentials", return_value=True)
def test_verify_credentials_success(mock_check, mock_region):
    ctx = BuildContext(
        distribution="dist",
        architecture="amd64",
        upstream_repo="repo",
        upstream_ref="ref",
        layer_name="layer",
        runtimes="python3.8",
        skip_publish=False,
        verbose=True,
        public=False,
        keep_temp=False,
    )
    tracker = MagicMock()
    updated_ctx = verify_credentials(ctx, tracker)
    assert updated_ctx.aws_region == "us-east-1"
    assert updated_ctx.dynamodb_region == "us-east-1"


@patch("local_build.aws.get_aws_region", return_value="us-east-1")
@patch("local_build.aws.check_aws_credentials", return_value=False)
def test_verify_credentials_fail_creds(mock_check, mock_region):
    ctx = BuildContext(
        distribution="dist",
        architecture="amd64",
        upstream_repo="repo",
        upstream_ref="ref",
        layer_name="layer",
        runtimes="python3.8",
        skip_publish=False,
        verbose=True,
        public=False,
        keep_temp=False,
    )
    tracker = MagicMock()
    with pytest.raises(TerminateApp):
        verify_credentials(ctx, tracker)
