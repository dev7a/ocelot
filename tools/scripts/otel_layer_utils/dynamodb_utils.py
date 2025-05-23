"""
DynamoDB utility functions for Lambda Layer management.

This module centralizes DynamoDB operations used across various scripts
to maintain consistency and reduce code duplication.
"""

import boto3
from decimal import Decimal
from typing import Dict, List, Optional
from boto3.dynamodb.conditions import Key

# Common constants
DYNAMODB_TABLE_NAME = "ocelot-layers"
GSI_DISTRIBUTION_INDEX = "distribution-index"
GSI_BASE_LAYER_INDEX = "base-layer-index"


def get_table(region: str = None):
    """
    Get a reference to the DynamoDB table.

    Args:
        region: Optional AWS region where the table exists.
               If not provided, boto3 will use the region from:
               - AWS_REGION or AWS_DEFAULT_REGION environment variables
               - ~/.aws/config file

    Returns:
        boto3.resource.Table: DynamoDB table resource
    """
    # If region is None, boto3 will use environment variables or AWS config
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    return table


def deserialize_item(item: Dict) -> Dict:
    """
    Convert DynamoDB types (Decimal, Set) to standard Python types.

    Args:
        item: DynamoDB item with potential Decimal and Set values

    Returns:
        Dict: Item with standard Python types
    """
    if not item:
        return {}

    cleaned_item = {}
    for key, value in item.items():
        if isinstance(value, Decimal):
            # Convert Decimal to int if it's whole, otherwise float
            cleaned_item[key] = int(value) if value % 1 == 0 else float(value)
        elif isinstance(value, set):
            # Convert set to list for broader compatibility
            cleaned_item[key] = sorted(list(value))
        else:
            cleaned_item[key] = value
    return cleaned_item


def write_item(item: Dict, region: str = None) -> Dict:
    """
    Write an item to the DynamoDB table.

    Args:
        item: Item to write (must contain 'layer_arn' as HASH key)
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        Dict: Response from DynamoDB

    Raises:
        ClientError: If the write operation fails
        ValueError: If 'layer_arn' is missing from the item
    """
    if "layer_arn" not in item:
        raise ValueError("Item must contain 'layer_arn' attribute for the primary key")

    # Convert empty strings to None for DynamoDB (which doesn't accept empty strings)
    item_cleaned = {k: (None if v == "" else v) for k, v in item.items()}

    # Remove None values
    item_to_write = {k: v for k, v in item_cleaned.items() if v is not None}

    table = get_table(region)
    response = table.put_item(Item=item_to_write)
    return response


def get_item(layer_arn: str, region: str = None) -> Optional[Dict]:
    """
    Get an item from DynamoDB by its primary key (layer_arn).

    Args:
        layer_arn: The full ARN of the layer (primary HASH key)
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        Optional[Dict]: Item if found, None if not found

    Raises:
        ClientError: If the get operation fails
    """
    table = get_table(region)
    response = table.get_item(Key={"layer_arn": layer_arn})

    if "Item" in response:
        return deserialize_item(response["Item"])
    return None


def delete_item(layer_arn: str, region: str = None) -> bool:
    """
    Delete an item from DynamoDB by its primary key (layer_arn).

    Args:
        layer_arn: The full ARN of the layer (primary HASH key)
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        bool: True if deletion was successful or item didn't exist, False otherwise

    Raises:
        ClientError: If the delete operation fails
    """
    table = get_table(region)

    # Check if item exists first (using the new primary key structure)
    # This get_item call is mainly to confirm existence before delete for a friendlier return.
    # DynamoDB's delete_item itself is idempotent.
    existing_item_response = table.get_item(Key={"layer_arn": layer_arn})
    if "Item" not in existing_item_response:
        return True  # Nothing to delete, considered successful

    # Delete the item
    delete_response = table.delete_item(Key={"layer_arn": layer_arn})
    status_code = delete_response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return status_code == 200


def query_by_distribution(distribution_value: str, region: str = None) -> List[Dict]:
    """
    Query items by distribution using the GSI 'distribution-index'.

    Args:
        distribution_value: Distribution name to query
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        List[Dict]: List of items matching the distribution

    Raises:
        ClientError: If the query operation fails
    """
    table = get_table(region)
    items = []
    last_evaluated_key = None

    while True:
        query_args = {
            "IndexName": GSI_DISTRIBUTION_INDEX,
            "KeyConditionExpression": Key("distribution").eq(distribution_value),
        }
        if last_evaluated_key:
            query_args["ExclusiveStartKey"] = last_evaluated_key

        response = table.query(**query_args)

        for item in response.get("Items", []):
            items.append(deserialize_item(item))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items


def query_by_base_layer_arn(
    base_layer_arn_value: str,
    region: str = None,
    sort_ascending: bool = False,
    limit: Optional[int] = None,
) -> List[Dict]:
    """
    Query layer versions by base_layer_arn using the GSI 'base-layer-index'.
    Useful for finding the latest version of a layer.

    Args:
        base_layer_arn_value: The base ARN of the layer (without the numeric version suffix).
        region: Optional AWS region for DynamoDB.
        sort_ascending: If True, sorts by version number in ascending order.
                        If False (default), sorts in descending order (latest versions first).
        limit: Optional maximum number of items to return.

    Returns:
        List[Dict]: List of layer versions matching the base_layer_arn.

    Raises:
        ClientError: If the query operation fails.
    """
    table = get_table(region)
    items = []
    last_evaluated_key = None

    while True:
        query_args = {
            "IndexName": GSI_BASE_LAYER_INDEX,
            "KeyConditionExpression": Key("base_layer_arn").eq(base_layer_arn_value),
            "ScanIndexForward": sort_ascending,
        }
        if limit is not None and not last_evaluated_key:
            if limit is not None:
                query_args["Limit"] = limit

        if last_evaluated_key:
            query_args["ExclusiveStartKey"] = last_evaluated_key

        response = table.query(**query_args)

        for item in response.get("Items", []):
            items.append(deserialize_item(item))
            if limit is not None and len(items) >= limit:
                last_evaluated_key = None
                break 
        
        if limit is not None and len(items) >= limit:
            break

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items


def scan_items(filter_expression=None, region: str = None) -> List[Dict]:
    """
    Scan the DynamoDB table, optionally with a filter expression.

    Args:
        filter_expression: Optional DynamoDB filter expression
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        List[Dict]: List of items from the scan

    Raises:
        ClientError: If the scan operation fails
    """
    table = get_table(region)
    items = []
    last_evaluated_key = None

    while True:
        scan_args = {}
        if filter_expression:
            scan_args["FilterExpression"] = filter_expression
        if last_evaluated_key:
            scan_args["ExclusiveStartKey"] = last_evaluated_key

        response = table.scan(**scan_args)

        for item in response.get("Items", []):
            items.append(deserialize_item(item))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items


def get_all_items(region: str = None) -> List[Dict]:
    """
    Get all items from the DynamoDB table.

    Args:
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        List[Dict]: All items in the table
    """
    return scan_items(region=region)
