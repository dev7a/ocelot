from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from scripts.otel_layer_utils.dynamodb_utils import (
    deserialize_item,
    write_item,
    get_item,
    delete_item,
    query_by_distribution,
    scan_items,
)


def test_deserialize_item():
    item = {
        "int": Decimal("42"),
        "float": Decimal("3.14"),
        "set": set([1, 2, 3]),
        "str": "hello",
    }
    result = deserialize_item(item)
    assert result["int"] == 42
    assert abs(result["float"] - 3.14) < 1e-6
    assert sorted(result["set"]) == [1, 2, 3]
    assert result["str"] == "hello"


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_write_item_calls_put(mock_get_table):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    item = {"layer_arn": "arn:test:key", "foo": "bar"}
    write_item(item)
    mock_table.put_item.assert_called_once()
    args, kwargs = mock_table.put_item.call_args
    assert "Item" in kwargs
    assert kwargs["Item"]["layer_arn"] == "arn:test:key"
    assert kwargs["Item"]["foo"] == "bar"


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_write_item_missing_layer_arn_raises_value_error(mock_get_table):
    with pytest.raises(ValueError, match="Item must contain 'layer_arn' attribute for the primary key"):
        write_item({"foo": "bar"})


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_get_item_found(mock_get_table):
    mock_table = MagicMock()
    mock_item_from_db = {"layer_arn": "arn:test:key", "val": "x"}
    mock_table.get_item.return_value = {"Item": mock_item_from_db}
    mock_get_table.return_value = mock_table

    item = get_item("arn:test:key")
    assert item is not None
    assert item["layer_arn"] == "arn:test:key"
    assert item["val"] == "x"


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_get_item_not_found(mock_get_table):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    item = get_item("key")
    assert item is None


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_delete_item_exists(mock_get_table):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {"Item": {"layer_arn": "arn:test:delete_key"}}
    mock_table.delete_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_get_table.return_value = mock_table

    result = delete_item("arn:test:delete_key")
    assert result is True
    mock_table.delete_item.assert_called_once_with(Key={"layer_arn": "arn:test:delete_key"})


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_delete_item_not_exists(mock_get_table):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    result = delete_item("arn:test:non_existent_key")
    assert result is True
    mock_table.delete_item.assert_not_called()


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_query_by_distribution(mock_get_table):
    mock_table = MagicMock()
    # Simulate two pages
    mock_table.query.side_effect = [
        {
            "Items": [{"pk": "1"}, {"pk": "2"}],
            "LastEvaluatedKey": {"pk": "2"},
        },
        {
            "Items": [{"pk": "3"}],
        },
    ]
    mock_get_table.return_value = mock_table

    items = query_by_distribution("dist")
    assert len(items) == 3
    assert {"pk": "1"} in items
    assert {"pk": "3"} in items


@patch("scripts.otel_layer_utils.dynamodb_utils.get_table")
def test_scan_items(mock_get_table):
    mock_table = MagicMock()
    # Simulate two pages
    mock_table.scan.side_effect = [
        {
            "Items": [{"pk": "1"}, {"pk": "2"}],
            "LastEvaluatedKey": {"pk": "2"},
        },
        {
            "Items": [{"pk": "3"}],
        },
    ]
    mock_get_table.return_value = mock_table

    items = scan_items()
    assert len(items) == 3
    assert {"pk": "1"} in items
    assert {"pk": "3"} in items
