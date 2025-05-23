"""Configuration handling for local build process."""

from pathlib import Path
from typing import Dict, List, Tuple

from scripts.otel_layer_utils.distribution_utils import (
    load_distributions as _load_distributions_utils,
    resolve_build_tags,
    DistributionError,
)
from scripts.otel_layer_utils.ui_utils import success, error, header, warning, info
from .context import BuildContext
from .exceptions import TerminateApp
from .testing import inject_error


def load_distribution_choices() -> Tuple[List[str], Dict]:
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
        distributions_data = _load_distributions_utils(dist_yaml_path)

        # If successful, populate choices
        distribution_choices = sorted(list(distributions_data.keys()))
        success("Loaded distribution choices", ", ".join(distribution_choices))

        # Fail fast if loaded data is empty or invalid
        if not distribution_choices or not distributions_data:
            raise ValueError(
                "Distributions config file loaded but appears empty or invalid."
            )

        return distribution_choices, distributions_data

    except FileNotFoundError:
        error(f"Fatal Error: Distributions config file not found at {dist_yaml_path}")
        raise TerminateApp(
            f"Distributions config file not found at {dist_yaml_path}",
            step_index=None,  # Not part of the tracked steps
            step_message=None,
        )
    except Exception as e:
        # Catch other errors during loading/parsing (e.g., YAMLError, ValueError)
        error(
            f"Fatal Error: Could not load distributions from config file {dist_yaml_path}",
            str(e),
        )
        raise TerminateApp(
            f"Failed to load distributions: {str(e)}",
            step_index=None,  # Not part of the tracked steps
            step_message=None,
        )


@inject_error(step_index=None)
def load_distributions(context: BuildContext) -> BuildContext:
    """
    Load distribution configuration and store in context.
    Also extracts the description for the current distribution.

    Args:
        context: The build context

    Returns:
        BuildContext: Updated build context with distributions data and description

    Raises:
        TerminateApp: If distributions data cannot be loaded (critical failure)
    """
    header("Loading distributions")

    try:
        repo_root = Path().cwd()
        dist_yaml_path = repo_root / "config" / "distributions.yaml"
        distributions_data = _load_distributions_utils(dist_yaml_path)
        context.set_distributions_data(distributions_data)
    except Exception as e: # Catch critical errors from loading the main distributions data
        error("CRITICAL: Failed to load distributions data from YAML", str(e))
        raise TerminateApp(
            f"CRITICAL: Failed to load distributions data: {str(e)}",
            step_index=None, 
            step_message=None,
        )

    # Now, safely attempt to extract the description for the current context.distribution
    current_dist_name = context.distribution
    dist_description = None
    try:
        # Ensure distributions_data was actually populated before trying to access it
        if context.distributions_data and current_dist_name in context.distributions_data:
            distribution_info = context.distributions_data[current_dist_name]
            if isinstance(distribution_info, dict):
                dist_description = distribution_info.get("description")
            else:
                warning(f"Data for distribution '{current_dist_name}' in config/distributions.yaml is not structured as a dictionary; cannot get description.")
        else:
            # This warning might be redundant if distribution name validity is checked by Click against loaded choices first,
            # but kept for safety if context.distribution could somehow be out of sync with loaded data.
            if context.distributions_data: # Only warn if data was loaded but key is missing
                warning(f"Distribution '{current_dist_name}' not found in loaded YAML data (config/distributions.yaml); cannot retrieve description.")
            # If context.distributions_data is empty, the critical error above would have already been raised.

    except Exception as e:
        # Catch any unexpected error during the description extraction specifically
        warning(f"Non-critical error while trying to extract description for distribution '{current_dist_name}'", str(e))
        # dist_description will remain None or its last state

    context.set_distribution_description_from_config(dist_description)
    
    if dist_description:
        success(f"Loaded description for '{current_dist_name}'", f'"{dist_description}"')
    else:
        # Refined info/warning based on why description might be missing
        if context.distributions_data and current_dist_name in context.distributions_data and \
           isinstance(context.distributions_data.get(current_dist_name), dict) and \
           "description" not in context.distributions_data[current_dist_name]:
            info(f"No 'description' field found for distribution '{current_dist_name}' in config.")
        elif not (context.distributions_data and current_dist_name in context.distributions_data):
            # This case should have been covered by warnings above about dist not found in data.
            info(f"Description for '{current_dist_name}' not available (distribution not found or data malformed).")
        # else: already covered by other warnings or success message

    return context


@inject_error(step_index=2)
def determine_build_tags(context: BuildContext, tracker) -> BuildContext:
    """
    Determine the build tags for the specified distribution.

    Args:
        context: The build context
        tracker: Step tracker for progress reporting

    Returns:
        BuildContext: Updated build context with build tags

    Raises:
        TerminateApp: If build tags cannot be resolved
    """
    tracker.start_step(2)

    try:
        # Check if distributions data is loaded
        if not context.distributions_data:
            error("Cannot resolve build tags", "Distributions data failed to load")
            raise TerminateApp(
                "Distributions data failed to load",
                step_index=2,
                step_message="Distributions data failed to load",
            )

        # Resolve build tags
        buildtags_list = resolve_build_tags(
            context.distribution, context.distributions_data
        )
        build_tags_string = ",".join(filter(None, buildtags_list))

        # Update the context
        context.set_build_tags(build_tags_string)

        # Also check for optional custom config file
        dist_info = context.distributions_data.get(context.distribution, {})
        config_file = dist_info.get("config-file")
        context.set_config_file(config_file)

        # Use the already imported success function
        success("Determined build tags", build_tags_string)
        if config_file:
            success("Custom config file specified", config_file)
            
        # For display in the step tracker, don't include the full tag list in the line
        tracker.complete_step(2)

        return context

    except DistributionError as e:
        error(
            f"Error resolving build tags for distribution '{context.distribution}'",
            str(e),
        )
        raise TerminateApp(
            f"Error resolving build tags: {str(e)}", step_index=2, step_message=str(e)
        )
    except Exception as e:
        error("An unexpected error occurred resolving build tags", str(e))
        raise TerminateApp(
            f"An unexpected error occurred resolving build tags: {str(e)}",
            step_index=2,
            step_message=f"Unexpected error: {str(e)}",
        )
