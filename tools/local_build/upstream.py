"""Upstream repository management for the local build process."""

from pathlib import Path
import tempfile

from scripts.otel_layer_utils.ui_utils import (
    status,
    info,
    subheader,
    error,
    success,
    debug,
)
from scripts.otel_layer_utils.subprocess_utils import run_command
from .context import BuildContext
from .exceptions import TerminateApp
from .testing import inject_error


@inject_error(step_index=0)
def clone_repository(context: BuildContext, tracker) -> BuildContext:
    """
    Clone the upstream repository and determine its version.

    Args:
        context: The build context
        tracker: Step tracker for progress reporting

    Returns:
        BuildContext: Updated build context with temporary directory and upstream version

    Raises:
        TerminateApp: If cloning or version determination fails
    """
    # --- Start the clone step ---
    tracker.start_step(0)
    subheader("Cloning repository")

    # Create temporary directory
    temp_upstream_dir = tempfile.mkdtemp(prefix="otel-upstream-")
    temp_upstream_path = Path(temp_upstream_dir)

    # Store in context
    context.set_temp_dir(temp_upstream_dir)

    # Display information
    status("Target repo", f"{context.upstream_repo}@{context.upstream_ref}")
    info("Temp directory", temp_upstream_dir)

    # Clone the repository
    repo_url = f"https://github.com/{context.upstream_repo}.git"
    try:
        run_command(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                context.upstream_ref,
                repo_url,
                str(temp_upstream_path),
            ],
            capture_output=True,
        )
        tracker.complete_step(0, "Repository cloned successfully")
    except Exception as e:
        error(f"Failed to clone repository {repo_url}", str(e))
        raise TerminateApp(
            f"Failed to clone repository: {str(e)}",
            step_index=0,
            step_message=f"Failed to clone repository: {str(e)}",
        )

    # Get upstream version from the cloned repository
    context = determine_upstream_version(context, tracker)

    return context


@inject_error(step_index=1)
def determine_upstream_version(context: BuildContext, tracker) -> BuildContext:
    """
    Determine the upstream version from the cloned repository.

    Args:
        context: The build context
        tracker: Step tracker for progress reporting

    Returns:
        BuildContext: Updated build context with upstream version

    Raises:
        TerminateApp: If version determination fails
    """
    temp_upstream_path = Path(context.temp_upstream_dir)
    upstream_collector_dir = temp_upstream_path / "collector"
    upstream_makefile = upstream_collector_dir / "Makefile"
    upstream_version_file = upstream_collector_dir / "VERSION"

    # Start the version determination step
    tracker.start_step(1)
    subheader("Determining version")

    # Check if Makefile exists
    if not upstream_makefile.exists():
        error("Makefile not found", f"{upstream_makefile}")
        debug(f"Looking for Makefile at {upstream_makefile}")
        raise TerminateApp(
            "Makefile not found", step_index=1, step_message="Makefile not found"
        )

    # Run the set-otelcol-version make target
    try:
        run_command(
            ["make", "set-otelcol-version"],
            cwd=str(upstream_collector_dir),
            capture_output=True,
        )
    except Exception as e:
        error("Failed to run set-otelcol-version target", str(e))
        raise TerminateApp(
            f"Failed to run make: {str(e)}",
            step_index=1,
            step_message=f"Failed to run make: {str(e)}",
        )

    # Check if VERSION file was created
    if not upstream_version_file.is_file():
        error("VERSION file not created", f"{upstream_version_file}")
        raise TerminateApp(
            "VERSION file not created",
            step_index=1,
            step_message="VERSION file not created",
        )

    # Read version from VERSION file
    try:
        with open(upstream_version_file, "r") as vf:
            upstream_version = vf.read().strip()

        if not upstream_version:
            error("VERSION file is empty", f"{upstream_version_file}")
            raise TerminateApp(
                "VERSION file is empty",
                step_index=1,
                step_message="VERSION file is empty",
            )

        # Update context with version
        context.set_upstream_version(upstream_version)
        success("Determined Upstream Version", upstream_version)
        tracker.complete_step(1, f"Version: {upstream_version}")

        return context
    except Exception as e:
        error("Failed to read VERSION file", str(e))
        raise TerminateApp(
            f"Failed to read VERSION: {str(e)}",
            step_index=1,
            step_message=f"Failed to read VERSION: {str(e)}",
        )


def cleanup_temp_dir(context: BuildContext) -> None:
    """
    Clean up temporary directory if needed.

    Args:
        context: The build context
    """
    import shutil

    if context.temp_upstream_dir and Path(context.temp_upstream_dir).exists():
        if context.keep_temp:
            info("Keeping temporary upstream clone", context.temp_upstream_dir)
        else:
            subheader("Cleaning up")
            status("Removing temporary upstream clone", context.temp_upstream_dir)
            shutil.rmtree(context.temp_upstream_dir)
