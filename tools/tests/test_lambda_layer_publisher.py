from scripts.lambda_layer_publisher import construct_layer_name


def test_construct_layer_name_with_explicit_version():
    name, arch, version = construct_layer_name(
        "otel-collector", "amd64", "clickhouse", "1.2.3", None, "prod"
    )
    assert name.endswith("-1_2_3-prod")
    assert arch == "x86_64"
    assert version == "1_2_3"


def test_construct_layer_name_with_collector_version():
    name, arch, version = construct_layer_name(
        "otel-collector", "arm64", "splunk", None, "v0.9.8", "dev"
    )
    assert name.endswith("-0_9_8-dev")
    assert arch == "arm64"
    assert version == "0_9_8"
