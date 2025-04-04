#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "boto3",
#     "pyyaml",
#     "click",
#     "yaspin",
# ]
# ///
"""
test-distribution-locally.py

A utility script to build and test custom OpenTelemetry Collector distributions locally.
This script emulates the refactored GitHub workflow process:
1. Clones upstream repo temporarily.
2. Determines upstream version using 'make set-otelcol-version'.
3. Determines build tags using distribution_utils directly.
4. Calls 'build_extension_layer.py' with version and tags in env.
5. Optionally calls 'lambda_layer_publisher.py' with necessary info.

Features:
- External commands (git, make) use spinners and only show output on failure
- Python scripts show full output for debugging
- Environment variables from child processes are captured using GitHub Actions simulation
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
import re
import shutil  # Needed for cleanup
import click
import time  # Add time for tracking overall execution time

# Import distribution utilities from the scripts directory
from scripts.otel_layer_utils.distribution_utils import (
    load_distributions,
    resolve_build_tags,
    DistributionError,
)
from scripts.otel_layer_utils.ui_utils import (
    header,
    subheader,
    status,
    info,
    detail,
    success,
    error,
    warning,
    format_table,
    StepTracker,
    set_verbose_mode,
    debug,
    format_file_size,
    separator,
    format_elapsed_time,
)
from scripts.otel_layer_utils.subprocess_utils import run_command


class TerminateApp(Exception):
    """Exception raised to signal application termination with an error code."""
    def __init__(self, message="Application terminated", exit_code=1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(self.message)


def is_python_script(cmd):
    """Check if the command is a Python script."""
    if len(cmd) < 2:
        return False
    # Check if the command is running python and a script
    return (cmd[0].endswith("python") or cmd[0].endswith("python3")) and cmd[
        1
    ].endswith(".py")


def check_aws_credentials():
    """Check if AWS credentials are configured correctly."""
    try:
        # Import boto3 (should be available as it's in the script requirements)
        import boto3

        # Create a boto3 STS client
        sts_client = boto3.client("sts")

        # Call get_caller_identity directly using boto3
        response = sts_client.get_caller_identity()

        # Extract account ID from response
        account_id = response.get("Account")
        if account_id:
            success("AWS credentials are configured", f"Account: {account_id}")
            return True
        else:
            warning(
                "AWS credentials are configured but account ID couldn't be determined."
            )
            return False

    except ImportError:
        error("boto3 is not installed", "Please install it: pip install boto3")
        return False
    except Exception as e:
        error("AWS credentials are not configured correctly", str(e))
        return False


def get_aws_region():
    """Get the current AWS region from boto3 session."""
    try:
        import boto3

        # Get the region from the default session
        session = boto3.session.Session()
        region = session.region_name

        if region:
            return region
        else:
            # Don't fallback, require configuration
            error("Could not determine AWS region from boto3 session.")
            detail(
                "Hint", "Configure region via AWS_REGION env var or 'aws configure'."
            )
            raise TerminateApp("Could not determine AWS region")
    except Exception as e:
        error("Error getting AWS region", str(e))
        raise TerminateApp("Failed to get AWS region")


def load_distribution_choices():
    """
    Load distribution choices from config/distributions.yaml.
    
    Returns:
        tuple: (distribution_choices, distributions_data)
        
    Raises:
        TerminateApp: If distributions cannot be loaded
    """
    distribution_choices = []
    distributions_data = {}
    
    try:
        repo_root = Path().cwd()
        dist_yaml_path = repo_root / "config" / "distributions.yaml"
        
        # Attempt to load distributions data
        distributions_data = load_distributions(dist_yaml_path)
        
        # If successful, populate choices
        distribution_choices = sorted(list(distributions_data.keys()))
        success("Loaded distribution choices", ", ".join(distribution_choices))
        
        # Fail fast if loaded data is empty or invalid
        if not distribution_choices or not distributions_data:
            raise ValueError("Distributions config file loaded but appears empty or invalid.")
            
        return distribution_choices, distributions_data
        
    except FileNotFoundError:
        error(f"Fatal Error: Distributions config file not found at {dist_yaml_path}")
        raise TerminateApp(f"Distributions config file not found at {dist_yaml_path}")
    except Exception as e:
        # Catch other errors during loading/parsing (e.g., YAMLError, ValueError)
        error(
            f"Fatal Error: Could not load distributions from config file {dist_yaml_path}",
            str(e),
        )
        raise TerminateApp(f"Failed to load distributions: {str(e)}")


DISTRIBUTION_CHOICES, _distributions_data = load_distribution_choices()
ARCHITECTURE_CHOICES = ["amd64", "arm64"]

# Load distribution choices
header("Loading distributions")

@click.command(
    context_settings=dict(
        help_option_names=["-h", "--help"],
        max_content_width=120,  # Wider help text
    )
)
@click.option(
    "--distribution",
    "-d",
    default="default",  # Keep default for CLI convenience, but resolution must succeed
    type=click.Choice(DISTRIBUTION_CHOICES, case_sensitive=False),
    help="The distribution to build.",
)
@click.option(
    "--architecture",
    "-a",
    default="amd64",
    type=click.Choice(ARCHITECTURE_CHOICES, case_sensitive=False),
    help="The architecture to build for.",
)
@click.option(
    "--upstream-repo",
    "-r",
    default="open-telemetry/opentelemetry-lambda",
    help="Upstream repository to use.",
)
@click.option(
    "--upstream-ref",
    "-b",
    default="main",
    help="Upstream Git reference (branch, tag, SHA).",
)
@click.option(
    "--layer-name",
    "-l",
    default="otel-ext-layer",
    help="Base name for the Lambda layer.",
)
@click.option(
    "--runtimes",
    default="nodejs18.x nodejs20.x java17 python3.9 python3.10",
    help="Space-delimited list of compatible runtimes.",
)
@click.option(
    "--skip-publish",
    is_flag=True,
    help="Skip the publishing step and only build the layer.",
)
@click.option("--verbose", "-v", is_flag=True, help="Show more detailed output.")
@click.option("--public", is_flag=True, help="Make the layer publicly accessible.")
@click.option(
    "--keep-temp",
    is_flag=True,
    help="Keep temporary directories (e.g., upstream clone).",
)
def main(
    distribution,
    architecture,
    upstream_repo,
    upstream_ref,
    layer_name,
    runtimes,
    skip_publish,
    verbose,
    public,
    keep_temp,
):
    """Build and test custom OTel Collector distributions locally."""

    # Track start time for overall execution
    start_time = time.time()

    # Enable verbose mode if requested
    set_verbose_mode(verbose)

    # Set up paths
    repo_root = Path(__file__).parent.parent.resolve()
    build_dir = repo_root / "build"
    build_dir.mkdir(exist_ok=True)
    scripts_dir = repo_root / "tools" / "scripts"  # Scripts are in tools/scripts

    temp_upstream_dir = None  # Initialize
    upstream_version = None
    build_tags_string = None

    # Setup a step tracker for the main build process
    separator(title="Build Process")
    build_steps = [
        "Clone upstream repository",
        "Determine upstream version",
        "Resolve build tags",
        "Build extension layer",
        "Publish layer (if enabled)",
    ]
    tracker = StepTracker(build_steps, title="Build Process Steps")

    try:
        # --- Step 0: Prepare Environment (Corresponds to 'prepare-environment' job) ---
        separator(title="Prepare Environment")
        header("Prepare environment")

        # --- Sub-step: Clone Upstream Repo ---
        subheader("Cloning repository")
        tracker.start_step(0)  # Start the clone step
        temp_upstream_dir = tempfile.mkdtemp(prefix="otel-upstream-")
        temp_upstream_path = Path(temp_upstream_dir)
        status("Target repo", f"{upstream_repo}@{upstream_ref}")
        info("Temp directory", temp_upstream_dir)
        repo_url = f"https://github.com/{upstream_repo}.git"
        run_command(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                upstream_ref,
                repo_url,
                str(temp_upstream_path),
            ],
            capture_output=True,
        )
        tracker.complete_step(0, "Repository cloned successfully")

        # Determine Version
        upstream_collector_dir = temp_upstream_path / "collector"
        upstream_makefile = upstream_collector_dir / "Makefile"
        upstream_version_file = upstream_collector_dir / "VERSION"
        upstream_version = None

        if not upstream_makefile.exists():
            error("Makefile not found", f"{upstream_makefile}")
            detail("Detail", "Cannot determine version via make")
            tracker.fail_step(1, "Makefile not found")
            raise TerminateApp("Makefile not found")

        subheader("Determining version")
        tracker.start_step(1)
        debug(f"Looking for Makefile at {upstream_makefile}")
        run_command(
            ["make", "set-otelcol-version"],
            cwd=str(upstream_collector_dir),
            capture_output=True,
        )

        if not upstream_version_file.is_file():
            error("VERSION file not created", f"{upstream_version_file}")
            tracker.fail_step(1, "VERSION file not created")
            raise TerminateApp("VERSION file not created")

        with open(upstream_version_file, "r") as vf:
            upstream_version = vf.read().strip()

        if not upstream_version:
            error("VERSION file is empty", f"{upstream_version_file}")
            tracker.fail_step(1, "VERSION file is empty")
            raise TerminateApp("VERSION file is empty")
        success("Determined Upstream Version", upstream_version)
        tracker.complete_step(1, f"Version: {upstream_version}")

        # --- Sub-step: Determine Build Tags String (Locally) ---
        subheader("Determining build tags")
        tracker.start_step(2)
        build_tags_string = ""
        try:
            # _distributions_data was loaded above when setting choices
            if not _distributions_data:  # Check if loading failed earlier
                error("Cannot resolve build tags", "Distributions data failed to load")
                tracker.fail_step(2, "Distributions data failed to load")
                raise TerminateApp("Distributions data failed to load")
            buildtags_list = resolve_build_tags(distribution, _distributions_data)
            build_tags_string = ",".join(filter(None, buildtags_list))
            success("Determined build tags", build_tags_string)
            tracker.complete_step(2, f"Tags: {build_tags_string}")
        except DistributionError as e:
            error(
                f"Error resolving build tags for distribution '{distribution}'", str(e)
            )
            tracker.fail_step(2, str(e))
            raise TerminateApp(f"Error resolving build tags: {str(e)}")
        except Exception as e:
            error("An unexpected error occurred resolving build tags", str(e))
            tracker.fail_step(2, str(e))
            raise TerminateApp(f"An unexpected error occurred resolving build tags: {str(e)}")

        # --- Step 1: Build Collector Layer (Corresponds to 'build-layer' job) ---
        separator(title="Build Layer")
        header(f"Build layer ({architecture})")
        tracker.start_step(3)  # Start the build step

        build_script = scripts_dir / "build_extension_layer.py"
        subheader("Running build script")
        build_cmd = [
            sys.executable,
            str(build_script),
            "--upstream-repo",
            upstream_repo,
            "--upstream-ref",
            upstream_ref,
            # Distribution determines build tags, layer naming, and is used for DynamoDB metadata
            "--distribution",
            distribution,
            "--arch",
            architecture,
            "--output-dir",
            str(build_dir),
            # Pass version and tags as command line arguments
            "--upstream-version",
            upstream_version,
            "--build-tags",
            build_tags_string,
        ]

        # Run build script (don't capture output by default, let it stream)
        run_command(build_cmd)

        layer_file = build_dir / f"collector-{architecture}-{distribution}.zip"
        if not layer_file.exists():
            error("Expected layer file not found after build", f"{layer_file}")
            tracker.fail_step(3, "Layer file not found")
            raise TerminateApp("Layer file not found")

        # Get file size
        file_size = os.path.getsize(layer_file)
        formatted_size = format_file_size(file_size)
        
        success("Build successful", f"{layer_file} ({formatted_size})")
        tracker.complete_step(3, f"Layer built: {layer_file.name} ({formatted_size})")

        if skip_publish:
            info("Skipping publish step", "Publishing not requested")
            tracker.complete_step(4, "Skipped (not requested)")
            
            # Add summary at the end
            separator(title="Build Summary")
            
            # Calculate total elapsed time
            total_elapsed = time.time() - start_time
            
            # Create summary table using the format_table function
            headers = ["Property", "Value"]
            rows = [
                ["Distribution", distribution],
                ["Architecture", architecture],
                ["Layer File", str(layer_file)],
                ["File Size", formatted_size],
                ["Total Duration", format_elapsed_time(total_elapsed)],
                ["Publishing", "Skipped"],
            ]
            format_table(headers, rows, title="Build Completion Summary")
            return

        # Check AWS credentials before publishing
        # --- Step 2: Publish Layer (Corresponds to 'release-layer' job using reusable workflow) ---
        separator(title="Publish Layer")
        header(f"Publish layer ({architecture})")
        tracker.start_step(4)  # Start the publish step

        # --- Sub-step: Check AWS Credentials ---
        subheader("Checking AWS credentials")
        if not check_aws_credentials():
            error("AWS credentials check failed", "Skipping publish step")
            detail("Hint", "Run 'aws configure' or set AWS environment variables")
            tracker.fail_step(4, "AWS credentials check failed")
            raise TerminateApp("AWS credentials check failed")

        # --- Sub-step: Get AWS Region ---
        subheader("Determining AWS region")
        region = get_aws_region()
        success("Target AWS Region", region)

        # --- Sub-step: Prepare Publish Environment ---
        subheader("Preparing for publish")

        # Print debug info if verbose
        if verbose:
            info("Debug info", "Publishing with parameters:")
            detail("Layer name", layer_name)
            detail("Artifact", str(layer_file))
            detail("Region", region)
            detail("Architecture", architecture)
            detail("Runtimes", runtimes)
            detail("Release group", "local")
            detail("Distribution", distribution)
            detail("Collector version", upstream_version)
            detail("Build tags", build_tags_string)
            detail("Make public", str(public).lower())

        # --- Sub-step: Execute Publish Script ---
        subheader("Publishing layer")
        publisher_script = scripts_dir / "lambda_layer_publisher.py"

        # Build command with all arguments including build-tags
        publish_cmd = [
            sys.executable,
            str(publisher_script),
            "--layer-name",
            layer_name,
            "--artifact-name",
            str(layer_file),
            "--region",
            region,
            "--architecture",
            architecture,
            "--runtimes",
            runtimes,
            "--release-group",
            "local",  # Always use 'local' for testing
            "--distribution",
            distribution,
            "--collector-version",
            upstream_version,
            "--make-public",
            str(public).lower(),
            "--build-tags",
            build_tags_string,
        ]

        publish_result, github_env = run_command(
            publish_cmd,
            capture_github_env=True,
            capture_output=False,  # Don't capture output since this script uses spinners
        )

        # Display layer information from GitHub environment variables or stdout
        layer_arn = github_env.get("layer_arn")
        if not layer_arn:
            # Fallback: Try to extract from stdout
            arn_match = re.search(
                r"Published Layer ARN: (arn:aws:lambda:[^:]+:[^:]+:layer:[^:]+:[0-9]+)",
                publish_result.stdout,
            )
            if arn_match:
                layer_arn = arn_match.group(1)

        if layer_arn:
            subheader("Layer published")
            status("Layer ARN", layer_arn)
            tracker.complete_step(4, f"Layer ARN: {layer_arn}")
        else:
            warning("Publish step completed, but could not determine final Layer ARN")
            tracker.complete_step(4, "Published successfully (ARN unknown)")

        success(
            f"Published {distribution} distribution to region {region} as a 'local' release"
        )
        info(
            "Next steps",
            "You can now test this layer by attaching it to a Lambda function",
        )
        
        # Add summary at the end
        separator(title="Build Summary")
        
        # Calculate total elapsed time
        total_elapsed = time.time() - start_time
        
        # Create summary table using the format_table function
        headers = ["Property", "Value"]
        rows = [
            ["Distribution", distribution],
            ["Architecture", architecture],
            ["Layer File", str(layer_file)],
            ["File Size", formatted_size],
            ["Total Duration", format_elapsed_time(total_elapsed)],
        ]
        
        # Add ARN if available
        if layer_arn:
            rows.append(["Layer ARN", layer_arn])
            
        format_table(headers, rows, title="Build Completion Summary")

    except subprocess.CalledProcessError:
        # Error message should have been printed by run_command
        error("An error occurred during execution")
        raise TerminateApp("An error occurred during execution")
    except Exception as e:
        error("An unexpected error occurred", str(e))
        raise TerminateApp(f"An unexpected error occurred: {str(e)}")
    finally:  # Correct indentation relative to try
        # Cleanup temporary upstream directory (Correct indentation relative to finally)
        if temp_upstream_dir and Path(temp_upstream_dir).exists():
            if keep_temp:
                info("Keeping temporary upstream clone", temp_upstream_dir)
            else:
                subheader("Cleaning up")
                status("Removing temporary upstream clone", temp_upstream_dir)
                shutil.rmtree(temp_upstream_dir)


if __name__ == "__main__":
    try:
        main()
    except TerminateApp as e:
        # The error has already been logged by the error() function where the exception was raised
        sys.exit(e.exit_code)
