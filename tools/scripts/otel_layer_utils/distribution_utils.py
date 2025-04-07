#!/usr/bin/env python3
"""
distribution_utils.py

Utility functions for loading and processing the distributions.yaml configuration.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Set, Optional


class DistributionError(Exception):
    """Custom exception for distribution processing errors."""

    pass


def load_distributions(yaml_path: Path) -> Dict:
    """Loads distribution data from the specified YAML file."""
    if not yaml_path.is_file():
        raise DistributionError(f"Distribution YAML file not found at {yaml_path}")
    try:
        with open(yaml_path, "r") as f:
            distributions_data = yaml.safe_load(f)
        if not distributions_data:
            raise DistributionError(f"{yaml_path} is empty or invalid.")
        return distributions_data
    except yaml.YAMLError as e:
        raise DistributionError(f"Error parsing {yaml_path}: {e}")
    except Exception as e:
        raise DistributionError(f"Error reading {yaml_path}: {e}")


def resolve_build_tags(
    distribution_name: str, distributions_data: Dict, visited: Optional[Set[str]] = None
) -> List[str]:
    """
    Resolves the final list of build tags for a given distribution,
    handling inheritance via the 'base' property.

    Args:
        distribution_name: The name of the distribution to resolve.
        distributions_data: The loaded dictionary of all distributions.
        visited: A set to track visited distributions during recursion to detect cycles.

    Returns:
        A list of unique build tags.

    Raises:
        DistributionError: If the distribution is not found, the base is not found,
                           or a circular dependency is detected.
    """
    if visited is None:
        visited = set()

    if distribution_name in visited:
        raise DistributionError(
            f"Circular dependency detected involving distribution: {distribution_name}"
        )

    dist_info = distributions_data.get(distribution_name)
    if dist_info is None:
        raise DistributionError(
            f"Distribution '{distribution_name}' not found in configuration."
        )

    visited.add(distribution_name)

    base_tags: Set[str] = set()
    base_name = dist_info.get("base")

    if base_name:
        if not isinstance(base_name, str):
            raise DistributionError(
                f"Invalid 'base' value for distribution '{distribution_name}': Must be a string."
            )
        # Recursively resolve base tags
        try:
            base_tags_list = resolve_build_tags(
                base_name, distributions_data, visited.copy()
            )
            base_tags = set(base_tags_list)
        except DistributionError as e:
            # Add context to the error message
            raise DistributionError(
                f"Error resolving base '{base_name}' for distribution '{distribution_name}': {e}"
            )

    # Get tags specific to this distribution
    current_tags_list = dist_info.get("buildtags", [])
    if not isinstance(current_tags_list, list):
        raise DistributionError(
            f"Invalid 'buildtags' value for distribution '{distribution_name}': Must be a list."
        )

    current_tags: Set[str] = set(current_tags_list)

    # Merge unique tags: base tags + current tags
    final_tags = base_tags.union(current_tags)

    # Return sorted list for consistent output
    return sorted(list(final_tags))
