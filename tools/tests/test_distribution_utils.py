import yaml
from pathlib import Path

import pytest

from scripts.otel_layer_utils.distribution_utils import (
    load_distributions,
    resolve_build_tags,
    DistributionError,
)


def test_load_distributions_success(tmp_path):
    data = {"dist1": {"buildtags": ["tag1", "tag2"]}}
    yaml_path = tmp_path / "distributions.yaml"
    yaml_path.write_text(yaml.dump(data))
    loaded = load_distributions(yaml_path)
    assert loaded == data


def test_load_distributions_file_not_found():
    with pytest.raises(DistributionError):
        load_distributions(Path("/nonexistent/path.yaml"))


def test_load_distributions_invalid_yaml(tmp_path):
    yaml_path = tmp_path / "bad.yaml"
    # Write truly invalid YAML that causes a parse error
    yaml_path.write_text("invalid: [unclosed list")
    with pytest.raises(DistributionError):
        load_distributions(yaml_path)


def test_resolve_build_tags_simple():
    dists = {
        "dist1": {"buildtags": ["tag1", "tag2"]},
    }
    tags = resolve_build_tags("dist1", dists)
    assert set(tags) == {"tag1", "tag2"}


def test_resolve_build_tags_with_inheritance():
    dists = {
        "base": {"buildtags": ["tag1"]},
        "child": {"base": "base", "buildtags": ["tag2"]},
    }
    tags = resolve_build_tags("child", dists)
    assert set(tags) == {"tag1", "tag2"}


def test_resolve_build_tags_circular_dependency():
    dists = {
        "a": {"base": "b", "buildtags": ["tag1"]},
        "b": {"base": "a", "buildtags": ["tag2"]},
    }
    with pytest.raises(DistributionError):
        resolve_build_tags("a", dists)


def test_resolve_build_tags_missing_distribution():
    dists = {}
    with pytest.raises(DistributionError):
        resolve_build_tags("nonexistent", dists)


def test_resolve_build_tags_invalid_base_type():
    dists = {
        "dist": {"base": 123, "buildtags": ["tag1"]},
    }
    with pytest.raises(DistributionError):
        resolve_build_tags("dist", dists)


def test_resolve_build_tags_invalid_buildtags_type():
    dists = {
        "dist": {"buildtags": "notalist"},
    }
    with pytest.raises(DistributionError):
        resolve_build_tags("dist", dists)
