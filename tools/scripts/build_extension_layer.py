#!/usr/bin/env python3
"""
build_extension_layer.py

Builds a custom OpenTelemetry Collector Lambda layer by cloning an upstream
repository, overlaying custom components, managing dependencies based on
configuration, and building the layer package. Version and build tags are
expected to be passed via environment variables from the GitHub workflow.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml  # Import yaml for dependency config loading
import click

# Import utility modules
from otel_layer_utils.distribution_utils import resolve_build_tags, DistributionError
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
    property_list,
)
from otel_layer_utils.subprocess_utils import run_command

# Default values (used if not overridden by args)
DEFAULT_UPSTREAM_REPO = "open-telemetry/opentelemetry-lambda"
DEFAULT_UPSTREAM_REF = "main"
DEFAULT_DISTRIBUTION = "default"
DEFAULT_ARCHITECTURE = "amd64"


def load_component_dependencies(yaml_path: Path) -> dict:
    """Load component dependency mappings from YAML file."""
    if not yaml_path.is_file():
        warning(
            f"Component dependency file not found at {yaml_path}",
            "Cannot add dependencies",
        )
        return {}  # Return empty dict if file doesn't exist

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
            if (
                not data
                or "dependencies" not in data
                or not isinstance(data["dependencies"], dict)
            ):
                warning(
                    f"Invalid format in {yaml_path}",
                    "Expected a 'dependencies' dictionary",
                )
                return {}

            success("Loaded dependency mappings", f"from {yaml_path}")
            return data["dependencies"]
    except yaml.YAMLError as e:
        error("Error parsing component dependency YAML file", str(e))
        return {}  # Return empty on error
    except Exception as e:
        error("Unexpected error loading YAML file", str(e))
        return {}


# Renamed for clarity, assumes distributions_data is loaded and passed in
def get_build_tags_list(distribution: str, distributions_data: dict) -> list[str]:
    """Determine the Go build tags list for a named distribution."""
    if not distributions_data:
        error(
            "Distributions data not loaded", f"Cannot resolve tags for '{distribution}'"
        )
        raise DistributionError("Distributions configuration not available.")
    try:
        buildtags_list = resolve_build_tags(distribution, distributions_data)
        return buildtags_list  # Return the list directly
    except DistributionError as e:
        error("Error resolving build tags", f"Distribution '{distribution}': {e}")
        raise  # Re-raise the exception


def resolve_components_by_tags(
    active_build_tags: list[str], dependency_mappings: dict
) -> list[str]:
    """
    Determine which components should be included based on active build tags.
    Handles hierarchical tag resolution (e.g., 'all' tags).

    Args:
        active_build_tags: List of active build tags
        dependency_mappings: Dictionary mapping component tags to dependencies

    Returns:
        List of component tags that should be included
    """
    included_components = []

    # Check for hierarchical tag resolution
    has_global_all = "lambdacomponents.all" in active_build_tags

    # Identify categories with 'all' tags
    category_all_tags = {}
    for tag in active_build_tags:
        if tag.endswith(".all") and tag != "lambdacomponents.all":
            category = tag.rsplit(".", 1)[0]  # e.g., 'lambdacomponents.connector'
            category_all_tags[category] = True

    # Determine which components should be included
    for component_tag in dependency_mappings.keys():
        should_include = False

        # Direct match with active tag
        if component_tag in active_build_tags:
            should_include = True
            detail("Including component", f"Direct match: {component_tag}")

        # Global "all" tag includes everything
        elif has_global_all:
            should_include = True
            detail("Including component", f"Via global 'all' tag: {component_tag}")

        # Category "all" tag includes components in that category
        else:
            for category in category_all_tags:
                if component_tag.startswith(
                    f"{category}."
                ) and not component_tag.endswith(".all"):
                    should_include = True
                    detail(
                        "Including component",
                        f"Via category 'all' tag: {component_tag} from {category}.all",
                    )
                    break

        if should_include:
            included_components.append(component_tag)

    return included_components


def selective_copy_components(
    component_dir: Path,
    upstream_dir: Path,
    active_build_tags: list[str],
    dependency_mappings: dict,
) -> list[str]:
    """
    Selectively copy only the components that match our active build tags.
    Handles hierarchical tag resolution (e.g., 'all' tags).

    Returns a list of component tags that were included.
    """
    if not component_dir.is_dir():
        warning(
            f"Custom components directory not found at {component_dir}",
            "Proceeding without overlay",
        )
        return []

    subheader("Selecting components to overlay")

    # Use common helper to determine which components to include
    included_components = resolve_components_by_tags(
        active_build_tags, dependency_mappings
    )

    # If no components to include, we're done
    if not included_components:
        info("No components to overlay", "Based on active build tags")
        return []

    # Now copy only the selected components
    status(
        "Copying selected components",
        f"Included: {len(included_components)} components",
    )

    # Map of component tag prefixes to directory paths
    component_type_dirs = {
        "lambdacomponents.connector": "connector",
        "lambdacomponents.exporter": "exporter",
        "lambdacomponents.processor": "processor",
        "lambdacomponents.receiver": "receiver",
        "lambdacomponents.extension": "extension",
    }

    # Track what was actually copied
    copied_components = []

    # Copy base/common files first (if they exist)
    common_dir = component_dir / "common"
    if common_dir.is_dir():
        upstream_common_dir = upstream_dir / "collector" / "common"
        upstream_common_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(common_dir, upstream_common_dir, dirs_exist_ok=True)
        success("Copied common files", f"From {common_dir} to {upstream_common_dir}")

    # Copy each component type directory if needed
    for component_tag in included_components:
        # Extract the component type (e.g., 'connector', 'exporter')
        component_parts = component_tag.split(".")
        if len(component_parts) < 3:
            warning(f"Invalid component tag format: {component_tag}", "Skipping")
            continue

        component_type_prefix = f"{component_parts[0]}.{component_parts[1]}"
        component_name = component_parts[2]

        # Get the directory name for this component type
        if component_type_prefix not in component_type_dirs:
            warning(f"Unknown component type: {component_type_prefix}", "Skipping")
            continue

        component_type_dir = component_type_dirs[component_type_prefix]

        # Source and destination paths
        source_type_dir = component_dir / component_type_dir
        if not source_type_dir.is_dir():
            warning(
                f"Component type directory not found: {source_type_dir}", "Skipping"
            )
            continue

        # Copy specific component files
        # For *.all components, we copy everything in the directory
        if component_name == "all":
            dest_type_dir = (
                upstream_dir / "collector" / "lambdacomponents" / component_type_dir
            )
            dest_type_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files in this component type directory
            shutil.copytree(source_type_dir, dest_type_dir, dirs_exist_ok=True)
            success(
                f"Copied all {component_type_dir} components",
                f"From {source_type_dir} to {dest_type_dir}",
            )
            copied_components.append(component_tag)
        else:
            # Look for specific component file(s)
            # Common naming patterns: component_name.go, component_name_factory.go, etc.
            component_files = list(source_type_dir.glob(f"*{component_name}*.go"))

            if not component_files:
                warning(f"No files found for component: {component_tag}", "Skipping")
                continue

            # Create destination directory
            dest_type_dir = (
                upstream_dir / "collector" / "lambdacomponents" / component_type_dir
            )
            dest_type_dir.mkdir(parents=True, exist_ok=True)

            # Copy each file individually
            for file in component_files:
                dest_file = dest_type_dir / file.name
                shutil.copy2(file, dest_file)
                detail("Copied file", f"{file.name}")

            success(f"Copied {component_name} component files", f"To {dest_type_dir}")
            copied_components.append(component_tag)

    if copied_components:
        success(
            "Component overlay complete",
            f"Included {len(copied_components)} components",
        )
    else:
        warning("No components were copied", "Check component directory structure")

    return copied_components


def add_dependencies(
    collector_dir: Path,
    active_build_tags: list[str],
    dependency_mappings: dict,
    upstream_version: str,
):
    """Add Go dependencies based on active build tags, mappings, and a provided upstream version."""
    if not dependency_mappings:
        info("No dependency mappings loaded", "Skipping dependency addition")
        return
    if not upstream_version:
        # This case should ideally be caught in main() before calling this function
        error("Critical Error", "Upstream version is missing in add_dependencies")
        sys.exit(1)

    # Use common helper to determine which components to include
    status("Determining required dependencies", "Based on active build tags")
    modules_to_add = set()  # Use a set to avoid duplicate modules
    components_to_include = resolve_components_by_tags(
        active_build_tags, dependency_mappings
    )

    # Add dependencies for each component
    for component_tag in components_to_include:
        modules = dependency_mappings.get(component_tag)
        if isinstance(modules, list):
            modules_to_add.update(modules)
        elif isinstance(modules, str):
            modules_to_add.add(modules)
        else:
            warning(
                f"Invalid format for tag '{component_tag}' in dependency config",
                "Expected list or string",
            )

    if not modules_to_add:
        info("No custom component dependencies required", "For this distribution")
        return

    subheader("Adding dependencies")
    status("Using version", upstream_version)

    try:
        # Ensure version starts with 'v' if it doesn't already (Go modules expect it)
        version_tag = (
            upstream_version
            if upstream_version.startswith("v")
            else f"v{upstream_version}"
        )

        # Check if we have any dependencies to add
        if modules_to_add:
            # First, analyze go.mod to understand existing dependencies
            status("Analyzing", "go.mod file for dependency compatibility")
            try:
                go_mod_path = collector_dir / "go.mod"
                with open(go_mod_path, "r") as f:
                    go_mod_content = f.read()
                    status(
                        "Read go.mod file", f"{len(go_mod_content.splitlines())} lines"
                    )
            except Exception as e:
                warning("Could not read go.mod file", str(e))
                go_mod_content = ""

            # Add dependencies using go mod edit for more precise control
            status(
                "Using go mod edit to add dependencies",
                f"{len(modules_to_add)} modules",
            )
            success_count = 0
            failure_count = 0

            for module_path in modules_to_add:
                versioned_module = f"{module_path}@{version_tag}"
                status("Adding dependency", versioned_module)

                try:
                    # Use go mod edit for a more controlled approach
                    run_command(
                        ["go", "mod", "edit", f"-require={versioned_module}"],
                        cwd=str(collector_dir),
                        capture_output=True,
                    )
                    success_count += 1
                    success(f"Added dependency {versioned_module}")
                except subprocess.CalledProcessError as e:
                    warning(
                        f"Failed to add dependency with exact version: {versioned_module}",
                        f"Error: {e.stderr if hasattr(e, 'stderr') else str(e)}",
                    )
                    failure_count += 1

            # Summary of dependency addition
            if success_count > 0:
                success(f"Successfully added {success_count} dependencies")
            if failure_count > 0:
                warning(f"Failed to add {failure_count} dependencies")

            # Run go mod tidy once at the end to resolve all dependencies
            if success_count > 0:
                status("Running", "go mod tidy to resolve dependencies")
                try:
                    run_command(
                        ["go", "mod", "tidy"],
                        cwd=str(collector_dir),
                        capture_output=True,
                    )
                    success("Dependency resolution completed successfully")
                except subprocess.CalledProcessError as e:
                    error(
                        "Failed running 'go mod tidy'",
                        e.stderr if hasattr(e, "stderr") else str(e),
                    )
                    detail(
                        "Continuing with build process", "The build may still succeed"
                    )
            else:
                warning("No dependencies were successfully added")
                detail("Action", "Skipping 'go mod tidy'")
        else:
            info("No dependencies to add", "Skipping dependency management")

    except Exception as e:
        error("An unexpected error occurred during dependency management")
        detail("Detail", str(e))
        # Continue with the build process; it might still work


@click.command()
@click.option(
    "-r",
    "--upstream-repo",
    default=DEFAULT_UPSTREAM_REPO,
    help=f"Upstream repository (default: {DEFAULT_UPSTREAM_REPO})",
)
@click.option(
    "-b",
    "--upstream-ref",
    default=DEFAULT_UPSTREAM_REF,
    help=f"Upstream Git reference (branch, tag, SHA) (default: {DEFAULT_UPSTREAM_REF})",
)
@click.option(
    "-d",
    "--distribution",
    default=DEFAULT_DISTRIBUTION,
    help="Distribution name (used for logging)",
)
@click.option(
    "-a",
    "--arch",
    default=DEFAULT_ARCHITECTURE,
    type=click.Choice(["amd64", "arm64"]),
    help=f"Architecture (default: {DEFAULT_ARCHITECTURE})",
)
@click.option(
    "-o",
    "--output-dir",
    help="Output directory for built layer (default: current directory)",
)
@click.option(
    "-k",
    "--keep-temp",
    is_flag=True,
    help="Keep temporary build directory",
)
@click.option(
    "-v",
    "--upstream-version",
    help="Version of the upstream OpenTelemetry Collector",
)
@click.option(
    "-t",
    "--build-tags",
    help="Comma-separated list of build tags",
)
@click.option(
    "--config-file",
    help="Optional custom collector config file name (relative to config/collector-configs/)",
)
def main(
    upstream_repo,
    upstream_ref,
    distribution,
    arch,
    output_dir,
    keep_temp,
    upstream_version,
    build_tags,
    config_file,
):
    """Build Custom OpenTelemetry Collector Lambda Layer."""

    # Get Version and Build Tags from arguments or environment (for backward compatibility)
    # Prioritize command-line arguments over environment variables
    if not upstream_version:
        upstream_version = os.environ.get("UPSTREAM_VERSION")

    if not build_tags:
        build_tags_string = os.environ.get("BUILD_TAGS_STRING")
    else:
        build_tags_string = build_tags

    # CRITICAL: Fail if version is not provided by the workflow
    if not upstream_version:
        error(
            "UPSTREAM_VERSION not provided",
            "Either pass with --upstream-version or set UPSTREAM_VERSION environment variable",
        )
        detail(
            "Info",
            "This variable should be set by the calling GitHub workflow or CLI argument",
        )
        sys.exit(1)

    # Build tags string is needed for the 'make package' env var.
    # The list of tags is needed for dependency resolution.
    # Fail if build tags are not provided (unless distribution is 'default' which might have none)
    active_build_tags = []
    if build_tags_string is not None:  # Allow empty string for 'default' potentially
        active_build_tags = [
            tag for tag in build_tags_string.split(",") if tag
        ]  # Handle empty tags from split
    # We will rely on the workflow passing the correct tags; local resolution is removed for simplicity

    # Setup Paths and Load Configs
    output_dir = Path(output_dir).resolve() if output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    custom_repo_path = Path.cwd()
    component_dir = custom_repo_path / "components"
    config_dir = custom_repo_path / "config"
    dependency_yaml_path = config_dir / "component_dependencies.yaml"

    # Load component dependencies config
    dependency_mappings = load_component_dependencies(dependency_yaml_path)

    # Display build configuration using property list
    header("Build configuration")

    # Group important configuration properties
    build_props = {
        "Upstream Repository": upstream_repo,
        "Upstream Ref": upstream_ref,
        "Distribution": distribution,
        "Architecture": arch,
        "Upstream Version": upstream_version,
        "Build Tags": build_tags_string or "[none]",
        "Output Directory": str(output_dir),
    }

    # Less important properties with dimmer styling
    other_props = {
        "Keep Temp Directory": str(keep_temp),
        "Custom Component Dir": str(component_dir),
        "Dependency Config": str(dependency_yaml_path),
    }

    # Display configuration
    property_list(build_props)
    property_list(other_props)

    # --- Build Process ---
    temp_dir = tempfile.mkdtemp()
    temp_dir_path = Path(temp_dir)
    upstream_dir = temp_dir_path / "upstream"

    try:
        info("Temporary Directory", temp_dir)

        # Step 1: Clone upstream repository
        subheader("Clone upstream repository")

        repo_url = f"https://github.com/{upstream_repo}.git"

        def clone_repo():
            return subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    upstream_ref,
                    repo_url,
                    str(upstream_dir),
                ],
                capture_output=True,
                text=True,
            )

        clone_result = spinner("Cloning repository", clone_repo)
        if clone_result.returncode != 0:
            error("Failed to clone repository", clone_result.stderr)
            sys.exit(1)

        success("Repository cloned successfully")

        # Step 2: Copy custom components to the upstream directory
        subheader("Overlay custom components")

        # Use selective copying instead of copying everything
        included_components = selective_copy_components(
            component_dir, upstream_dir, active_build_tags, dependency_mappings
        )

        # If no components were included, we're done with this step
        if not included_components:
            info("No custom components to overlay", "Proceeding with build")
        else:
            success("Copied components", f"From {component_dir} to {upstream_dir}")

        # Step 2.5: Copy custom config file if specified
        if config_file:
            custom_config_path = (
                Path.cwd() / "config" / "collector-configs" / config_file
            )
            collector_dir = upstream_dir / "collector"
            dest_config_path = collector_dir / "config.yaml"
            if custom_config_path.is_file():
                try:
                    shutil.copy(custom_config_path, dest_config_path)
                    success(
                        "Custom collector config copied",
                        f"{custom_config_path} -> {dest_config_path}",
                    )
                except Exception as e:
                    warning(
                        f"Failed to copy custom config file: {custom_config_path}",
                        str(e),
                    )
            else:
                warning(
                    f"Custom config file not found: {custom_config_path}",
                    "Using default upstream config.yaml",
                )

        # Step 3: Add dependencies for custom components (if needed)
        subheader("Add dependencies")

        collector_dir = upstream_dir / "collector"
        if not collector_dir.is_dir():
            error("Collector directory not found", f"In upstream repo: {collector_dir}")
            sys.exit(1)

        # Pass the list of active tags, mappings, and the determined version
        add_dependencies(
            collector_dir, active_build_tags, dependency_mappings, upstream_version
        )

        # Step 4: Build the collector using 'make package'
        subheader("Build collector")

        build_env = {"GOARCH": arch}
        if build_tags_string:  # Use the comma-separated string for the env var
            build_env["BUILDTAGS"] = build_tags_string

        makefile_path = collector_dir / "Makefile"
        if not makefile_path.exists():
            error("Makefile not found", f"At {makefile_path}")
            detail("Detail", "Cannot build using make")
            sys.exit(1)

        def run_make_package():
            return subprocess.run(
                ["make", "package"],
                cwd=str(collector_dir),
                env={**os.environ.copy(), **build_env},
                capture_output=True,
                text=True,
            )

        build_result = spinner("Running make package", run_make_package)
        if build_result.returncode != 0:
            error("Build failed", build_result.stderr)
            if build_result.stdout:
                click.echo(build_result.stdout)
            sys.exit(1)

        success("Build successful")

        # Step 5: Rename and Copy the built layer
        subheader("Prepare output")

        build_output_dir = collector_dir / "build"
        original_filename = f"opentelemetry-collector-layer-{arch}.zip"

        # Always include distribution name in the filename for consistency
        new_filename = f"collector-{arch}-{distribution}.zip"

        original_build_file = build_output_dir / original_filename
        renamed_build_file = (
            build_output_dir / new_filename
        )  # Path for renamed file within build dir

        status("Checking build output", str(original_build_file))
        if not original_build_file.is_file():
            error("Build file not found", f"{original_build_file}")
            detail("Action", "Checking build directory contents")
            try:
                dir_contents = os.listdir(build_output_dir)
                for item in dir_contents:
                    detail("File", item)
            except Exception as ls_err:
                error("Could not list build directory contents", str(ls_err))
            sys.exit(1)

        # Rename the file produced by make
        status("Renaming file", f"{original_filename} to {new_filename}")
        try:
            original_build_file.rename(renamed_build_file)
            success("File renamed successfully")
        except OSError as e:
            error("Error renaming file")
            detail("Detail", str(e))
            sys.exit(1)

        # Copy the RENAMED file to the final output directory
        target_file = output_dir / new_filename  # Final destination uses the new name
        status("Copying layer", f"To {target_file}")
        shutil.copy(renamed_build_file, target_file)

        header("Build successful")
        status("Layer available at", str(target_file))

    except subprocess.CalledProcessError as e:
        header("Build failed")
        error(str(e))
        sys.exit(1)
    except Exception as e:
        header("Build failed")
        error("An unexpected error occurred")
        detail("Detail", str(e))
        sys.exit(1)
    finally:
        # Cleanup temporary directory
        if not keep_temp:
            subheader("Cleaning up")
            status("Removing temp dir", temp_dir)
            shutil.rmtree(temp_dir)
        else:
            info("Keeping temporary directory", temp_dir)


if __name__ == "__main__":
    main()
