"""Build process for local OTel Collector layer."""

import os
import sys
from pathlib import Path

from scripts.otel_layer_utils.ui_utils import (
    header,
    subheader,
    error,
    success,
    format_file_size,
    separator,
)
from scripts.otel_layer_utils.subprocess_utils import run_command
from .context import BuildContext
from .exceptions import TerminateApp
from .testing import inject_error


@inject_error(step_index=3)
def build_layer(context: BuildContext, tracker) -> BuildContext:
    """
    Build the collector layer using the build script.

    Args:
        context: The build context
        tracker: Step tracker for progress reporting

    Returns:
        BuildContext: Updated build context with layer file and size

    Raises:
        TerminateApp: If build fails
    """
    # Start build step
    separator(title="Build Layer")
    header(f"Build layer ({context.architecture})")
    tracker.start_step(3)

    # Get build script path
    build_script = context.scripts_dir / "build_extension_layer.py"
    subheader("Running build script")

    # Prepare build command
    build_cmd = [
        sys.executable,
        str(build_script),
        "--upstream-repo",
        context.upstream_repo,
        "--upstream-ref",
        context.upstream_ref,
        # Distribution determines build tags, layer naming, and is used for DynamoDB metadata
        "--distribution",
        context.distribution,
        "--arch",
        context.architecture,
        "--output-dir",
        str(context.build_dir),
        # Pass version and tags as command line arguments
        "--upstream-version",
        context.upstream_version,
        "--build-tags",
        context.build_tags_string,
    ]

    try:
        # Run build script (don't capture output by default, let it stream)
        run_command(build_cmd)

        # Check output file
        layer_file = (
            context.build_dir
            / f"collector-{context.architecture}-{context.distribution}.zip"
        )
        if not layer_file.exists():
            error("Expected layer file not found after build", f"{layer_file}")
            raise TerminateApp(
                "Layer file not found",
                step_index=3,
                step_message="Layer file not found",
            )

        # Get file size
        file_size = os.path.getsize(layer_file)
        formatted_size = format_file_size(file_size)

        # Update context
        context.set_layer_file(layer_file, file_size)

        # Report success
        success("Build successful", f"{layer_file} ({formatted_size})")
        tracker.complete_step(3, f"Layer built: {layer_file.name} ({formatted_size})")

        return context

    except Exception as e:
        error("Failed to build layer", str(e))
        raise TerminateApp(
            f"Build failed: {str(e)}",
            step_index=3,
            step_message=f"Build failed: {str(e)}",
        )
