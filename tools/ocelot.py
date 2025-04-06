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
ocelot.py

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

Testing Features:
- Set LOCAL_BUILD_INJECT_ERROR=<function_name> to simulate an error in a specific function:
  Available functions: clone_repository, determine_upstream_version, determine_build_tags, 
  build_layer, verify_credentials, publish_layer
"""

import sys
import time
import subprocess
import os
from pathlib import Path

import click

# Add necessary paths to python path for imports to work correctly
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add repo root
sys.path.insert(0, str(Path(__file__).parent))  # Add tools directory

# Import from the modular components
from local_build.exceptions import TerminateApp
from local_build.config import (
    load_distributions,
    determine_build_tags,
    load_distribution_choices,
)
from local_build.upstream import clone_repository, cleanup_temp_dir
from local_build.build import build_layer
from local_build.publish import publish_layer
from local_build.report import generate_summary
from local_build.context import BuildContext

# Import from the UI utilities
from scripts.otel_layer_utils.ui_utils import separator, set_verbose_mode, StepTracker, info, warning

# Check for error injection environment variable
error_target = os.environ.get("LOCAL_BUILD_INJECT_ERROR")
if error_target:
    warning(f"Error injection enabled for function: {error_target}")
    info("Test Mode", "Will simulate failure in the specified function")

# Load distribution choices
DISTRIBUTION_CHOICES, _distributions_data = load_distribution_choices()
ARCHITECTURE_CHOICES = ["amd64", "arm64"]


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
    default="ocel",
    help="Base name for the Lambda layer.",
)
@click.option(
    "--runtimes",
    default="",
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

    # Create build context
    context = BuildContext(
        distribution=distribution,
        architecture=architecture,
        upstream_repo=upstream_repo,
        upstream_ref=upstream_ref,
        layer_name=layer_name,
        runtimes=runtimes,
        skip_publish=skip_publish,
        verbose=verbose,
        public=public,
        keep_temp=keep_temp,
    )

    # Ensure build directory exists
    context.build_dir.mkdir(exist_ok=True)

    # Set start time in context
    context.start_time = start_time

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
        # --- Step 0: Load Distribution Configuration ---
        context = load_distributions(context)

        # --- Step 1: Clone Upstream Repository and Determine Version ---
        context = clone_repository(context, tracker)

        # --- Step 2: Determine Build Tags ---
        context = determine_build_tags(context, tracker)

        # --- Step 3: Build Layer ---
        context = build_layer(context, tracker)

        # --- Step 4: Publish Layer (if not skipped) ---
        if not context.skip_publish:
            if context.verbose:
                info("Build step", "Starting AWS credential verification")
            from local_build.aws import verify_credentials
            context = verify_credentials(context, tracker)
            if context.verbose:
                info("Build step", "Starting layer publication")
            context = publish_layer(context, tracker)

        # --- Step 5: Generate Summary Report ---
        generate_summary(context, start_time)

    except TerminateApp as e:
        # Display the error message if it hasn't been displayed yet
        from scripts.otel_layer_utils.ui_utils import error
        error("Process terminated", e.message, exc_info=e)
        
        # Update the tracker if step information is provided
        if (
            hasattr(e, "step_index")
            and e.step_index is not None
            and hasattr(e, "step_message")
            and e.step_message is not None
        ):
            tracker.fail_step(e.step_index, e.step_message)

        # Exit with the provided error code
        sys.exit(e.exit_code)
    except subprocess.CalledProcessError as e:
        # Error message should have been printed by run_command
        from scripts.otel_layer_utils.ui_utils import error

        error("An error occurred during execution", exc_info=e)
        sys.exit(1)
    except Exception as e:
        from scripts.otel_layer_utils.ui_utils import error

        error("An unexpected error occurred", str(e), exc_info=e)
        sys.exit(1)
    finally:
        # Cleanup temporary upstream directory
        cleanup_temp_dir(context)


if __name__ == "__main__":
    try:
        main()
    except TerminateApp as e:
        # Display the error if not already displayed
        from scripts.otel_layer_utils.ui_utils import error
        error("Process terminated", e.message, exc_info=e)
        sys.exit(e.exit_code)
    except Exception as e:
        from scripts.otel_layer_utils.ui_utils import error
        error("An unexpected error occurred", str(e), exc_info=e)
        sys.exit(1)
