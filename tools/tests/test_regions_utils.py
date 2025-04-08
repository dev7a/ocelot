from unittest.mock import patch, MagicMock

from scripts.otel_layer_utils.regions_utils import (
    get_region_continent_mapping,
    get_region_info,
    get_wide_region,
)

MOCK_RESPONSE = {
    "1": {
        "type": "AWS Region",
        "code": "us-east-1",
        "name": "US East (N. Virginia)",
        "continent": "North America",
    },
    "2": {
        "type": "AWS Region",
        "code": "eu-west-1",
        "name": "EU (Ireland)",
        "continent": "Europe",
    },
    "3": {
        "type": "Edge Location",
        "code": "edge-1",
        "name": "Edge Location 1",
        "continent": "Global",
    },
}


@patch("scripts.otel_layer_utils.regions_utils.requests.get")
def test_get_region_continent_mapping(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    mock_get.return_value = mock_resp

    mapping = get_region_continent_mapping()
    assert mapping == {
        "us-east-1": "North America",
        "eu-west-1": "Europe",
    }


@patch("scripts.otel_layer_utils.regions_utils.requests.get")
def test_get_region_info_all(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    mock_get.return_value = mock_resp

    info = get_region_info()
    assert info == {
        "us-east-1": "US East (N. Virginia)",
        "eu-west-1": "EU (Ireland)",
    }


@patch("scripts.otel_layer_utils.regions_utils.requests.get")
def test_get_region_info_filtered(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    mock_get.return_value = mock_resp

    info = get_region_info(enabled_regions=["eu-west-1"])
    assert info == {
        "eu-west-1": "EU (Ireland)",
    }


@patch("scripts.otel_layer_utils.regions_utils.requests.get")
def test_get_wide_region_known(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    mock_get.return_value = mock_resp

    continent = get_wide_region("us-east-1")
    assert continent == "North America"


@patch("scripts.otel_layer_utils.regions_utils.requests.get")
def test_get_wide_region_unknown(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    mock_get.return_value = mock_resp

    continent = get_wide_region("ap-southeast-1")
    assert continent == "Other"
