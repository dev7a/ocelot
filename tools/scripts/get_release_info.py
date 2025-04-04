#!/usr/bin/env python3
"""
get_release_info.py

Determines build tags, release tag, and release title based on distribution,
custom tags, collector version, and the distributions.yaml configuration file.

Reads inputs from environment variables:
- DISTRIBUTION: The selected distribution name.
- CUSTOM_BUILD_TAGS_INPUT: User-provided custom build tags.
- INPUT_COLLECTOR_VERSION: The collector version string (e.g., "v0.119.0").
- RELEASE_GROUP: The release group (e.g., "prod", "beta").
- DIST_YAML_PATH: Path to the distributions YAML file (defaults to 'config/distributions.yaml').

Sets GitHub Actions outputs:
- tag: The calculated release tag (e.g., "minimal-v0.119.0-prod").
- title: The calculated release title (e.g., "Release minimal v0.119.0 (prod)").
- build_tags: The calculated, comma-separated build tags string.
- collector_version: The input collector version (passed through).
- distribution: The input distribution name (passed through).
"""

import os
import sys
from pathlib import Path
from otel_layer_utils.github_utils import set_github_output
from otel_layer_utils.distribution_utils import (
    load_distributions,
    resolve_build_tags,
    DistributionError,
)

# Get Github Output file path
GITHUB_OUTPUT_FILE = os.environ.get("GITHUB_OUTPUT")

# Check if we're running in GitHub Actions
if not GITHUB_OUTPUT_FILE:
    print(
        "Error: GITHUB_OUTPUT environment variable not set. This script must run in GitHub Actions.",
        file=sys.stderr,
    )
    sys.exit(1)


# --- Get inputs from environment variables - Fail Fast ---
distribution = os.environ.get("DISTRIBUTION")
collector_version = os.environ.get("INPUT_COLLECTOR_VERSION")
release_group = os.environ.get("RELEASE_GROUP")
yaml_path_str = os.environ.get("DIST_YAML_PATH")  # Workflow should provide this

if not distribution:
    print("Error: DISTRIBUTION environment variable not set.", file=sys.stderr)
    sys.exit(1)
if not collector_version:
    print(
        "Error: INPUT_COLLECTOR_VERSION environment variable not set.", file=sys.stderr
    )
    sys.exit(1)
if not release_group:
    print("Error: RELEASE_GROUP environment variable not set.", file=sys.stderr)
    sys.exit(1)
if not yaml_path_str:
    print("Error: DIST_YAML_PATH environment variable not set.", file=sys.stderr)
    sys.exit(1)

yaml_path = Path(yaml_path_str)

print(f"Input Distribution: {distribution}")
print(f"Input Collector Version: {collector_version}")
print(f"Input Release Group: {release_group}")
print(f"Distribution Yaml Path: {yaml_path}")

# --- Determine Build Tags - Fail Fast ---
build_tags = ""
try:
    distributions_data = load_distributions(yaml_path)
    # Resolve tags using the utility, handles base inheritance
    buildtags_list = resolve_build_tags(distribution, distributions_data)
    # Filter out empty strings just in case resolve_build_tags returns them
    build_tags = ",".join(filter(None, buildtags_list))

except DistributionError as e:
    # Fail fast on any distribution processing error (file not found, dist not found, circular dep, etc.)
    print(f"Error processing distributions: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:  # Catch any other unexpected errors during tag resolution
    print(
        f"An unexpected error occurred while getting build tags: {e}", file=sys.stderr
    )
    sys.exit(1)

print(f"Determined Build Tags: '{build_tags}'")  # Quote for clarity if empty

# --- Determine Release Tag and Title ---
# Clean collector version for tag/name (remove 'v' prefix)
version_tag_part = collector_version.lstrip("v")
# Always include release group in tag and title
release_tag = f"{distribution}-v{version_tag_part}-{release_group}"
release_title = f"Release: distribution: {distribution} | version: {version_tag_part} | group: {release_group}"

print(f"Release Tag: {release_tag}")
print(f"Release Title: {release_title}")

# --- Set GitHub Actions outputs ---
print("\nSetting GitHub Actions outputs...")
set_github_output("tag", release_tag)
set_github_output("title", release_title)
set_github_output("build_tags", build_tags)
set_github_output("collector_version", collector_version)  # Pass through
set_github_output("distribution", distribution)  # Pass through
set_github_output("release_group", release_group)  # Output release group

print("\nSuccessfully set outputs.")
