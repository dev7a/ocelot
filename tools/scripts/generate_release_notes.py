#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "boto3",
#     "click",
#     "requests",
# ]
# ///
"""
Generate markdown release notes for a specific layer distribution and version
by querying the DynamoDB metadata store.
"""

import sys
import click

from botocore.exceptions import ClientError

# Import DynamoDB utilities
from otel_layer_utils.dynamodb_utils import DYNAMODB_TABLE_NAME, query_by_distribution
from otel_layer_utils.regions_utils import get_region_info, get_wide_region


def _get_latest_aws_layer_versions(layer_list: list) -> list:
    """Filters a list of layer items to return only the latest AWS layer version for each base ARN."""
    latest_versions_map = {}
    for item in layer_list:
        full_arn = item.get("layer_arn")
        if not full_arn or full_arn == "N/A":
            print(f"Skipping item with invalid ARN in _get_latest_aws_layer_versions: {item}", file=sys.stderr)
            continue
        try:
            arn_parts = full_arn.split(':')
            if len(arn_parts) < 8:
                raise ValueError("ARN does not have enough parts to extract version.")
            base_arn = ":".join(arn_parts[:-1])
            aws_layer_version_num = int(arn_parts[-1])
        except (ValueError, IndexError) as e:
            print(f"Could not parse AWS layer version from ARN '{full_arn}' in _get_latest_aws_layer_versions: {e}. Skipping.", file=sys.stderr)
            continue

        # Store the parsed version number with the item for comparison
        item_with_parsed_version = dict(item)
        item_with_parsed_version['_aws_layer_version_num'] = aws_layer_version_num

        current_max_item = latest_versions_map.get(base_arn)
        if not current_max_item or aws_layer_version_num > current_max_item['_aws_layer_version_num']:
            latest_versions_map[base_arn] = item_with_parsed_version
    
    return list(latest_versions_map.values())


def generate_notes(distribution: str, collector_version: str, build_tags: str):
    """Queries DynamoDB and generates markdown release notes."""

    print(
        f"Querying DynamoDB table '{DYNAMODB_TABLE_NAME}' for distribution={distribution} using GSI 'distribution-index'...",
        file=sys.stderr,
    )

    # Use the GSI to query directly by distribution (sk)
    try:
        items = query_by_distribution(distribution)
        print(
            f"Found {len(items)} raw items for distribution. Filtering for collector version '{collector_version}'...",
            file=sys.stderr,
        )

        # Filter results in Python for the specific collector version
        filtered_items = [
            item
            for item in items
            if item.get("collector_version_input") == collector_version
        ]
    except ClientError as e:
        print(
            f"Error: Failed querying DynamoDB GSI for distribution '{distribution}': {e}",
            file=sys.stderr,
        )
        # Depending on requirements, might want to exit or return partial notes
        return f"# Error\n\nFailed to query layer metadata from DynamoDB: {e}"
    except Exception as e:
        print(
            f"Error: An unexpected error occurred during DynamoDB query: {e}",
            file=sys.stderr,
        )
        return f"# Error\n\nAn unexpected error occurred while querying DynamoDB: {e}"

    print(
        f"Found {len(filtered_items)} items matching the collector version.",
        file=sys.stderr,
    )

    # Get region information
    region_display_map = get_region_info()

    # Attempt to get distribution_description from the first filtered item
    dist_description_from_db = None
    if filtered_items:
        # All items should have the same distribution_description if they match the distribution
        # and collector_version, and if the publisher script populated it.
        dist_description_from_db = filtered_items[0].get("distribution_description")

    # --- Generate Markdown Body ---
    # Use literal \n for multi-line strings passed to gh release create --notes
    body_lines = []
    body_lines.append(
        f"## Release Details for {distribution} - Collector {collector_version}\n"
    )

    if dist_description_from_db:
        body_lines.append(f"### Distribution Description\n")
        body_lines.append(f"> {dist_description_from_db}\n\n") # Using blockquote for description

    body_lines.append("### Build Tags Used:\n")
    if build_tags:
        # Simple comma split and format as list
        tags_list = [
            f"- `{tag.strip()}`" for tag in build_tags.split(",") if tag.strip()
        ]
        if tags_list:
            body_lines.extend(tags_list)
        else:
            body_lines.append("- Default (no specific tags identified)")
    else:
        body_lines.append("- Default (no specific tags)")
    body_lines.append("\n")  # Add blank line for spacing

    body_lines.append("### Layer ARNs by Region:\n")
    if not filtered_items:
        body_lines.append(
            "No matching layers found in the metadata store for this specific version and distribution.\n"
        )
    else:
        # Sort and group items
        sorted_items = sorted(
            filtered_items,
            key=lambda x: (
                get_wide_region(x.get("region", "zzzz")),
                x.get("region", "zzzz"),
                x.get("architecture", "zzzz"),
            ),
        )

        # Group by wide region and region
        wide_regions = {}
        for item in sorted_items:
            region = item.get("region", "unknown")
            wide_region = get_wide_region(region)

            if wide_region not in wide_regions:
                wide_regions[wide_region] = {}

            if region not in wide_regions[wide_region]:
                wide_regions[wide_region][region] = {"amd64": [], "arm64": []}

            arch = item.get("architecture", "unknown")
            if arch in ["amd64", "arm64"]:
                wide_regions[wide_region][region][arch].append(item)

        # Generate tables with badges
        for wide_region_name in sorted(wide_regions.keys()):
            body_lines.append("<table>")
            # Wide region header
            body_lines.append(
                f'<tr><td colspan="3"><strong>{wide_region_name}</strong></td></tr>'
            )

            # Process each region in this wide region
            for region_name in sorted(wide_regions[wide_region_name].keys()):
                region_display_name = region_display_map.get(region_name, region_name)
                current_region_data = wide_regions[wide_region_name][region_name]

                # Region header
                body_lines.append(
                    f'<tr><td colspan="3">✅ <strong>{region_display_name}</strong></td></tr>'
                )

                # AMD64 layers - filter for latest AWS version
                latest_amd64_layers = _get_latest_aws_layer_versions(current_region_data["amd64"])
                if latest_amd64_layers:
                    for item in sorted(latest_amd64_layers, key=lambda x: x.get("layer_arn")):
                        arn = item.get("layer_arn", "N/A")
                        body_lines.append("<tr>")
                        body_lines.append(
                            f'<td><img src="https://img.shields.io/badge/{region_name.replace("-", "--")}-eee?style=for-the-badge" alt="{region_name}"></td>'
                        )
                        body_lines.append(
                            '<td><img src="https://img.shields.io/badge/arch-amd64-blue?style=for-the-badge" alt="amd64"></td>'
                        )
                        body_lines.append(f"<td>{arn}</td>")
                        body_lines.append("</tr>")

                # ARM64 layers - filter for latest AWS version
                latest_arm64_layers = _get_latest_aws_layer_versions(current_region_data["arm64"])
                if latest_arm64_layers:
                    for item in sorted(latest_arm64_layers, key=lambda x: x.get("layer_arn")):
                        arn = item.get("layer_arn", "N/A")
                        body_lines.append("<tr>")
                        body_lines.append(
                            f'<td><img src="https://img.shields.io/badge/{region_name.replace("-", "--")}-eee?style=for-the-badge" alt="{region_name}"></td>'
                        )
                        body_lines.append(
                            '<td><img src="https://img.shields.io/badge/arch-arm64-orange?style=for-the-badge" alt="arm64"></td>'
                        )
                        body_lines.append(f"<td>{arn}</td>")
                        body_lines.append("</tr>")

            body_lines.append("</table>")
            body_lines.append("")  # Add blank line between wide regions

    # Join lines with literal newline character for GitHub notes
    return "\n".join(body_lines)


@click.command()
@click.option(
    "--distribution",
    required=True,
    help="Layer distribution name (used as DynamoDB PK)",
)
@click.option(
    "--collector-version",
    required=True,
    help="Collector version string to filter layers (e.g., v0.119.0)",
)
@click.option(
    "--build-tags",
    default="",
    help="Comma-separated build tags used for this release",
)
def main(distribution, collector_version, build_tags):
    """Generate GitHub Release notes for custom Lambda layers."""
    notes = generate_notes(distribution, collector_version, build_tags)
    click.echo(notes)  # Print final markdown notes to stdout


if __name__ == "__main__":
    main()
