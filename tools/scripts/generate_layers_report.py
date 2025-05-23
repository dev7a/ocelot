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

DISTRIBUTIONS = [
    "default",
    "minimal",
    "clickhouse",
    "clickhouse-otlphttp",
    "full",
    "custom",
]

ARCHITECTURES = ["amd64", "arm64", "unknown"]  # Add unknown as fallback


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
    This function passes through all AWS Lambda layer versions.
    """
    layers_by_dist_arch = {}

    for item in items:
        distribution = item.get("distribution", "unknown")
        architecture = item.get("architecture", "unknown")
        region = item.get("region", "unknown")
        layer_arn_full = item.get("layer_arn", "N/A")
        # This 'version' is the collector version string (e.g., v0.126.0)
        collector_version_str = item.get("layer_version_str", "unknown") 
        timestamp = item.get("publish_timestamp", "Unknown")

        if layer_arn_full == "N/A":
            print(f"Skipping item with missing 'layer_arn': {item}", file=sys.stderr)
            continue

        # Ensure architecture is in our known list, default to unknown
        if architecture not in ARCHITECTURES:
            architecture = "unknown"

        key = f"{distribution}:{architecture}"
        if key not in layers_by_dist_arch:
            layers_by_dist_arch[key] = []

        layers_by_dist_arch[key].append(
            {
                "region": region,
                "arn": layer_arn_full,  # Full ARN including AWS Layer Version suffix
                "version": collector_version_str,  # Collector version string
                "timestamp": timestamp,
            }
        )
    
    print(
        f"Processed and grouped {len(items)} items into {len(layers_by_dist_arch)} distribution/architecture groups."
    )
    return layers_by_dist_arch


def generate_report(
    layers_by_dist_arch: Dict, output_file: str = "LAYERS.md", pattern: str = None
):
    """
    Generate a markdown report from the processed layer information,
    ensuring only the latest AWS Lambda Layer version is shown for each unique layer.
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
            # Dynamically get all unique distribution names from the processed data
            # The keys in layers_by_dist_arch are like "distribution_name:architecture"
            found_distribution_names = sorted(list(set(
                k.split(':')[0] for k in layers_by_dist_arch.keys()
            )))

            if not found_distribution_names:
                 f.write("No layer distributions found in the processed data.\n\n")
            else:
                # We can still try to use the predefined DISTRIBUTIONS list for ordering,
                # and append any new ones found that are not in the predefined list.
                
                # Start with distributions that are in our predefined list and also found
                ordered_known_distributions = [
                    d for d in DISTRIBUTIONS if d in found_distribution_names
                ]
                
                # Add any newly found distributions that were not in our predefined list, sorted alphabetically
                newly_found_distributions = sorted([
                    d for d in found_distribution_names if d not in DISTRIBUTIONS
                ])
                
                # Combine them for the final processing order
                distributions_to_report = ordered_known_distributions + newly_found_distributions

                if not distributions_to_report:
                     f.write("No distributions to report after filtering (this should not happen if found_distribution_names was populated).\n\n")
                else:
                    for dist in distributions_to_report:
                        f.write(f"### {dist} Distribution\n\n")

                        # Use predefined order of architectures
                        # Ensure we only try to access architectures for the current 'dist'
                        sorted_architectures = [
                            a for a in ARCHITECTURES if f"{dist}:{a}" in layers_by_dist_arch
                        ]

                        for arch in sorted_architectures:
                            key = f"{dist}:{arch}"
                            # Check if key exists and the list is not empty
                            if key in layers_by_dist_arch and layers_by_dist_arch[key]:
                                f.write(f"#### {arch} Architecture\n\n")
                                
                                # --- Filter for latest AWS Lambda Layer Version ---
                                current_group_layers = layers_by_dist_arch[key]
                                latest_aws_versions_map = {} # Key: (base_arn, region), Value: layer_item

                                for layer_item in current_group_layers:
                                    full_arn = layer_item.get("arn")
                                    item_region = layer_item.get("region")

                                    if not full_arn or full_arn == "N/A":
                                        print(f"Skipping layer item with invalid ARN: {layer_item}", file=sys.stderr)
                                        continue
                                    
                                    try:
                                        arn_parts = full_arn.split(':')
                                        if len(arn_parts) < 7: # Basic check for ARN structure (e.g. arn:partition:service:region:account-id:resource-type/resource-id or :layer:name:version)
                                            # For layer ARNs, it's usually 7 or 8 parts if version is separate, or version is part of the 7th part.
                                            # e.g., arn:aws:lambda:us-east-1:123456789012:layer:my-layer:1 (8 parts)
                                            # or    arn:aws:lambda:us-east-1:123456789012:layer:my-layer (7 parts if no version in ARN explicitly listed in DB, though unlikely for this script)
                                            # We expect the version to be the last part.
                                            raise ValueError("ARN does not have enough parts to extract version.")

                                        base_arn = ":".join(arn_parts[:-1])
                                        aws_layer_version_num = int(arn_parts[-1])
                                    except (ValueError, IndexError) as e:
                                        print(f"Could not parse AWS layer version from ARN '{full_arn}': {e}. Skipping this item for 'latest' selection.", file=sys.stderr)
                                        continue # Skip if ARN not parsable for version

                                    unique_layer_key = (base_arn, item_region)
                                    
                                    # Store aws_layer_version_num in the item temporarily for comparison
                                    # This avoids modifying the original dict if it's shared, but for max(), it's fine.
                                    # We'll retrieve it from the stored item if this one becomes the candidate.
                                    
                                    current_max_item = latest_aws_versions_map.get(unique_layer_key)
                                    if not current_max_item:
                                        # Store a copy with the parsed version for future comparisons
                                        item_copy = dict(layer_item)
                                        item_copy['_aws_layer_version_num'] = aws_layer_version_num
                                        latest_aws_versions_map[unique_layer_key] = item_copy
                                    else:
                                        # Compare with the stored AWS layer version of the current max item
                                        if aws_layer_version_num > current_max_item['_aws_layer_version_num']:
                                            item_copy = dict(layer_item)
                                            item_copy['_aws_layer_version_num'] = aws_layer_version_num
                                            latest_aws_versions_map[unique_layer_key] = item_copy
                                
                                layers_to_display = list(latest_aws_versions_map.values())
                                # --- End filter ---

                                if not layers_to_display:
                                    f.write("No layers to display for this architecture after filtering.\n\n")
                                    continue


                                f.write(
                                    "| Region | Layer ARN | Version | Published (DB Timestamp) |\n"
                                )
                                f.write(
                                    "|--------|-----------|---------|-------------------------|"
                                )

                                # Sort the filtered list by region and timestamp for consistent output
                                sorted_layers = sorted(
                                    layers_to_display,
                                    key=lambda x: (x.get("region", ""), x.get("timestamp", "")),
                                )

                                for layer in sorted_layers:
                                    ts = layer.get("timestamp", "Unknown")
                                    try:
                                        dt_obj = datetime.fromisoformat(
                                            ts.replace("Z", "+00:00")
                                        )
                                        formatted_ts = dt_obj.strftime("%Y-%m-%dT%H:%M:%S%Z")
                                    except (ValueError, AttributeError):
                                        formatted_ts = ts

                                    # The 'version' field here is the collector_version_str
                                    f.write(
                                        f"\n| {layer.get('region', '?')} | `{layer.get('arn', 'N/A')}` | {layer.get('version', '?')} | {formatted_ts} |"
                                    )

                                f.write("\n\n")

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

    all_items = fetch_layers_from_dynamodb(pattern)
    layers_by_dist_arch = process_dynamodb_items(all_items)
    generate_report(layers_by_dist_arch, output, pattern)


if __name__ == "__main__":
    main()
