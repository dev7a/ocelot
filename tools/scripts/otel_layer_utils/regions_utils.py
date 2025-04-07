#!/usr/bin/env python3
"""
Utilities for working with AWS regions.
Provides mapping between region codes, display names, and continent groups.
"""

import requests
from typing import Dict, List, Optional
from functools import lru_cache


@lru_cache(maxsize=1)
def get_region_continent_mapping() -> Dict[str, str]:
    """
    Get mapping of AWS region codes to their continent names from AWS API.

    Returns:
        Dict[str, str]: A mapping of region codes to continent names
                        (e.g., 'us-east-1': 'North America')
    """
    response = requests.get(
        "https://b0.p.awsstatic.com/locations/1.0/aws/current/locations.json",
        timeout=10,
    )
    data = response.json()

    mapping = {}
    for _, value in data.items():
        if (
            value.get("type") == "AWS Region"
            and "code" in value
            and "continent" in value
        ):
            mapping[value["code"]] = value["continent"]

    return mapping


def get_region_info(enabled_regions: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Get mapping of region codes to their human-readable names.

    Args:
        enabled_regions: Optional list of AWS region codes to filter by.
                         If None, all regions from the AWS locations API are returned.

    Returns:
        Dict[str, str]: A mapping of region codes to region names
                        (e.g., 'us-east-1': 'US East (N. Virginia)')
    """
    response = requests.get(
        "https://b0.p.awsstatic.com/locations/1.0/aws/current/locations.json",
        timeout=10,
    )
    data = response.json()

    region_info = {
        value["code"]: value["name"]
        for key, value in data.items()
        if value["type"] == "AWS Region"
    }

    if enabled_regions:
        return {
            code: name for code, name in region_info.items() if code in enabled_regions
        }

    return region_info


def get_wide_region(region_code: str) -> str:
    """
    Get the continent name for a specific AWS region.

    Args:
        region_code: AWS region code (e.g., 'us-east-1')

    Returns:
        str: Continent name (e.g., 'North America')
    """
    region_mapping = get_region_continent_mapping()
    return region_mapping.get(region_code, "Other")
