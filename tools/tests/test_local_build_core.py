from local_build.exceptions import TerminateApp
from local_build.context import BuildContext


def test_terminate_app_exception():
    e = TerminateApp(
        "Test error", exit_code=42, step_index=3, step_message="Step failed"
    )
    assert e.message == "Test error"
    assert e.exit_code == 42
    assert e.step_index == 3
    assert e.step_message == "Step failed"


def test_build_context_initialization_and_setters():
    ctx = BuildContext(
        distribution="dist",
        architecture="amd64",
        upstream_repo="repo",
        upstream_ref="ref",
        layer_name="layer",
        runtimes="python3.8",
        skip_publish=True,
        verbose=True,
        public=False,
        keep_temp=True,
    )
    assert ctx.distribution == "dist"
    assert ctx.architecture == "amd64"
    assert ctx.upstream_repo == "repo"
    assert ctx.upstream_ref == "ref"
    assert ctx.layer_name == "layer"
    assert ctx.runtimes == "python3.8"
    assert ctx.skip_publish is True
    assert ctx.verbose is True
    assert ctx.public is False
    assert ctx.keep_temp is True

    ctx.set_temp_dir("/tmp/testdir")
    assert ctx.temp_upstream_dir == "/tmp/testdir"

    ctx.set_upstream_version("v1.0.0")
    assert ctx.upstream_version == "v1.0.0"

    ctx.set_build_tags("tag1,tag2")
    assert ctx.build_tags_string == "tag1,tag2"

    data = {"dist": {"some": "data"}}
    ctx.set_distributions_data(data)
    assert ctx.distributions_data == data

    from pathlib import Path as P

    ctx.set_layer_file(P("/tmp/layer.zip"), 12345)
    assert ctx.layer_file == P("/tmp/layer.zip")
    assert ctx.layer_file_size == 12345

    ctx.set_layer_arn("arn:aws:lambda:region:account:layer:layername:1")
    assert ctx.layer_arn == "arn:aws:lambda:region:account:layer:layername:1"

    ctx.set_aws_region("us-east-1")
    assert ctx.aws_region == "us-east-1"

    ctx.set_dynamodb_region("us-west-2")
    assert ctx.dynamodb_region == "us-west-2"
