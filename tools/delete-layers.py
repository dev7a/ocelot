#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "boto3",
#     "click",
#     "termcolor",
#     "yaspin",
# ]
# ///
"""
Interactive script to delete AWS Lambda layers matching a glob pattern across all regions.
This is a maintenance utility to clean up old or unneeded Lambda layers.

CAUTION: Use with care as layer deletion CANNOT be undone.
"""

import boto3
import fnmatch
import sys
import click
from botocore.exceptions import ClientError
from typing import Dict, List, Tuple
from yaspin import yaspin

# Import UI utilities from shared module
from scripts.otel_layer_utils.ui_utils import (
    header,
    subheader,
    status,
    info,
    success,
    error,
    warning,
    spinner,
    format_table,
    StepTracker,
    set_verbose_mode,
    debug,
)

# Import DynamoDB utilities
from scripts.otel_layer_utils.dynamodb_utils import delete_item

# List of regions to query - keep in sync with publish workflow
REGIONS = [
    "ca-central-1",
    "ca-west-1",
    "eu-central-1",
    "eu-central-2",
    "eu-north-1",
    "eu-south-1",
    "eu-south-2",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "us-east-1",
    "us-east-2",
    "us-west-2",
]


def check_aws_cli() -> bool:
    """
    Check if AWS credentials are configured properly.
    """
    try:
        # Create a boto3 session to check if credentials are available
        def check_credentials():
            session = boto3.Session()
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            return identity.get("Account")

        account_id = spinner("Checking AWS credentials", check_credentials)
        if account_id:
            success("AWS credentials are configured", f"Account: {account_id}")
            return True
        else:
            error("AWS credentials check failed", "No account ID returned")
            return False
    except ClientError as e:
        error("Error with AWS credentials", str(e))
        return False


def find_matching_layers(pattern: str) -> List[Dict]:
    """
    Find all Lambda layers that match the given glob pattern across all regions.
    Returns a list of dicts containing layer info.
    """
    matching_layers = []

    header("SEARCHING FOR LAYERS")
    status("Pattern", pattern)
    status("Regions", f"{len(REGIONS)} AWS regions")

    # Verify AWS credentials
    if not check_aws_cli():
        error(
            "AWS credentials not configured",
            "Please run 'aws configure' or set AWS environment variables.",
        )
        return matching_layers

    for region in REGIONS:
        with yaspin(text=f"Searching in {region}...") as sp:
            layers_found = 0
            try:
                # Create a Lambda client for the region
                lambda_client = boto3.client("lambda", region_name=region)

                # List all layers
                paginator = lambda_client.get_paginator("list_layers")

                for page in paginator.paginate():
                    for layer in page["Layers"]:
                        layer_name = layer["LayerName"]

                        # Check if the layer name matches the pattern
                        if fnmatch.fnmatch(layer_name, pattern):
                            # Get all versions of this layer
                            try:
                                versions_paginator = lambda_client.get_paginator(
                                    "list_layer_versions"
                                )
                                versions = []

                                for version_page in versions_paginator.paginate(
                                    LayerName=layer_name
                                ):
                                    for version in version_page["LayerVersions"]:
                                        versions.append(
                                            {
                                                "Version": version["Version"],
                                                "Arn": version["LayerVersionArn"],
                                                "CreatedDate": version.get(
                                                    "CreatedDate", "Unknown"
                                                ),
                                            }
                                        )

                                matching_layers.append(
                                    {
                                        "Name": layer_name,
                                        "Region": region,
                                        "Versions": versions,
                                    }
                                )

                                layers_found += 1

                            except ClientError as e:
                                sp.fail("✗")
                                error(
                                    f"Error getting versions for layer {layer_name}",
                                    str(e),
                                )

                if layers_found:
                    sp.text = f"Found {layers_found} layer(s) in {region}"
                    sp.ok("✓")
                else:
                    sp.text = f"No matching layers in {region}"
                    sp.ok("-")

            except ClientError as e:
                sp.fail("✗")
                error(f"Error searching in region {region}", str(e))

    return matching_layers


def delete_dynamodb_record(layer_arn: str) -> bool:
    """
    Delete a record from DynamoDB using the layer ARN as the primary key.

    Args:
        layer_arn: The ARN of the layer to delete from DynamoDB

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        return delete_item(pk=layer_arn)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ResourceNotFoundException":
            debug(f"DynamoDB record not found for {layer_arn}")
        elif error_code == "AccessDeniedException":
            debug(f"Access denied to DynamoDB for {layer_arn}")
        else:
            debug(f"DynamoDB error: {e}")
        return False
    except Exception as e:
        debug(f"Unexpected error deleting DynamoDB record: {e}")
        return False


def delete_layers(
    layers: List[Dict], dry_run: bool = False, skip_dynamodb: bool = False
) -> Tuple[int, int, int, int]:
    """
    Delete the specified layers and all their versions, including DynamoDB records.

    Args:
        layers: List of layer info dictionaries
        dry_run: If True, only simulate the deletion
        skip_dynamodb: If True, skip DynamoDB record deletion

    Returns:
        Tuple[int, int, int, int]: (lambda_success, lambda_failure, dynamo_success, dynamo_failure)
    """
    lambda_success = 0
    lambda_failure = 0
    dynamo_success = 0
    dynamo_failure = 0

    if not layers:
        warning("No layers to delete", "Nothing to do")
        return (0, 0, 0, 0)

    header("DELETING LAYERS")
    status("Mode", "DRY RUN" if dry_run else "ACTUAL DELETE")
    status("DynamoDB Cleanup", "Disabled" if skip_dynamodb else "Enabled")

    # Create a step tracker for the deletion process
    steps = []
    for layer in layers:
        region = layer["Region"]
        layer_name = layer["Name"]
        versions_count = len(layer["Versions"])
        steps.append(f"Delete {layer_name} ({versions_count} versions) in {region}")

    tracker = StepTracker(steps, title="Layer Deletion Steps")

    for idx, layer in enumerate(layers):
        region = layer["Region"]
        layer_name = layer["Name"]
        versions = layer["Versions"]

        tracker.start_step(idx)

        if dry_run:
            info(
                "[DRY RUN]",
                f"Would delete layer {layer_name} in {region} with {len(versions)} version(s)",
            )
            lambda_success += len(versions)

            if not skip_dynamodb:
                info(
                    "[DRY RUN]",
                    f"Would delete DynamoDB records for {len(versions)} version(s)",
                )
                dynamo_success += len(versions)

            tracker.complete_step(idx, "[DRY RUN] Deletion simulated")
            continue

        try:
            lambda_client = boto3.client("lambda", region_name=region)

            versions_success = 0
            versions_failed = 0
            dynamo_versions_success = 0
            dynamo_versions_failed = 0

            for version in versions:
                version_number = version["Version"]
                layer_arn = version["Arn"]

                # Delete Lambda layer version
                try:
                    with yaspin(
                        text=f"Deleting {layer_name} version {version_number} in {region}..."
                    ) as sp:
                        lambda_client.delete_layer_version(
                            LayerName=layer_name, VersionNumber=version_number
                        )
                        sp.ok("✓")

                    lambda_success += 1
                    versions_success += 1

                    # Delete DynamoDB record if requested
                    if not skip_dynamodb:
                        with yaspin(
                            text=f"Deleting DynamoDB record for {layer_arn}..."
                        ) as sp:
                            if delete_dynamodb_record(layer_arn):
                                sp.ok("✓")
                                dynamo_success += 1
                                dynamo_versions_success += 1
                            else:
                                sp.fail("✗")
                                dynamo_failure += 1
                                dynamo_versions_failed += 1

                except ClientError as e:
                    sp.fail("✗")
                    error(
                        f"Error deleting {layer_name} version {version_number} in {region}",
                        str(e),
                    )
                    lambda_failure += 1
                    versions_failed += 1

            # Update step tracker with a better formatted result message
            has_failures = versions_failed > 0 or (
                not skip_dynamodb and dynamo_versions_failed > 0
            )

            # Format a multi-line status message for better readability
            status_lines = []
            status_lines.append(
                f"Lambda Layer: {versions_success} deleted{f', {versions_failed} failed' if versions_failed > 0 else ''}"
            )

            if not skip_dynamodb:
                status_lines.append(
                    f"DynamoDB Records: {dynamo_versions_success} deleted{f', {dynamo_versions_failed} failed' if dynamo_versions_failed > 0 else ''}"
                )

            # Join the status lines with newlines and proper indentation
            result_msg = "\n    ".join(status_lines)

            if has_failures:
                tracker.fail_step(idx, result_msg)
            else:
                tracker.complete_step(idx, result_msg)

        except ClientError as e:
            error(f"Error setting up client for region {region}", str(e))
            lambda_failure += len(versions)
            if not skip_dynamodb:
                dynamo_failure += len(versions)
            tracker.fail_step(idx, "Failed to set up AWS client")

    return (lambda_success, lambda_failure, dynamo_success, dynamo_failure)


def print_layer_summary(layers: List[Dict]):
    """
    Print a summary of layers that will be deleted.
    """
    if not layers:
        warning("No layers found", "No layers match the specified pattern.")
        return

    total_layers = len(layers)
    total_versions = sum(len(layer["Versions"]) for layer in layers)

    header("LAYERS SUMMARY")
    status(
        "Found", f"{total_layers} layer(s) with a total of {total_versions} version(s)"
    )

    # Group by region for better organization
    layers_by_region = {}
    for layer in layers:
        region = layer["Region"]
        if region not in layers_by_region:
            layers_by_region[region] = []
        layers_by_region[region].append(layer)

    # Print by region
    for region in sorted(layers_by_region.keys()):
        subheader(f"Region: {region}")

        for layer in layers_by_region[region]:
            layer_name = layer["Name"]
            versions = layer["Versions"]

            # Sort versions by number
            versions.sort(key=lambda x: x["Version"])

            status("Layer", layer_name)

            # Create a table for versions
            headers = ["Version", "Created Date", "ARN"]
            rows = []
            for version in versions:
                version_number = version["Version"]
                created_date = version["CreatedDate"]
                arn = version["Arn"]

                if isinstance(created_date, str):
                    created_date_str = created_date
                else:
                    created_date_str = created_date.strftime("%Y-%m-%d %H:%M:%S")

                # Truncate ARN if too long
                arn_display = arn
                if len(arn) > 80:
                    arn_display = arn[:77] + "..."

                rows.append([version_number, created_date_str, arn_display])

            format_table(headers, rows)


def confirm_deletion(
    layers: List[Dict], force: bool = False, skip_dynamodb: bool = False
) -> bool:
    """
    Ask for confirmation before deleting layers.
    """
    if force:
        return True

    if not layers:
        return False

    total_versions = sum(len(layer["Versions"]) for layer in layers)

    header("CONFIRMATION REQUIRED")
    warning(
        "Warning",
        f"You are about to delete {len(layers)} layer(s) with {total_versions} total version(s).",
    )

    if not skip_dynamodb:
        warning("Warning", "The corresponding DynamoDB records will also be deleted.")

    warning("Warning", "This action CANNOT be undone!")

    confirmation = input("\nType 'DELETE' to confirm: ")
    return confirmation == "DELETE"


@click.command()
@click.option(
    "--pattern",
    required=True,
    help="Glob pattern to match layer names (e.g., 'custom-otel-collector-*-0_119_0')",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Perform a dry run without actually deleting layers",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt (use with caution)",
)
@click.option(
    "--regions",
    help="Comma-separated list of regions to check (default: all supported regions)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show more detailed output",
)
@click.option(
    "--skip-dynamodb",
    is_flag=True,
    help="Skip deletion of DynamoDB records (delete Lambda layer versions only)",
)
def main(pattern, dry_run, force, regions, verbose, skip_dynamodb):
    """Delete AWS Lambda layers matching a pattern across regions."""

    # Set verbose mode if available
    set_verbose_mode(verbose)

    # Show script banner
    header("AWS LAMBDA LAYER DELETION UTILITY")

    # Use specified regions if provided
    global REGIONS
    if regions:
        REGIONS = [region.strip() for region in regions.split(",")]
        status("Using regions", ", ".join(REGIONS))

    # Show summary of options
    headers = ["Option", "Value"]
    rows = [
        ["Pattern", pattern],
        ["Dry Run", "Yes" if dry_run else "No"],
        ["Force", "Yes" if force else "No"],
        ["Regions", len(REGIONS)],
        ["DynamoDB Cleanup", "Disabled" if skip_dynamodb else "Enabled"],
    ]
    format_table(headers, rows, title="Configuration")

    # Find matching layers
    matching_layers = find_matching_layers(pattern)

    # Print summary
    print_layer_summary(matching_layers)

    # Ask for confirmation
    if not dry_run:
        if not confirm_deletion(matching_layers, force, skip_dynamodb):
            warning("Deletion cancelled", "User did not confirm deletion")
            return

    # Delete layers
    lambda_success, lambda_failure, dynamo_success, dynamo_failure = delete_layers(
        matching_layers, dry_run, skip_dynamodb
    )

    # Print results
    header("RESULTS")
    if dry_run:
        info("Dry Run Summary", f"Would have deleted {lambda_success} layer version(s)")
        if not skip_dynamodb:
            info(
                "Dry Run Summary",
                f"Would have deleted {dynamo_success} DynamoDB record(s)",
            )
    else:
        if lambda_success > 0:
            success("Successfully deleted", f"{lambda_success} layer version(s)")
        if lambda_failure > 0:
            error("Failed to delete", f"{lambda_failure} layer version(s)")

        if not skip_dynamodb:
            if dynamo_success > 0:
                success("Successfully deleted", f"{dynamo_success} DynamoDB record(s)")
            if dynamo_failure > 0:
                error("Failed to delete", f"{dynamo_failure} DynamoDB record(s)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        warning("Operation cancelled", "User interrupted the process")
        sys.exit(1)
