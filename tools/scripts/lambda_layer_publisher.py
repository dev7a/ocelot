#!/usr/bin/env python3
"""
lambda_layer_publisher.py

A comprehensive script to handle AWS Lambda layer publishing:
- Constructs layer name based on inputs
- Calculates MD5 hash of layer content
- Checks if an identical layer already exists
- Publishes new layer version if needed
- Makes the layer public if requested
- Writes metadata to DynamoDB
- Outputs a summary of the action
"""

import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional, Tuple
import click


# Import utility modules
from otel_layer_utils.ui_utils import (
    header,
    subheader,
    status,
    info,
    detail,
    success,
    error,
    warning,
    spinner,
    github_summary_table,
)
from otel_layer_utils.dynamodb_utils import DYNAMODB_TABLE_NAME, get_item, write_item
from otel_layer_utils.github_utils import set_github_output

# Import boto3 for AWS API operations
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    error("boto3 library not found", "Please install it: pip install boto3")
    sys.exit(1)

# Default values
DEFAULT_UPSTREAM_REPO = "open-telemetry/opentelemetry-lambda"
DEFAULT_UPSTREAM_REF = "main"
DEFAULT_DISTRIBUTION = "default"
DEFAULT_ARCHITECTURE = "amd64"


def calculate_md5(filename: str) -> str:
    """Calculate MD5 hash of a file."""
    status("Computing MD5", filename)

    def compute_hash():
        hash_md5 = hashlib.md5()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    md5_hash = spinner("Computing MD5 hash", compute_hash)
    success("MD5 Hash", md5_hash)
    return md5_hash


def construct_layer_name(
    base_name: str,
    architecture: Optional[str] = None,
    distribution: Optional[str] = None,
    version: Optional[str] = None,
    collector_version: Optional[str] = None,
    release_group: str = "prod",
) -> Tuple[str, str, str]:  # Added layer_version_str to return
    """
    Construct the full layer name according to AWS naming rules.

    Returns:
        Tuple[str, str, str]: (layer_name_cleaned, arch_str, layer_version_str_for_naming)
    """
    layer_name = base_name
    layer_version_str_for_naming = ""

    # Handle architecture
    arch_str = architecture.replace("amd64", "x86_64") if architecture else "x86_64"
    if architecture:
        layer_name = f"{layer_name}-{architecture}"

    # Add distribution if specified
    if distribution:
        layer_name = f"{layer_name}-{distribution}"
        info("Including distribution in layer name", distribution)

    # Determine version string for naming
    layer_version = None
    if version:
        layer_version = version
    elif collector_version:
        layer_version = re.sub(r"^v", "", collector_version)
    else:
        github_ref = os.environ.get("GITHUB_REF", "")
        if github_ref:
            layer_version = re.sub(r".*\/[^0-9\.]*", "", github_ref) or "latest"
        else:
            layer_version = "latest"

    # Clean up the version for AWS naming rules
    if layer_version:
        # Replace dots with underscores, remove disallowed chars
        layer_version_cleaned_for_naming = re.sub(r"[^a-zA-Z0-9_-]", "_", layer_version)
        layer_name = f"{layer_name}-{layer_version_cleaned_for_naming}"
        layer_version_str_for_naming = (
            layer_version_cleaned_for_naming  # Store the cleaned version used in name
        )

    # Always add release group (even if 'prod')
    layer_name = f"{layer_name}-{release_group}"

    # Final cleanup for layer name
    layer_name_cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", layer_name)
    if re.match(r"^[0-9]", layer_name_cleaned):
        layer_name_cleaned = f"layer-{layer_name_cleaned}"

    success("Final layer name", layer_name_cleaned)
    # The actual version string might differ slightly from the cleaned one used in the name
    # We will re-extract it from the final name if needed later, or use layer_version_str_for_naming
    return layer_name_cleaned, arch_str, layer_version_str_for_naming


def check_layer_exists(
    layer_name: str, current_md5: str, region: str
) -> Tuple[bool, Optional[str]]:
    """Check if a Lambda layer with the given name and MD5 hash exists using boto3."""
    subheader("Checking layers")
    status("Checking layer existence", f"{layer_name} in {region}")

    def check_lambda_layers():
        try:
            lambda_client = boto3.client("lambda", region_name=region)

            # Get all versions of the layer
            try:
                paginator = lambda_client.get_paginator("list_layer_versions")
                existing_layers = []

                for page in paginator.paginate(LayerName=layer_name):
                    for version in page["LayerVersions"]:
                        existing_layers.append(
                            {
                                "LayerVersionArn": version["LayerVersionArn"],
                                "Description": version.get("Description", ""),
                            }
                        )

                return existing_layers
            except lambda_client.exceptions.ResourceNotFoundException:
                return None

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            error("AWS Error", f"{error_code} - {error_message}", exc_info=e)
            return False
        except Exception as e:
            error("Error", str(e), exc_info=e)
            return False

    existing_layers = spinner("Checking existing layers", check_lambda_layers)

    if existing_layers is None:
        info("No existing layers found", layer_name)
        return False, None

    if not existing_layers:
        info("No existing layers found", "Empty response")
        return False, None

    status("Found existing layers", str(len(existing_layers)))
    detail("Current MD5", current_md5)

    # Check for MD5 match in descriptions
    for layer in existing_layers:
        if current_md5 in layer["Description"]:
            matching_layer = layer["LayerVersionArn"]
            success("Found match", matching_layer)
            return True, matching_layer

    # No match found, return the latest version ARN if available
    if existing_layers:
        latest_layer = existing_layers[0]["LayerVersionArn"]
        info("No MD5 match", f"Latest version: {latest_layer}")
        return False, latest_layer

    return False, None


def publish_layer(
    layer_name: str,
    layer_file: str,
    md5_hash: str,
    region: str,
    arch: str,
    runtimes: Optional[str] = None,
    build_tags: Optional[str] = None,
    dry_run: bool = False,
) -> Optional[str]:
    """Publish a new Lambda layer version using boto3."""
    subheader("Publishing layer")
    status("Layer name", layer_name)

    if dry_run:
        info("Dry Run", "Would publish layer with the following details:")
        detail("  Layer Name", layer_name)
        detail("  Region", region)
        detail("  Architecture", arch)
        detail("  Runtimes", runtimes or "[None]")
        detail("  Build Tags", build_tags or "[None]")
        # Simulate a successful ARN generation for dry run
        simulated_arn = f"arn:aws:lambda:{region}:123456789012:layer:{layer_name}:1"
        success("Dry Run", f"Simulated ARN: {simulated_arn}")
        return simulated_arn

    # Construct description
    description = f"md5: {md5_hash}"
    if build_tags:
        # Split the original build_tags string into a list
        tags_list = build_tags.split(',')
        
        # Process each tag: strip "lambdacomponents." prefix and whitespace
        processed_tags = []
        for tag in tags_list:
            tag = tag.strip() # Remove leading/trailing whitespace
            # Replace the prefix "lambdacomponents." with an empty string
            processed_tags.append(tag.replace("lambdacomponents.", ""))
        
        # Join the processed tags with ", "
        formatted_build_tags = ", ".join(processed_tags)
        
        description += f" | {formatted_build_tags}" # Append the formatted tags
        
    # Truncate description if it exceeds AWS limit (256 chars)
    if len(description) > 256:
        description = description[:253] + "..."
        info("Description truncated", "Length limit exceeded")

    detail("Description", description)

    # Convert arch from amd64 to x86_64 if needed
    compatible_architectures = [arch.replace("amd64", "x86_64")]

    # Prepare the runtimes list
    compatible_runtimes = runtimes.split() if runtimes else None

    # Define a function to handle the publishing process
    def do_publish():
        try:
            # Read the ZIP file content
            with open(layer_file, "rb") as f:
                zip_content = f.read()

            lambda_client = boto3.client("lambda", region_name=region)

            # Prepare the parameters
            params = {
                "LayerName": layer_name,
                "Description": description,
                "Content": {"ZipFile": zip_content},
                "CompatibleArchitectures": compatible_architectures,
                "LicenseInfo": "MIT",
            }

            # Add runtimes if specified
            if compatible_runtimes:
                params["CompatibleRuntimes"] = compatible_runtimes

            # Publish the layer
            response = lambda_client.publish_layer_version(**params)

            return response["LayerVersionArn"]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            error("AWS Error", f"{error_code} - {error_message}", exc_info=e)
            return None
        except Exception as e:
            error("Error", str(e), exc_info=e)
            return None

    # Use spinner for reading file
    layer_zip_size = os.path.getsize(layer_file) / (1024 * 1024)  # Convert to MB
    info("Layer file size", f"{layer_zip_size:.2f} MB")

    # Use spinner for uploading
    layer_arn = spinner("Uploading to AWS Lambda", do_publish)

    if layer_arn:
        success("Published", layer_arn)
    return layer_arn


def make_layer_public(
    layer_name: str, layer_arn: str, region: str, dry_run: bool = False
) -> bool:
    """Make a Lambda layer version publicly accessible using boto3."""
    subheader("Making layer public")
    status("Layer ARN", layer_arn)

    if dry_run:
        info("Dry Run", f"Would make layer {layer_arn} public in {region}")
        return True  # Assume success for dry run

    if not layer_arn:
        error("No ARN", "Cannot make layer public")
        return False

    # Extract version number from ARN
    version_match = re.search(r":(\d+)$", layer_arn)
    if not version_match:
        error("Invalid ARN", f"No version number in ARN: {layer_arn}")
        return False

    layer_version = int(version_match.group(1))
    detail("Version", str(layer_version))

    def update_permissions():
        try:
            lambda_client = boto3.client("lambda", region_name=region)

            # Check if permission already exists
            try:
                lambda_client.get_layer_version_policy(
                    LayerName=layer_name, VersionNumber=layer_version
                )
                return "already_public"
            except lambda_client.exceptions.ResourceNotFoundException:
                # Expected exception if no policy exists
                pass

            # Add public permission
            lambda_client.add_layer_version_permission(
                LayerName=layer_name,
                VersionNumber=layer_version,
                StatementId="publish",
                Action="lambda:GetLayerVersion",
                Principal="*",
            )

            return "success"

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            error("AWS Error", f"{error_code} - {error_message}", exc_info=e)
            return None
        except Exception as e:
            error("Error", str(e), exc_info=e)
            return None

    result = spinner("Updating layer permissions", update_permissions)

    if result == "already_public":
        info("Already public", "Skipping permission update")
        return True
    elif result == "success":
        status("Setting permissions", "Public access enabled")
        success("Layer public")
        return True
    else:
        return False


def write_metadata_to_dynamodb(
    dynamodb_region: str, metadata: dict, dry_run: bool = False
) -> bool:
    """Write the collected layer metadata to the DynamoDB table."""
    subheader("Writing metadata")
    status("Target table", DYNAMODB_TABLE_NAME)

    if dry_run:
        info("Dry Run", "Would write the following metadata to DynamoDB:")
        for key, value in metadata.items():
            detail(f"  {key}", str(value))
        return True  # Assume success for dry run

    # Basic validation
    required_keys = [
        "pk",
        "sk",
        "layer_arn",
        "region",
        "distribution",
        "architecture",
        "md5_hash",
    ]
    if not all(key in metadata and metadata[key] for key in required_keys):
        error("Invalid metadata", "Missing required fields")
        return False

    # Ensure publish_timestamp is set
    if "publish_timestamp" not in metadata:
        metadata["publish_timestamp"] = datetime.now(timezone.utc).isoformat()

    def write_to_dynamo():
        try:
            response = write_item(metadata, region=dynamodb_region)
            return response
        except ValueError as e:
            error("Validation Error", str(e), exc_info=e)
            return None
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "ResourceNotFoundException":
                error("AWS Error", str(e), exc_info=e)
                detail("Detail", f"Table not found in {dynamodb_region}")
            elif error_code == "AccessDeniedException":
                error("AWS Error", str(e), exc_info=e)
                detail("Detail", "Access denied - check IAM permissions")
            else:
                error("AWS Error", str(e), exc_info=e)
            return None
        except Exception as e:
            error("Error", str(e), exc_info=e)
            return None

    response = spinner("Writing to DynamoDB", write_to_dynamo)
    if response:
        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code == 200:
            success("Write successful", metadata["layer_arn"])
            return True
        else:
            error("Write failed", f"Status code: {status_code}")
            return False

    return False


def create_github_summary(
    layer_name: str,
    region: str,
    layer_arn: str,
    md5_hash: str,
    skip_publish: bool,
    artifact_name: str,
    distribution: Optional[str] = None,
    architecture: Optional[str] = None,
    collector_version: Optional[str] = None,
) -> None:
    """Create a summary for GitHub Actions."""
    github_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not github_step_summary:
        return

    properties = {
        "Layer Name": layer_name,
        "Region": region,
        "ARN": layer_arn,
        "Content MD5": md5_hash,
        "Status": "Reused existing layer (identical content)"
        if skip_publish
        else "Published new layer version",
        "Artifact": artifact_name,
    }

    if distribution and distribution != "default":
        properties["Distribution"] = distribution

    if architecture:
        properties["Architecture"] = architecture

    if collector_version:
        properties["Collector Version"] = collector_version

    summary = github_summary_table(properties, "Layer Publishing Summary")

    try:
        with open(github_step_summary, "a") as f:
            f.write(summary + "\n")
    except Exception as e:
        error("Error writing to GITHUB_STEP_SUMMARY", str(e), exc_info=e)


def check_and_repair_dynamodb(
    dynamodb_region: str,
    args_dict,
    existing_layer_arn: str,
    md5_hash: str,
    layer_version_str: str,
    dry_run: bool = False,
):
    """Checks if metadata for an existing layer ARN is in DynamoDB and adds it if missing."""
    subheader("Checking DynamoDB")
    status("Checking metadata", existing_layer_arn)

    # Perform the check even in dry run mode to see if repair *would* be needed
    pk = existing_layer_arn
    sk = args_dict["distribution"]

    def check_dynamodb():
        try:
            item = get_item(pk)
            return {"Item": item} if item else {}
        except ClientError as e:
            error("AWS Error", str(e), exc_info=e)
            return None
        except Exception as e:
            error("Error", str(e), exc_info=e)
            return None

    response = spinner("Checking DynamoDB", check_dynamodb)

    if response and "Item" not in response:
        info("Metadata missing", "Will repair record")
        status("Repairing record", "Creating new metadata")
        # Construct the metadata dictionary exactly as in the successful publish path
        metadata = {
            "pk": pk,
            "sk": sk,
            "layer_arn": existing_layer_arn,
            "region": args_dict["region"],
            "base_name": args_dict["layer_name"],
            "architecture": args_dict["architecture"],
            "distribution": args_dict["distribution"],
            "layer_version_str": layer_version_str,
            "collector_version_input": args_dict["collector_version"],
            "md5_hash": md5_hash,
            "publish_timestamp": datetime.now(timezone.utc).isoformat(),
            "compatible_runtimes": args_dict["runtimes"].split()
            if args_dict["runtimes"]
            else None,
        }
        # Attempt to write the missing record (or simulate in dry run)
        write_success = write_metadata_to_dynamodb(
            dynamodb_region, metadata, dry_run=dry_run
        )
        if write_success:
            success("Repair complete" if not dry_run else "Dry Run: Repair simulated")
        else:
            error(
                "Repair failed" if not dry_run else "Dry Run: Repair simulation failed"
            )
    elif response:
        info("Metadata exists", "No repair needed")


# Use callbacks for default values to support environment variable fallbacks
def env_bool(env_var, default=False):
    """Convert environment variable to boolean"""
    val = os.environ.get(env_var, "").lower()
    if val in ("true", "yes", "1"):
        return True
    return default


@click.command()
@click.option(
    "--layer-name",
    required=True,
    help="Base layer name (e.g., custom-otel-collector)",
)
@click.option(
    "--artifact-name",
    required=True,
    help="Path to the layer zip artifact file",
)
@click.option(
    "--region",
    required=True,
    help="AWS region to publish the layer",
)
@click.option(
    "--dynamodb-region",
    required=True,
    help="AWS region with the dynamodb to record the publishing",
)
@click.option(
    "--architecture",
    help="Layer architecture (amd64 or arm64)",
)
@click.option(
    "--runtimes",
    help="Space-delimited list of compatible runtimes",
)
@click.option(
    "--release-group",
    default="prod",
    help="Release group (dev or prod, default: prod)",
)
@click.option(
    "--layer-version",
    help="Specific version override for layer naming",
)
@click.option(
    "--distribution",
    default="default",
    help="Distribution name (default: default)",
)
@click.option(
    "--collector-version",
    help="Version of the OpenTelemetry collector included",
)
@click.option(
    "--make-public",
    type=click.BOOL,
    default=True,
    help="Make the layer publicly accessible (true/false)",
)
@click.option(
    "--build-tags",
    default="",
    help="Comma-separated build tags used for the layer",
)
@click.option(
    "--dry-run",
    type=click.BOOL,  # Changed from is_flag=True
    default=False,
    help="Perform a dry run without actual publishing (true/false)",
)
def main(
    layer_name,
    artifact_name,
    region,
    dynamodb_region,
    architecture,
    runtimes,
    release_group,
    layer_version,
    distribution,
    collector_version,
    make_public,
    build_tags,
    dry_run,
):
    """AWS Lambda Layer Publisher"""

    header("Lambda layer publisher")
    if dry_run:
        warning("Dry Run Mode Enabled", "No actual publishing will occur")

    # Step 1: Construct layer name
    subheader("Constructing layer name")
    layer_name, arch_str, layer_version_str = construct_layer_name(
        layer_name,
        architecture,
        distribution,
        layer_version,
        collector_version,
        release_group,
    )

    # Step 2: Calculate MD5 hash
    subheader("Calculating MD5 hash")
    md5_hash = calculate_md5(artifact_name)

    # Step 3: Check if layer exists using Lambda API
    skip_publish, existing_layer_arn = check_layer_exists(layer_name, md5_hash, region)

    # Set output for GitHub Actions early
    set_github_output("skip_publish", str(skip_publish).lower())

    layer_arn = existing_layer_arn  # Use existing ARN if found
    dynamo_success = False

    # Store args in a dictionary for check_and_repair_dynamodb
    args_dict = {
        "layer_name": layer_name,
        "artifact_name": artifact_name,
        "region": region,
        "architecture": architecture,
        "runtimes": runtimes,
        "release_group": release_group,
        "layer_version": layer_version,
        "distribution": distribution,
        "collector_version": collector_version,
        "public": make_public,
    }

    # Step 4: Publish layer if needed
    if not skip_publish:
        info("Publishing new layer version", "Creating new AWS Lambda layer")
        layer_arn = publish_layer(
            layer_name,
            artifact_name,
            md5_hash,
            region,
            arch_str,
            runtimes,
            build_tags=build_tags,
            dry_run=dry_run,  # Pass dry_run flag
        )
        if layer_arn:
            # Step 5: Make layer public only if explicitly requested and not in dry run
            public_success = True
            if make_public:
                public_success = make_layer_public(
                    layer_name, layer_arn, region, dry_run=dry_run
                )  # Pass dry_run
            else:
                info(
                    "Keeping layer private",
                    "Use --make-public true to make it publicly accessible",
                )

            if public_success:
                # Step 5.5: Write Metadata for NEW layer to DynamoDB (or simulate in dry run)
                info("Preparing metadata for new layer", "For DynamoDB storage")
                metadata = {
                    "pk": layer_arn,
                    "sk": distribution,
                    "layer_arn": layer_arn,
                    "region": region,
                    "base_name": layer_name,
                    "architecture": architecture,
                    "distribution": distribution,
                    "layer_version_str": layer_version_str,
                    "collector_version_input": collector_version,
                    "md5_hash": md5_hash,
                    "publish_timestamp": datetime.now(timezone.utc).isoformat(),
                    "public": make_public,  # Track whether the layer is public
                    # Store as a list instead of a set for DynamoDB List (L) type
                    "compatible_runtimes": runtimes.split() if runtimes else None,
                }
                dynamo_success = write_metadata_to_dynamodb(
                    dynamodb_region, metadata, dry_run=dry_run
                )  # Pass dry_run
                if not dynamo_success and not dry_run:  # Only warn if not dry run
                    warning(
                        "Layer published and made public, but failed to write metadata to DynamoDB"
                    )
            else:
                warning(
                    f"Layer {layer_arn} was published but could not be made public",
                    "Skipping DynamoDB write",
                )
        else:
            # Handle case where publishing failed
            error(
                f"Layer publishing failed for {layer_name} in {region}",
                "No ARN generated",
            )
            sys.exit(1)  # Exit if publish fails

    # Logic for skipped publish
    elif skip_publish and existing_layer_arn:
        subheader("Reusing existing layer")
        info(f"Layer with MD5 {md5_hash} already exists", existing_layer_arn)
        layer_arn = existing_layer_arn  # Ensure layer_arn is set to the existing one

        # Check/repair DynamoDB even in dry run mode to simulate the check
        check_and_repair_dynamodb(
            dynamodb_region,
            args_dict,
            existing_layer_arn,
            md5_hash,
            layer_version_str,
            dry_run=dry_run,  # Pass dry_run
        )
        # Note: We don't set dynamo_success here, as the goal was just checking/repairing.
        # The summary will correctly reflect 'Reused existing layer'.

    # Set layer_arn output for GitHub Actions
    if layer_arn:
        set_github_output("layer_arn", layer_arn)
        subheader("Layer processing complete")
        create_github_summary(
            layer_name,
            region,
            layer_arn,  # Use the ARN (new or existing)
            md5_hash,
            skip_publish,  # Pass the result of the initial check
            artifact_name,
            distribution,
            architecture,
            collector_version,
        )
    else:
        # This case should ideally not be reached if publishing failed (exited)
        # or if skip_publish was true but existing_layer_arn was somehow None
        error("No valid layer ARN available to generate summary")


if __name__ == "__main__":
    main()
