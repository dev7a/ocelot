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
from otel_layer_utils.regions_utils import (
    get_region_info,
    get_wide_region
)


def generate_notes(distribution: str, collector_version: str, build_tags: str):
    """Queries DynamoDB and generates markdown release notes."""

    print(
        f"Querying DynamoDB table '{DYNAMODB_TABLE_NAME}' for distribution={distribution} using GSI sk-pk-index...",
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

    # --- Generate Markdown Body ---
    # Use literal \n for multi-line strings passed to gh release create --notes
    body_lines = []
    body_lines.append(
        f"## Release Details for {distribution} - Collector {collector_version}\n"
    )

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
        for wide_region in sorted(wide_regions.keys()):
            body_lines.append("<table>")
            # Wide region header
            body_lines.append(f'<tr><td colspan="3"><strong>{wide_region}</strong></td></tr>')
            
            # Process each region in this wide region
            for region in sorted(wide_regions[wide_region].keys()):
                region_display = region_display_map.get(region, region)
                region_data = wide_regions[wide_region][region]
                
                # Region header
                body_lines.append(f'<tr><td colspan="3">✅ <strong>{region_display}</strong></td></tr>')
                
                # AMD64 row
                if region_data["amd64"]:
                    for item in region_data["amd64"]:
                        arn = item.get("layer_arn", "N/A")
                        body_lines.append("<tr>")
                        body_lines.append(f'<td><img src="https://img.shields.io/badge/{region.replace("-", "--")}-eee?style=for-the-badge" alt="{region}"></td>')
                        body_lines.append('<td><img src="https://img.shields.io/badge/arch-amd64-blue?style=for-the-badge" alt="amd64"></td>')
                        body_lines.append(f"<td>{arn}</td>")
                        body_lines.append("</tr>")
                
                # ARM64 row
                if region_data["arm64"]:
                    for item in region_data["arm64"]:
                        arn = item.get("layer_arn", "N/A")
                        body_lines.append("<tr>")
                        body_lines.append(f'<td><img src="https://img.shields.io/badge/{region.replace("-", "--")}-eee?style=for-the-badge" alt="{region}"></td>')
                        body_lines.append('<td><img src="https://img.shields.io/badge/arch-arm64-orange?style=for-the-badge" alt="arm64"></td>')
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
