from unittest.mock import patch, MagicMock

import pytest

from local_build.config import (
    load_distribution_choices,
    load_distributions,
    determine_build_tags,
)
from local_build.context import BuildContext
from local_build.exceptions import TerminateApp


@patch("local_build.config._load_distributions_utils")
def test_load_distribution_choices_success(mock_load):
    mock_load.return_value = {
        "dist1": {},
        "dist2": {},
    }
    choices, data = load_distribution_choices()
    assert sorted(choices) == ["dist1", "dist2"]
    assert data == mock_load.return_value


@patch("local_build.config._load_distributions_utils")
def test_load_distribution_choices_file_not_found(mock_load):
    mock_load.side_effect = FileNotFoundError()
    with pytest.raises(TerminateApp):
        load_distribution_choices()


@patch("local_build.config._load_distributions_utils")
def test_load_distribution_choices_other_error(mock_load):
    mock_load.side_effect = Exception("fail")
    with pytest.raises(TerminateApp):
        load_distribution_choices()


@patch("local_build.config._load_distributions_utils")
def test_load_distributions_success(mock_load):
    mock_load.return_value = {"dist": {}}
    ctx = BuildContext(
        distribution="dist",
        architecture="amd64",
        upstream_repo="repo",
        upstream_ref="ref",
        layer_name="layer",
        runtimes="python3.8",
        skip_publish=False,
        verbose=False,
        public=False,
        keep_temp=False,
    )
    updated_ctx = load_distributions(ctx)
    assert updated_ctx.distributions_data == {"dist": {}}


@patch("local_build.config._load_distributions_utils")
def test_load_distributions_error(mock_load):
    mock_load.side_effect = Exception("fail")
    ctx = BuildContext(
        distribution="dist",
        architecture="amd64",
        upstream_repo="repo",
        upstream_ref="ref",
        layer_name="layer",
        runtimes="python3.8",
        skip_publish=False,
        verbose=False,
        public=False,
        keep_temp=False,
    )
    with pytest.raises(TerminateApp):
        load_distributions(ctx)


@patch("local_build.config.resolve_build_tags")
def test_determine_build_tags_success(mock_resolve):
    mock_resolve.return_value = ["tag1", "tag2"]
    ctx = BuildContext(
        distribution="dist",
        architecture="amd64",
        upstream_repo="repo",
        upstream_ref="ref",
        layer_name="layer",
        runtimes="python3.8",
        skip_publish=False,
        verbose=False,
        public=False,
        keep_temp=False,
    )
    ctx.distributions_data = {"dist": {"buildtags": ["tag1", "tag2"]}}
    tracker = MagicMock()
    updated_ctx = determine_build_tags(ctx, tracker)
    assert updated_ctx.build_tags_string == "tag1,tag2"


@patch("local_build.config.resolve_build_tags")
def test_determine_build_tags_error(mock_resolve):
    mock_resolve.side_effect = Exception("fail")
    ctx = BuildContext(
        distribution="dist",
        architecture="amd64",
        upstream_repo="repo",
        upstream_ref="ref",
        layer_name="layer",
        runtimes="python3.8",
        skip_publish=False,
        verbose=False,
        public=False,
        keep_temp=False,
    )
    ctx.distributions_data = {"dist": {"buildtags": ["tag1", "tag2"]}}
    tracker = MagicMock()
    with pytest.raises(TerminateApp):
        determine_build_tags(ctx, tracker)
