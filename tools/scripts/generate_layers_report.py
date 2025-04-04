#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "boto3",
#     "click",
# ]
# ///
"""
Generate a markdown report of all OpenTelemetry Lambda layers across AWS regions
by fetching metadata from a DynamoDB table.
"""

import fnmatch
from datetime import datetime
from typing import Dict, List
import sys
import click


# Import DynamoDB utilities
from otel_layer_utils.dynamodb_utils import (
    DYNAMODB_TABLE_NAME,
    query_by_distribution,
    scan_items,
)

# Known distributions to query (should match what's used as PK)
DISTRIBUTIONS = [
    "default",
    "minimal",
    "clickhouse",
    "clickhouse-otlphttp",
    "full",
    "custom",
]

# Known architectures to group by
ARCHITECTURES = ["amd64", "arm64", "unknown"]  # Add unknown as fallback


# --- Removed functions that parse names or call Lambda API ---
# get_distribution, get_architecture, get_version, check_aws_cli, fetch_layers


def fetch_layers_from_dynamodb(pattern: str = None) -> List[Dict]:
    """
    Fetch all layer metadata items from the DynamoDB table.
    Optionally filters items based on a glob pattern against the layer_arn.
    """
    all_items = []

    print(f"Querying DynamoDB table '{DYNAMODB_TABLE_NAME}' for layer metadata...")

    # If no pattern is provided, we'll get all items
    # If pattern is a specific distribution pattern, we can use query by distribution
    if (
        pattern
        and pattern.startswith("*")
        and pattern.endswith("*")
        and "*" not in pattern[1:-1]
    ):
        # This is likely just a distribution filter (e.g., "*clickhouse*")
        distribution = pattern[1:-1]  # Remove the asterisks
        if distribution in DISTRIBUTIONS:
            print(f"Using GSI 'sk-pk-index' to query for distribution: {distribution}")
            try:
                all_items = query_by_distribution(distribution)
                print(
                    f"Retrieved {len(all_items)} items for distribution '{distribution}'."
                )
                return all_items
            except Exception as e:
                print(
                    f"Error querying for distribution '{distribution}': {e}",
                    file=sys.stderr,
                )
                # Fall back to scan on error

    # Otherwise, use scan for more complex patterns or all items
    print("Using scan operation to retrieve all items")
    try:
        # Get all items (already deserialized)
        all_items = scan_items()
    except Exception as e:
        print(f"Error scanning DynamoDB table: {e}", file=sys.stderr)

    print(f"Retrieved {len(all_items)} total items from DynamoDB.")

    # Optional filtering based on pattern
    if pattern:
        filtered_items = [
            item
            for item in all_items
            if "layer_arn" in item and fnmatch.fnmatch(item["layer_arn"], pattern)
        ]
        print(
            f"Filtered down to {len(filtered_items)} items matching pattern: {pattern}"
        )
        return filtered_items
    else:
        return all_items


def process_dynamodb_items(items: List[Dict]) -> Dict:
    """
    Process the list of items fetched from DynamoDB and group them by
    distribution and architecture for the report.
    """
    layers_by_dist_arch = {}

    for item in items:
        # Items are already deserialized by our utility functions
        distribution = item.get("distribution", "unknown")
        architecture = item.get("architecture", "unknown")
        region = item.get("region", "unknown")
        layer_arn = item.get("layer_arn", "N/A")  # Use layer_arn attribute directly
        version = item.get("layer_version_str", "unknown")  # Use stored version string
        timestamp = item.get("publish_timestamp", "Unknown")  # Use stored timestamp

        # Ensure architecture is in our known list, default to unknown
        if architecture not in ARCHITECTURES:
            architecture = "unknown"

        key = f"{distribution}:{architecture}"
        if key not in layers_by_dist_arch:
            layers_by_dist_arch[key] = []

        layers_by_dist_arch[key].append(
            {
                "region": region,
                "arn": layer_arn,
                "version": version,
                "timestamp": timestamp,
            }
        )

    print(
        f"Processed items into {len(layers_by_dist_arch)} distribution/architecture groups."
    )
    return layers_by_dist_arch


def generate_report(
    layers_by_dist_arch: Dict, output_file: str = "LAYERS.md", pattern: str = None
):
    """
    Generate a markdown report from the processed layer information.
    (Signature and core logic remain largely the same)
    """
    with open(output_file, "w") as f:
        f.write("# OpenTelemetry Lambda Layers Report\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if pattern:
            f.write(f"Filtered by pattern (applied post-fetch): `{pattern}`\n\n")
        else:
            f.write(f"Source: DynamoDB table '{DYNAMODB_TABLE_NAME}'\n\n")

        f.write(
            "This report lists all OpenTelemetry Lambda layers available across AWS regions, based on metadata stored in DynamoDB.\n\n"
        )

        f.write("## Available Layers by Distribution\n\n")

        if not layers_by_dist_arch:
            f.write(
                "No layer metadata found in DynamoDB matching the specified criteria.\n\n"
            )
        else:
            # Use the predefined order of distributions
            sorted_distributions = [
                d
                for d in DISTRIBUTIONS
                if any(k.startswith(f"{d}:") for k in layers_by_dist_arch)
            ]

            for dist in sorted_distributions:
                f.write(f"### {dist} Distribution\n\n")

                # Use predefined order of architectures
                sorted_architectures = [
                    a for a in ARCHITECTURES if f"{dist}:{a}" in layers_by_dist_arch
                ]

                for arch in sorted_architectures:
                    key = f"{dist}:{arch}"
                    if layers_by_dist_arch[key]:  # Check if list is not empty
                        f.write(f"#### {arch} Architecture\n\n")
                        f.write(
                            "| Region | Layer ARN | Version | Published (DB Timestamp) |\n"
                        )  # Updated header
                        f.write(
                            "|--------|-----------|---------|-------------------------|"
                        )

                        # Sort by region for consistent output
                        # Use ?.get('timestamp', '') to handle potential missing timestamp safely
                        sorted_layers = sorted(
                            layers_by_dist_arch[key],
                            key=lambda x: (x.get("region", ""), x.get("timestamp", "")),
                        )

                        for layer in sorted_layers:
                            # Format timestamp nicely if possible (assuming ISO format)
                            ts = layer.get("timestamp", "Unknown")
                            try:
                                # Attempt to parse and format
                                dt_obj = datetime.fromisoformat(
                                    ts.replace("Z", "+00:00")
                                )
                                formatted_ts = dt_obj.strftime("%Y-%m-%dT%H:%M:%S%Z")
                            except (ValueError, AttributeError):
                                formatted_ts = (
                                    ts  # Keep original if not parsable ISO format
                                )

                            f.write(
                                f"\n| {layer.get('region', '?')} | `{layer.get('arn', 'N/A')}` | {layer.get('version', '?')} | {formatted_ts} |"
                            )

                        f.write("\n\n")  # Ensure newline after table

        f.write("## Usage Instructions\n\n")
        f.write(
            "To use a layer in your Lambda function, add the ARN to your function's configuration:\n\n"
        )
        f.write("```bash\n")
        f.write(
            "aws lambda update-function-configuration --function-name YOUR_FUNCTION --layers ARN_FROM_TABLE\n"
        )
        f.write("```\n\n")
        f.write(
            "For more information, see the [documentation](https://github.com/open-telemetry/opentelemetry-lambda).\n"
        )

    print(f"Report generated and saved to {output_file}")


@click.command()
@click.option(
    "--pattern",
    default=None,
    help="Glob pattern to filter layers based on ARN (e.g., '*clickhouse*amd64*')",
)
@click.option(
    "--output",
    default="LAYERS.md",
    help="Output file path for the markdown report",
)
def main(pattern, output):
    """Generate a markdown report of OpenTelemetry Lambda layers from DynamoDB"""

    # Fetch raw layer items from DynamoDB
    all_items = fetch_layers_from_dynamodb(pattern)

    # Process items into the structure needed for reporting
    layers_by_dist_arch = process_dynamodb_items(all_items)

    # Generate the report
    generate_report(layers_by_dist_arch, output, pattern)


if __name__ == "__main__":
    main()
