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
DYNAMODB_TABLE_NAME = "custom-collector-extension-layers"
GSI_NAME = "sk-pk-index"  # Global Secondary Index name


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
        item: Item to write (must contain pk and sk)
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        Dict: Response from DynamoDB

    Raises:
        ClientError: If the write operation fails
    """
    if "pk" not in item or "sk" not in item:
        raise ValueError("Item must contain 'pk' and 'sk' attributes")

    # Convert empty strings to None for DynamoDB (which doesn't accept empty strings)
    item_cleaned = {k: (None if v == "" else v) for k, v in item.items()}

    # Remove None values
    item_to_write = {k: v for k, v in item_cleaned.items() if v is not None}

    table = get_table(region)
    response = table.put_item(Item=item_to_write)
    return response


def get_item(pk: str, region: str = None) -> Optional[Dict]:
    """
    Get an item from DynamoDB by its primary key.

    Args:
        pk: Partition key value
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        Optional[Dict]: Item if found, None if not found

    Raises:
        ClientError: If the get operation fails
    """
    table = get_table(region)
    response = table.get_item(Key={"pk": pk})

    if "Item" in response:
        return deserialize_item(response["Item"])
    return None


def delete_item(pk: str, region: str = None) -> bool:
    """
    Delete an item from DynamoDB by its primary key.

    Args:
        pk: Partition key value
        region: Optional AWS region for DynamoDB.
                If not provided, boto3 will use the region from environment variables or AWS config.

    Returns:
        bool: True if deletion was successful or item didn't exist, False otherwise

    Raises:
        ClientError: If the delete operation fails
    """
    table = get_table(region)

    # Check if item exists first
    response = table.get_item(Key={"pk": pk})
    if "Item" not in response:
        return True  # Nothing to delete

    # Delete the item
    delete_response = table.delete_item(Key={"pk": pk})
    status_code = delete_response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return status_code == 200


def query_by_distribution(distribution: str, region: str = None) -> List[Dict]:
    """
    Query items by distribution using the GSI.

    Args:
        distribution: Distribution name to query
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
            "IndexName": GSI_NAME,
            "KeyConditionExpression": Key("sk").eq(distribution),
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
