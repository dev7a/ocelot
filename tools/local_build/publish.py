"""Layer publishing functionality for the local build process."""

import re
import sys

from scripts.otel_layer_utils.ui_utils import (
    header,
    subheader,
    status,
    info,
    detail,
    error,
    warning,
    success,
    separator,
)
from scripts.otel_layer_utils.subprocess_utils import run_command
from .context import BuildContext
from .exceptions import TerminateApp
from .testing import inject_error


@inject_error(step_index=4)
def publish_layer(context: BuildContext, tracker) -> BuildContext:
    """
    Publish the built layer to AWS Lambda.

    Args:
        context: The build context
        tracker: Step tracker for progress reporting

    Returns:
        BuildContext: Updated build context with layer ARN

    Raises:
        TerminateApp: If publishing fails
    """
    if context.verbose:
        info(
            "Function call",
            f"publish_layer started with aws_region={context.aws_region}, dynamodb_region={context.dynamodb_region}",
        )

    # Check if we should skip publishing
    if context.skip_publish:
        info("Skipping publish step", "Publishing not requested")
        tracker.complete_step(4, "Skipped (not requested)")
        return context

    # Start publish step
    separator(title="Publish Layer")
    header(f"Publish layer ({context.architecture})")
    tracker.start_step(4)

    # Sub-step: Prepare Publish Environment
    subheader("Preparing for publish")

    # Print debug info if verbose
    if context.verbose:
        info("Debug info", "Publishing with parameters:")
        detail("Layer name", context.layer_name)
        detail("Artifact", str(context.layer_file))
        detail("Region", context.aws_region)
        detail("DynamoDB Region", str(context.dynamodb_region))
        detail("Architecture", context.architecture)
        detail("Runtimes", context.runtimes)
        detail("Release group", "local")
        detail("Distribution", context.distribution)
        detail("Collector version", context.upstream_version)
        detail("Build tags", context.build_tags_string)
        detail("Make public", str(context.public).lower())

    # Sub-step: Execute Publish Script
    subheader("Publishing layer")
    publisher_script = context.scripts_dir / "lambda_layer_publisher.py"

    # Build command with all arguments including build-tags
    publish_cmd = [
        sys.executable,
        str(publisher_script),
        "--layer-name",
        context.layer_name,
        "--artifact-name",
        str(context.layer_file),
        "--region",
        context.aws_region,
        "--dynamodb-region",
        context.dynamodb_region,
        "--architecture",
        context.architecture,
        "--runtimes",
        context.runtimes,
        "--release-group",
        "local",  # Always use 'local' for testing
        "--distribution",
        context.distribution,
        "--collector-version",
        context.upstream_version,
        "--make-public",
        str(context.public).lower(),
        "--build-tags",
        context.build_tags_string,
    ]

    try:
        # Run publish script
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
            context.set_layer_arn(layer_arn)
            tracker.complete_step(4, f"Layer ARN: {layer_arn}")
        else:
            warning("Publish step completed, but could not determine final Layer ARN")
            tracker.complete_step(4, "Published successfully (ARN unknown)")

        success(
            f"Published {context.distribution} distribution to region {context.aws_region} as a 'local' release"
        )
        info(
            "Next steps",
            "You can now test this layer by attaching it to a Lambda function",
        )

        return context

    except Exception as e:
        error("Failed to publish layer", str(e), exc_info=e)
        raise TerminateApp(
            f"Publication failed: {str(e)}",
            step_index=4,
            step_message=f"Publication failed: {str(e)}",
        )
