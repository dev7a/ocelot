"""Report generation for local build process."""

import time
from typing import List, Tuple

from scripts.otel_layer_utils.ui_utils import (
    separator,
    format_file_size,
    format_elapsed_time,
    format_table,
)
from .context import BuildContext


def generate_summary(context: BuildContext, start_time: float) -> None:
    """
    Generate a summary report of the build process.

    Args:
        context: The build context
        start_time: The start time of the build process
    """
    separator(title="Build Summary")

    # Calculate total elapsed time
    total_elapsed = time.time() - start_time

    # Build rows for the summary table
    rows = _build_summary_rows(context, total_elapsed)

    # Create summary table
    headers = ["Property", "Value"]
    format_table(headers, rows, title="Build Completion Summary")


def _build_summary_rows(
    context: BuildContext, total_elapsed: float
) -> List[Tuple[str, str]]:
    """
    Build the rows for the summary table.

    Args:
        context: The build context
        total_elapsed: Total elapsed time in seconds

    Returns:
        List of (property, value) tuples for the summary table
    """
    rows = [
        ["Distribution", context.distribution],
        ["Architecture", context.architecture],
    ]

    # Add layer file information if available
    if context.layer_file:
        rows.append(["Layer File", str(context.layer_file)])

    # Add file size if available
    if context.layer_file_size:
        rows.append(["File Size", format_file_size(context.layer_file_size)])

    # Add timing information
    rows.append(["Total Duration", format_elapsed_time(total_elapsed)])

    # Add publishing information
    if context.skip_publish:
        rows.append(["Publishing", "Skipped"])
    elif context.layer_arn:
        rows.append(["Layer ARN", context.layer_arn])

    return rows
